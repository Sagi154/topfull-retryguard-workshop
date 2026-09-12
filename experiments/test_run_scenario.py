"""
test_run_scenario.py — Unit tests for the load-phase scheduling logic in
run_scenario.py (resolve_locust_phases, due_phases) and for the Locust
launch wiring (_launch_locust). No network access; all SSH calls are mocked.

Run:
    python experiments/test_run_scenario.py
"""
import json
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


class TestStartRetryGuardWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "retryguard_script": "/home/idozacharia/experiments/retryguard.py",
            },
            "retryguard": {
                "enabled": enabled,
                "rejection_threshold": 0.20,
                "sample_interval_seconds": 1,
                "interval_samples": 30,
                "retry_attempts_on": 3,
                "retry_attempts_off": 0,
            },
        }

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_deploys_retryguard_py(self, mock_deploy, mock_ssh, mock_json, mock_script, mock_wait):
        run_scenario.start_retryguard(self._cfg(enabled=True))
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "retryguard.py",
            "/home/idozacharia/experiments/retryguard.py",
        )

    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_noop_when_disabled(self, mock_deploy):
        run_scenario.start_retryguard(self._cfg(enabled=False))
        mock_deploy.assert_not_called()


class TestEnvoyRetryCollectorWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "envoy_retry_collector_script":
                    "/home/idozacharia/experiments/envoy_retry_collector.py",
            },
            "envoy_retry_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 5,
            },
        }

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    @mock.patch("run_scenario.discover_service_pod_ips", return_value={})
    def test_start_uploads_params_and_launches_tmux(
        self, mock_seed, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        run_scenario.start_envoy_retry_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )

        json_path, params = mock_write_json.call_args[0][1:3]
        self.assertEqual(json_path, "/tmp/envoy_retry_params.json")
        self.assertEqual(params["poll_interval_seconds"], 5)
        self.assertNotIn("services", params)
        self.assertEqual(params["transport"], "network_prometheus")
        self.assertEqual(params["pod_ips"], {})
        self.assertIn("max_workers", params)
        self.assertNotIn("exec_mode", params)
        self.assertNotIn("pod_names", params)
        self.assertNotIn("record_path", params)

        script_path, script_body = mock_write_script.call_args[0][1:3]
        self.assertEqual(script_path, "/tmp/rg_envoy_retry.sh")
        self.assertIn("envoy_retry_collector.py --params /tmp/envoy_retry_params.json",
                      script_body)

        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if "tmux new-session" in c.args[1] and "envoyretry" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_start_noop_when_disabled(
        self, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=False)
        run_scenario.start_envoy_retry_collector(cfg)
        mock_ssh.assert_not_called()
        mock_write_json.assert_not_called()
        mock_write_script.assert_not_called()

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    @mock.patch("run_scenario.discover_service_pod_ips", return_value={})
    def test_start_passes_services_override(
        self, mock_seed, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["envoy_retry_collector"]["services"] = ["frontend", "cartservice"]
        run_scenario.start_envoy_retry_collector(cfg)
        params = mock_write_json.call_args[0][2]
        self.assertEqual(params["services"], ["frontend", "cartservice"])

    @mock.patch("run_scenario.ssh")
    def test_stop_master_stack_pkills_envoy_collector(self, mock_ssh):
        cfg = {
            "infra": {"master_ssh_host": "topfull-master"},
        }
        run_scenario.stop_master_stack(cfg)
        cmd = mock_ssh.call_args[0][1]
        self.assertIn("[e]nvoy_retry_collector.py", cmd)

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_ensure_envoy_stats_enabled_patches_each_caller(
        self, mock_ssh, mock_write_json
    ):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        run_scenario.ensure_envoy_stats_enabled(cfg, ["frontend", "checkoutservice"])

        patch_calls = [
            c for c in mock_ssh.call_args_list
            if "kubectl patch deployment" in c.args[1]
        ]
        self.assertEqual(len(patch_calls), 2)
        self.assertIn("frontend", patch_calls[0].args[1])
        self.assertIn("checkoutservice", patch_calls[1].args[1])

        rollout_calls = [
            c for c in mock_ssh.call_args_list
            if "kubectl rollout status" in c.args[1]
        ]
        self.assertEqual(len(rollout_calls), 2)

        patched_json = mock_write_json.call_args[0][2]
        self.assertEqual(
            patched_json["spec"]["template"]["metadata"]["annotations"]
            ["sidecar.istio.io/statsInclusionRegexps"],
            run_scenario.STATS_INCLUSION_REGEX,
        )
        # Regex must now also cover inbound listener stats, not just outbound.
        self.assertIn("downstream_rq", run_scenario.STATS_INCLUSION_REGEX)
        self.assertIn("upstream_rq", run_scenario.STATS_INCLUSION_REGEX)

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_ensure_envoy_stats_enabled_warns_but_continues_on_patch_failure(
        self, mock_ssh, mock_write_json
    ):
        mock_ssh.return_value = SimpleNamespace(
            returncode=1, stdout="", stderr="not found"
        )
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        # Must not raise.
        run_scenario.ensure_envoy_stats_enabled(cfg, ["frontend"])
        rollout_calls = [
            c for c in mock_ssh.call_args_list
            if "kubectl rollout status" in c.args[1]
        ]
        self.assertEqual(len(rollout_calls), 0)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    @mock.patch("run_scenario.discover_service_pod_ips", return_value={})
    def test_start_envoy_retry_collector_patches_all_services_by_default(
        self, mock_seed, mock_deploy, mock_ssh, mock_ensure, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        run_scenario.start_envoy_retry_collector(cfg)
        mock_ensure.assert_called_once_with(cfg, run_scenario.ALL_BOUTIQUE_SERVICES)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    @mock.patch("run_scenario.discover_service_pod_ips", return_value={})
    def test_start_envoy_retry_collector_patches_service_override(
        self, mock_seed, mock_deploy, mock_ssh, mock_ensure, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["envoy_retry_collector"]["services"] = ["frontend"]
        run_scenario.start_envoy_retry_collector(cfg)
        mock_ensure.assert_called_once_with(cfg, ["frontend"])


class TestResourceUsageCollectorWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "resource_usage_collector_script":
                    "/home/idozacharia/experiments/resource_usage_collector.py",
            },
            "resource_usage_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 5,
            },
        }

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_uploads_params_and_launches_tmux(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        run_scenario.start_resource_usage_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "resource_usage_collector.py",
            "/home/idozacharia/experiments/resource_usage_collector.py",
        )

        json_path, params = mock_write_json.call_args[0][1:3]
        self.assertEqual(json_path, "/tmp/resource_usage_params.json")
        self.assertEqual(params["poll_interval_seconds"], 5)
        self.assertNotIn("services", params)

        script_path, script_body = mock_write_script.call_args[0][1:3]
        self.assertEqual(script_path, "/tmp/rg_resource_usage.sh")
        self.assertIn(
            "resource_usage_collector.py --params /tmp/resource_usage_params.json",
            script_body,
        )

        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if "tmux new-session" in c.args[1] and "resourceusage" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_start_noop_when_disabled(
        self, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=False)
        run_scenario.start_resource_usage_collector(cfg)
        mock_ssh.assert_not_called()
        mock_write_json.assert_not_called()
        mock_write_script.assert_not_called()

    @mock.patch("run_scenario.ssh")
    def test_stop_master_stack_pkills_resource_collector(self, mock_ssh):
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        run_scenario.stop_master_stack(cfg)
        cmd = mock_ssh.call_args[0][1]
        self.assertIn("[r]esource_usage_collector.py", cmd)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_passes_services_override(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["resource_usage_collector"]["services"] = ["frontend", "checkoutservice"]
        run_scenario.start_resource_usage_collector(cfg)
        params = mock_write_json.call_args[0][2]
        self.assertEqual(params["services"], ["frontend", "checkoutservice"])


class TestTopfullThrottleCollectorWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "topfull_throttle_collector_script":
                    "/home/idozacharia/experiments/topfull_throttle_collector.py",
            },
            "topfull_throttle_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 1,
            },
        }

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_uploads_params_and_launches_tmux(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        run_scenario.start_topfull_throttle_collector(cfg)
        self.assertEqual(
            mock_deploy.call_args_list,
            [
                mock.call(
                    "topfull-master",
                    "topfull_throttle_collector.py",
                    "/home/idozacharia/experiments/topfull_throttle_collector.py",
                ),
                mock.call(
                    "topfull-master",
                    "topfull_cpu_quotas.py",
                    "/home/idozacharia/experiments/topfull_cpu_quotas.py",
                ),
            ],
        )
        json_path, params = mock_write_json.call_args[0][1:3]
        self.assertEqual(json_path, "/tmp/topfull_throttle_params.json")
        self.assertEqual(params["poll_interval_seconds"], 1)
        self.assertEqual(params["layer_a_poll_interval_seconds"], 5)
        self.assertNotIn(
            "layer_a_poll_interval_seconds",
            cfg["topfull_throttle_collector"],
        )
        script_path, script_body = mock_write_script.call_args[0][1:3]
        self.assertEqual(script_path, "/tmp/rg_topfull_throttle.sh")
        self.assertIn(
            "topfull_throttle_collector.py --params /tmp/topfull_throttle_params.json",
            script_body,
        )
        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if "tmux new-session" in c.args[1] and "throttle" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_start_noop_when_disabled(
        self, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        run_scenario.start_topfull_throttle_collector(self._cfg(enabled=False))
        mock_ssh.assert_not_called()
        mock_write_json.assert_not_called()

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_passes_explicit_layer_a_interval(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["topfull_throttle_collector"]["layer_a_poll_interval_seconds"] = 1
        run_scenario.start_topfull_throttle_collector(cfg)
        params = mock_write_json.call_args[0][2]
        self.assertEqual(params["poll_interval_seconds"], 1)
        self.assertEqual(params["layer_a_poll_interval_seconds"], 1)


class TestDeployRepoScript(unittest.TestCase):
    def test_missing_local_file_exits(self):
        with mock.patch.object(run_scenario, "EXPERIMENTS_DIR", Path("/no/such/dir")):
            with self.assertRaises(SystemExit):
                run_scenario.deploy_repo_script(
                    "topfull-master", "retryguard.py",
                    "/home/idozacharia/experiments/retryguard.py",
                )

    @mock.patch("run_scenario.step")
    @mock.patch("run_scenario.scp_to")
    @mock.patch("run_scenario.ssh")
    def test_plain_cp_when_dest_writable(self, mock_ssh, mock_scp, mock_step):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        run_scenario.deploy_repo_script(
            "topfull-master", "retryguard.py",
            "/home/idozacharia/experiments/retryguard.py",
        )
        mock_scp.assert_called_once()
        self.assertEqual(mock_scp.call_args[0][2], "/tmp/rg_deploy_retryguard.py")
        dest_copies = [
            c.args[1] for c in mock_ssh.call_args_list
            if "experiments/retryguard.py" in c.args[1]
        ]
        self.assertTrue(any(cmd.startswith("cp ") for cmd in dest_copies))
        self.assertFalse(any("sudo cp" in cmd for cmd in dest_copies))

    @mock.patch("run_scenario.step")
    @mock.patch("run_scenario.scp_to")
    @mock.patch("run_scenario.ssh")
    def test_sudo_cp_fallback_when_plain_cp_fails(self, mock_ssh, mock_scp, mock_step):
        def ssh_side_effect(host, cmd, check=True):
            if cmd.startswith("cp "):
                return SimpleNamespace(returncode=1, stdout="", stderr="Permission denied")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_ssh.side_effect = ssh_side_effect
        run_scenario.deploy_repo_script(
            "topfull-master", "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )
        sudo_copies = [
            c.args[1] for c in mock_ssh.call_args_list
            if "sudo cp" in c.args[1]
        ]
        self.assertEqual(len(sudo_copies), 1)

    @mock.patch("run_scenario.scp_to")
    @mock.patch("run_scenario.ssh")
    def test_both_cp_paths_fail_exits(self, mock_ssh, mock_scp):
        mock_ssh.return_value = SimpleNamespace(
            returncode=1, stdout="", stderr="Permission denied"
        )
        with self.assertRaises(SystemExit):
            run_scenario.deploy_repo_script(
                "topfull-master", "retryguard.py",
                "/home/idozacharia/experiments/retryguard.py",
            )


class TestServiceCapacity(unittest.TestCase):
    def test_parse_cpu_to_millicores_variants(self):
        self.assertEqual(run_scenario.parse_cpu_to_millicores("100m"), 100)
        self.assertEqual(run_scenario.parse_cpu_to_millicores("1"), 1000)
        self.assertEqual(run_scenario.parse_cpu_to_millicores("0.5"), 500)
        self.assertIsNone(run_scenario.parse_cpu_to_millicores(None))
        self.assertIsNone(run_scenario.parse_cpu_to_millicores(""))

    @mock.patch("run_scenario.ssh")
    def test_capture_service_capacity_parses_deployment_json(self, mock_ssh):
        deploy_json = json.dumps({
            "items": [
                {
                    "metadata": {"name": "checkoutservice"},
                    "spec": {
                        "replicas": 1,
                        "template": {"spec": {"containers": [
                            {"name": "server", "resources": {
                                "limits": {"cpu": "100m"},
                                "requests": {"cpu": "100m"},
                            }},
                        ]}},
                    },
                },
                {
                    "metadata": {"name": "frontend"},
                    "spec": {
                        "replicas": 1,
                        "template": {"spec": {"containers": [
                            {"name": "server", "resources": {
                                "limits": {"cpu": "300m"},
                                "requests": {"cpu": "200m"},
                            }},
                        ]}},
                    },
                },
                {
                    "metadata": {"name": "not-requested-service"},
                    "spec": {"replicas": 1, "template": {"spec": {"containers": []}}},
                },
            ],
        })
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout=deploy_json, stderr="")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}

        capacity = run_scenario.capture_service_capacity(
            cfg, ["checkoutservice", "frontend"]
        )

        self.assertEqual(set(capacity.keys()), {"checkoutservice", "frontend"})
        self.assertEqual(capacity["checkoutservice"], {
            "cpu_limit_millicores": 100,
            "cpu_request_millicores": 100,
            "replica_count": 1,
        })
        self.assertEqual(capacity["frontend"]["cpu_limit_millicores"], 300)
        self.assertEqual(capacity["frontend"]["cpu_request_millicores"], 200)

    @mock.patch("run_scenario.ssh")
    def test_capture_service_capacity_handles_bad_json(self, mock_ssh):
        mock_ssh.return_value = SimpleNamespace(returncode=1, stdout="", stderr="boom")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        capacity = run_scenario.capture_service_capacity(cfg, ["frontend"])
        self.assertEqual(capacity, {})

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_writes_service_capacity_json(self, mock_ssh, mock_write_json):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src",
                "results_base_path": "/home/idozacharia/experiments/results",
            },
            "scenario_id": 1, "scenario_name": "scenario_1_baseline",
            "condition": "baseline", "run_number": 7, "duration_seconds": 300,
            "retryguard": {"enabled": False},
            "log_folder": "test_run",
        }
        capacity = {"frontend": {"cpu_limit_millicores": 300, "cpu_request_millicores": 200, "replica_count": 1}}

        run_scenario.collect_results(cfg, capacity)

        capacity_calls = [
            c for c in mock_write_json.call_args_list
            if c.args[1].endswith("service_capacity.json")
        ]
        self.assertEqual(len(capacity_calls), 1)
        self.assertEqual(capacity_calls[0].args[2], capacity)

        manifest_calls = [
            c for c in mock_write_json.call_args_list
            if c.args[1].endswith("run_manifest.json")
        ]
        self.assertEqual(len(manifest_calls), 1)
        self.assertIn("topfull_throttle_collector", manifest_calls[0].args[2])

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_writes_empty_dict_when_capacity_omitted(self, mock_ssh, mock_write_json):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src",
                "results_base_path": "/home/idozacharia/experiments/results",
            },
            "scenario_id": 1, "scenario_name": "scenario_1_baseline",
            "condition": "baseline", "run_number": 7, "duration_seconds": 300,
            "retryguard": {"enabled": False},
            "log_folder": "test_run",
        }
        run_scenario.collect_results(cfg)
        capacity_calls = [
            c for c in mock_write_json.call_args_list
            if c.args[1].endswith("service_capacity.json")
        ]
        self.assertEqual(capacity_calls[0].args[2], {})


class TestApplyCpuLimitFraction(unittest.TestCase):
    def test_patches_catalog_to_50m(self):
        cfg = {
            "infra": {"master_ssh_host": "topfull-master"},
            "scale_constraints": [{
                "deployment": "productcatalogservice",
                "namespace": "default",
                "method": "cpu_limit",
                "cpu_limit_fraction": 0.1,
                "container": "server",
            }],
        }
        patches = []

        def fake_ssh(host, cmd, check=True):
            patches.append(cmd)
            return SimpleNamespace(stdout="{}", returncode=0)

        with mock.patch.object(run_scenario, "ssh", fake_ssh), \
             mock.patch.object(run_scenario, "wait_with_progress", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "banner", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None):
            run_scenario.apply_constraints(cfg)
        joined = "\n".join(patches)
        self.assertIn("50m", joined)
        self.assertNotIn("100m", joined)


class TestReconcilePaperCpuLimits(unittest.TestCase):
    def test_patches_checkout_to_1000m_500m(self):
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        cmds = []

        def fake_ssh(host, cmd, check=True):
            cmds.append(cmd)
            return SimpleNamespace(stdout="", returncode=0)

        with mock.patch.object(run_scenario, "ssh", fake_ssh), \
             mock.patch.object(run_scenario, "banner", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "wait_with_progress", lambda *a, **k: None):
            run_scenario.reconcile_paper_cpu_limits(cfg)
        checkout_cmds = [c for c in cmds if "checkoutservice" in c]
        self.assertTrue(any("1000m" in c and "500m" in c for c in checkout_cmds))


class TestScenarioYamlsUseFraction(unittest.TestCase):
    def test_s3_s4_have_no_absolute_cpu_limit(self):
        import re
        root = Path(__file__).resolve().parent / "configs"
        names = [
            "scenario_3_baseline.yaml", "scenario_3_retryguard.yaml",
            "scenario_4a_baseline.yaml", "scenario_4a_retryguard.yaml",
            "scenario_4b_baseline.yaml", "scenario_4b_retryguard.yaml",
        ]
        for name in names:
            text = (root / name).read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"(?m)^\s*cpu_limit:\s", text),
                msg=f"{name} still has absolute cpu_limit:",
            )
            self.assertIn("cpu_limit_fraction: 0.1", text, msg=name)


class TestEnsureDetectorQuotaOverlay(unittest.TestCase):
    def test_skips_when_marker_present(self):
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src",
            }
        }
        cmds = []

        def fake_ssh(host, cmd, check=True):
            cmds.append(cmd)
            if "grep" in cmd and "TOPFULL_RUN_QUOTAS_OVERLAY" in cmd:
                return SimpleNamespace(
                    stdout="42:        # TOPFULL_RUN_QUOTAS_OVERLAY\n",
                    returncode=0,
                )
            return SimpleNamespace(stdout="", returncode=0)

        with mock.patch.object(run_scenario, "ssh", fake_ssh), \
             mock.patch.object(run_scenario, "banner", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None):
            run_scenario.ensure_detector_quota_overlay(cfg)
        self.assertFalse(
            any("cp " in c and "overload_detection" in c for c in cmds)
        )

    def test_effective_map_written_shape(self):
        import topfull_cpu_quotas
        constraints = [{
            "deployment": "checkoutservice",
            "method": "cpu_limit",
            "cpu_limit_fraction": 0.1,
        }]
        got = topfull_cpu_quotas.effective_cpu_quotas(constraints)
        self.assertEqual(got["checkoutservice"], 100)


class TestMeshCollectorNetworkWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "envoy_retry_collector_script":
                    "/home/idozacharia/experiments/envoy_retry_collector.py",
            },
            "envoy_retry_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 1,
                "max_workers": 4,
            },
            "log_folder": "baseline_topfull_no_retryguard_sustained_overload_run99",
        }

    @mock.patch("run_scenario.ssh")
    def test_discover_service_pod_ips_uses_master_kubectl(self, mock_ssh):
        mock_ssh.side_effect = [
            SimpleNamespace(returncode=0, stdout="192.168.1.10\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="192.168.1.11\n", stderr=""),
        ]
        got = run_scenario.discover_service_pod_ips(
            self._cfg(), ["frontend", "checkoutservice"]
        )
        self.assertEqual(
            got, {"frontend": "192.168.1.10", "checkoutservice": "192.168.1.11"}
        )
        self.assertEqual(mock_ssh.call_args_list[0].args[0], "topfull-master")
        self.assertIn("app=frontend", mock_ssh.call_args_list[0].args[1])
        self.assertIn("jsonpath={.items[0].status.podIP}", mock_ssh.call_args_list[0].args[1])

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.discover_service_pod_ips")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_uploads_pod_ips_on_master(
        self,
        mock_deploy,
        mock_ssh,
        mock_seed,
        mock_ensure,
        mock_write_json,
        mock_write_script,
        mock_wait,
    ):
        mock_seed.return_value = {"frontend": "192.168.1.10"}
        cfg = self._cfg()
        cfg["envoy_retry_collector"]["services"] = ["frontend"]
        run_scenario.start_envoy_retry_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )
        json_host, json_path, params = mock_write_json.call_args[0][:3]
        self.assertEqual(json_host, "topfull-master")
        self.assertEqual(params["transport"], "network_prometheus")
        self.assertEqual(params["pod_ips"], {"frontend": "192.168.1.10"})
        self.assertEqual(params["max_workers"], 4)
        self.assertNotIn("exec_mode", params)
        script_host, script_path, script_body = mock_write_script.call_args[0][:3]
        self.assertEqual(script_host, "topfull-master")
        self.assertEqual(script_path, "/tmp/rg_envoy_retry.sh")
        self.assertIn("source /home/idozacharia/TopFull/venv/bin/activate", script_body)
        self.assertIn("envoy_retry_collector.py --params /tmp/envoy_retry_params.json", script_body)
        self.assertNotIn("--exec-mode", script_body)
        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if len(c.args) > 1 and "tmux new-session" in c.args[1] and "envoyretry" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)
        self.assertEqual(tmux_calls[0].args[0], "topfull-master")

    @mock.patch("run_scenario.pull_worker_mesh_csvs", create=True)
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_no_worker_pull(self, mock_ssh, mock_write_json, mock_pull):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src",
                "results_base_path": "/home/idozacharia/experiments/results",
            },
            "scenario_id": 2,
            "scenario_name": "sustained_overload",
            "condition": "baseline",
            "run_number": 99,
            "duration_seconds": 600,
            "retryguard": {"enabled": False},
            "log_folder": "test_run",
            "envoy_retry_collector": {
                "enabled": True,
                "poll_interval_seconds": 1,
                "max_workers": 4,
            },
        }
        run_scenario.collect_results(cfg)
        mock_pull.assert_not_called()
        manifest = [
            c.args[2]
            for c in mock_write_json.call_args_list
            if c.args[1].endswith("run_manifest.json")
        ][0]
        erc = manifest["envoy_retry_collector"]
        self.assertEqual(erc["transport"], "network_prometheus")
        self.assertEqual(erc["exec_host"], "topfull-master")
        self.assertNotIn("exec_mode", erc)


if __name__ == "__main__":
    unittest.main()
