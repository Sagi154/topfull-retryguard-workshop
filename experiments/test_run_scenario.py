"""
test_run_scenario.py — Unit tests for the load-phase scheduling logic in
run_scenario.py (resolve_locust_phases, due_phases) and for the Locust
launch wiring (_launch_locust). No network access; all SSH calls are mocked.

Run:
    python experiments/test_run_scenario.py
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_scenario


class TestResolveLocustPhasesBackwardCompat(unittest.TestCase):
    def test_no_phases_key_returns_single_phase_at_zero(self):
        cfg = {
            "duration_seconds": 600,
            "locust": {
                "user_counts": {"getproduct": 100, "emptycart": 300},
                "spawn_rate": 90,
            },
        }
        phases = run_scenario.resolve_locust_phases(cfg)
        self.assertEqual(phases, [{
            "at_seconds": 0,
            "user_counts": {"getproduct": 100, "emptycart": 300},
            "spawn_rate": 90,
        }])

    def test_missing_locust_block_returns_empty_single_phase(self):
        cfg = {"duration_seconds": 300}
        phases = run_scenario.resolve_locust_phases(cfg)
        self.assertEqual(phases, [{
            "at_seconds": 0, "user_counts": {}, "spawn_rate": None,
        }])


class TestResolveLocustPhasesExplicit(unittest.TestCase):
    def test_two_phases_sorted_and_normalized(self):
        cfg = {
            "duration_seconds": 900,
            "locust": {
                "spawn_rate": 90,
                "phases": [
                    {"at_seconds": 300, "user_counts": {"getproduct": 25}},
                    {"at_seconds": 0, "user_counts": {"getproduct": 100}},
                ],
            },
        }
        phases = run_scenario.resolve_locust_phases(cfg)
        self.assertEqual([p["at_seconds"] for p in phases], [0, 300])
        self.assertEqual(phases[0]["user_counts"], {"getproduct": 100})
        self.assertEqual(phases[1]["user_counts"], {"getproduct": 25})
        self.assertEqual(phases[0]["spawn_rate"], 90)
        self.assertEqual(phases[1]["spawn_rate"], 90)

    def test_phase_specific_spawn_rate_overrides_default(self):
        cfg = {
            "duration_seconds": 900,
            "locust": {
                "spawn_rate": 90,
                "phases": [
                    {"at_seconds": 0, "user_counts": {}, "spawn_rate": 90},
                    {"at_seconds": 300, "user_counts": {}, "spawn_rate": 20},
                ],
            },
        }
        phases = run_scenario.resolve_locust_phases(cfg)
        self.assertEqual(phases[1]["spawn_rate"], 20)

    def test_phases_and_top_level_user_counts_is_an_error(self):
        cfg = {
            "duration_seconds": 900,
            "locust": {
                "user_counts": {"getproduct": 100},
                "phases": [{"at_seconds": 0, "user_counts": {"getproduct": 100}}],
            },
        }
        with self.assertRaises(run_scenario.ConfigError):
            run_scenario.resolve_locust_phases(cfg)

    def test_first_phase_must_start_at_zero(self):
        cfg = {
            "duration_seconds": 900,
            "locust": {"phases": [{"at_seconds": 10, "user_counts": {}}]},
        }
        with self.assertRaises(run_scenario.ConfigError):
            run_scenario.resolve_locust_phases(cfg)

    def test_duplicate_at_seconds_is_an_error(self):
        cfg = {
            "duration_seconds": 900,
            "locust": {"phases": [
                {"at_seconds": 0, "user_counts": {}},
                {"at_seconds": 0, "user_counts": {}},
            ]},
        }
        with self.assertRaises(run_scenario.ConfigError):
            run_scenario.resolve_locust_phases(cfg)

    def test_phase_at_or_after_duration_is_an_error(self):
        cfg = {
            "duration_seconds": 300,
            "locust": {"phases": [
                {"at_seconds": 0, "user_counts": {}},
                {"at_seconds": 300, "user_counts": {}},
            ]},
        }
        with self.assertRaises(run_scenario.ConfigError):
            run_scenario.resolve_locust_phases(cfg)

    def test_missing_at_seconds_is_an_error(self):
        cfg = {
            "duration_seconds": 300,
            "locust": {"phases": [{"user_counts": {}}]},
        }
        with self.assertRaises(run_scenario.ConfigError):
            run_scenario.resolve_locust_phases(cfg)


class TestDuePhases(unittest.TestCase):
    def setUp(self):
        self.phases = [
            {"at_seconds": 0, "user_counts": {}, "spawn_rate": 90},
            {"at_seconds": 300, "user_counts": {}, "spawn_rate": 90},
            {"at_seconds": 600, "user_counts": {}, "spawn_rate": 90},
        ]

    def test_nothing_due_before_threshold(self):
        self.assertEqual(run_scenario.due_phases(299, {0}, self.phases), [])

    def test_single_phase_due_at_threshold(self):
        self.assertEqual(run_scenario.due_phases(300, {0}, self.phases), [1])

    def test_multiple_phases_due_after_a_gap(self):
        self.assertEqual(run_scenario.due_phases(650, {0}, self.phases), [1, 2])

    def test_already_fired_phase_is_not_returned_again(self):
        self.assertEqual(run_scenario.due_phases(650, {0, 1}, self.phases), [2])

    def test_backward_compat_single_phase_never_fires(self):
        single = [{"at_seconds": 0, "user_counts": {}, "spawn_rate": 90}]
        self.assertEqual(run_scenario.due_phases(10_000, {0}, single), [])


class TestLaunchLocustWiring(unittest.TestCase):
    def _base_cfg(self):
        return {
            "infra": {
                "loadgen_ssh_host": "topfull-load",
                "topfull_loadgen_path": "/home/idozacharia/TopFull/TopFull_loadgen",
            },
            "locust": {
                "scripts": ["online_boutique_create.sh", "online_boutique_create2.sh"],
            },
        }

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_launch_locust_exports_user_counts_and_spawn_rate(
        self, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = SimpleNamespace(stdout="3")
        cfg = self._base_cfg()

        run_scenario._launch_locust(
            cfg,
            user_counts={"getproduct": 25, "emptycart": 75},
            spawn_rate=90,
        )

        written_path, written_content = mock_write_script.call_args[0][1:3]
        self.assertEqual(written_path, "/tmp/rg_locust_launch.sh")
        self.assertIn("export GETPRODUCT=25", written_content)
        self.assertIn("export CART=75", written_content)
        self.assertIn("export RATE=90", written_content)

        kill_calls = [
            c for c in mock_ssh.call_args_list
            if "pkill" in c.args[1] or "kill-server" in c.args[1]
        ]
        self.assertTrue(kill_calls, "expected a Locust kill command before relaunch")

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_launch_locust_exits_if_no_locust_processes_found(
        self, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = SimpleNamespace(stdout="0")
        cfg = self._base_cfg()

        with self.assertRaises(SystemExit):
            run_scenario._launch_locust(cfg, user_counts={}, spawn_rate=None)

    @mock.patch("run_scenario._launch_locust")
    def test_start_locust_launches_only_phase_zero(self, mock_launch):
        cfg = self._base_cfg()
        phases = [
            {"at_seconds": 0, "user_counts": {"getproduct": 100}, "spawn_rate": 90},
            {"at_seconds": 300, "user_counts": {"getproduct": 25}, "spawn_rate": 90},
        ]
        run_scenario.start_locust(cfg, phases)
        mock_launch.assert_called_once_with(cfg, {"getproduct": 100}, 90)

    @mock.patch("run_scenario._launch_locust")
    def test_switch_locust_phase_relaunches_with_new_load(self, mock_launch):
        cfg = self._base_cfg()
        phase = {"at_seconds": 300, "user_counts": {"getproduct": 25}, "spawn_rate": 20}
        run_scenario.switch_locust_phase(cfg, phase)
        mock_launch.assert_called_once_with(cfg, {"getproduct": 25}, 20)


if __name__ == "__main__":
    unittest.main()
