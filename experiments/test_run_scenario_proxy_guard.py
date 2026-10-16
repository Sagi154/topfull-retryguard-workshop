"""Proxy start-up guard and catalog probe tolerance in the hold runner."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_scenario  # noqa: E402
import topfull_cpu_quotas  # noqa: E402

CLEAN = "getproduct=10000.0/getcart=10000.0/postcart=10000.0/emptycart=10000.0/postcheckout=10000.0/"
DIRTY = "getproduct=10.0/getcart=10.0/postcart=417.8/emptycart=0.0/postcheckout=10.0/"


def test_parse_proxy_thresholds_reads_every_api():
    parsed = run_scenario.parse_proxy_thresholds(CLEAN)
    assert parsed["getproduct"] == 10000.0
    assert len(parsed) == 5


def test_parse_proxy_thresholds_ignores_junk():
    assert run_scenario.parse_proxy_thresholds("") == {}
    assert run_scenario.parse_proxy_thresholds("garbage/a=b/") == {}


def test_cap_problems_empty_when_uncapped():
    assert run_scenario.proxy_cap_problems(run_scenario.parse_proxy_thresholds(CLEAN)) == []


def test_cap_problems_names_leftover_caps_and_zero():
    problems = run_scenario.proxy_cap_problems(run_scenario.parse_proxy_thresholds(DIRTY))
    assert "emptycart=0" in problems
    assert "postcart=417.8" in problems
    assert len(problems) == 5


def test_cap_problems_flags_unreadable_proxy():
    assert run_scenario.proxy_cap_problems({}) == ["no thresholds returned by the proxy"]


def _ssh_ok():
    return mock.Mock(stdout="", returncode=0)


def test_ensure_proxy_uncapped_passes_without_restart():
    restart = mock.Mock()
    with mock.patch.object(run_scenario, "read_proxy_thresholds",
                           return_value=run_scenario.parse_proxy_thresholds(CLEAN)):
        run_scenario.ensure_proxy_uncapped("m", "/src", restart)
    restart.assert_not_called()


def test_ensure_proxy_uncapped_restarts_a_dirty_proxy_then_passes():
    restart = mock.Mock()
    reads = [run_scenario.parse_proxy_thresholds(DIRTY),
             run_scenario.parse_proxy_thresholds(CLEAN)]
    with mock.patch.object(run_scenario, "read_proxy_thresholds", side_effect=reads), \
            mock.patch.object(run_scenario, "ssh", return_value=_ssh_ok()):
        run_scenario.ensure_proxy_uncapped("m", "/src", restart)
    restart.assert_called_once()


def test_ensure_proxy_uncapped_aborts_after_two_restarts():
    restart = mock.Mock()
    dirty = run_scenario.parse_proxy_thresholds(DIRTY)
    with mock.patch.object(run_scenario, "read_proxy_thresholds", return_value=dirty), \
            mock.patch.object(run_scenario, "ssh", return_value=_ssh_ok()):
        with pytest.raises(RuntimeError, match="not 10000"):
            run_scenario.ensure_proxy_uncapped("m", "/src", restart)
    assert restart.call_count == 2


def test_catalog_probe_is_default_when_catalog_is_not_constrained():
    assert topfull_cpu_quotas.probe_settings_for([]) == topfull_cpu_quotas.DEFAULT_PROBE
    other = [{"deployment": "checkoutservice", "method": "cpu_limit",
              "cpu_limit_millicores": 200}]
    assert topfull_cpu_quotas.probe_settings_for(other) == topfull_cpu_quotas.DEFAULT_PROBE


def test_catalog_probe_is_tolerant_when_catalog_is_constrained():
    constrained = [{"deployment": "productcatalogservice", "method": "cpu_limit",
                    "cpu_limit_millicores": 100}]
    assert topfull_cpu_quotas.probe_settings_for(constrained) == topfull_cpu_quotas.TOLERANT_PROBE
    assert topfull_cpu_quotas.TOLERANT_PROBE["timeoutSeconds"] == 5


def test_catalog_probe_restore_returns_manifest_default():
    constrained = [{"deployment": "productcatalogservice", "method": "cpu_limit",
                    "cpu_limit_millicores": 100}]
    assert topfull_cpu_quotas.probe_settings_for(constrained, restore=True) == {
        "timeoutSeconds": 1, "failureThreshold": 3}


def test_read_proxy_soft_limit_takes_the_lowest_value():
    out = mock.Mock(stdout="1048576\n1024\n", returncode=0)
    with mock.patch.object(run_scenario, "ssh", return_value=out):
        assert run_scenario.read_proxy_soft_limit("m") == 1024


def test_read_proxy_soft_limit_is_none_without_a_proxy():
    with mock.patch.object(run_scenario, "ssh", return_value=mock.Mock(stdout="", returncode=0)):
        assert run_scenario.read_proxy_soft_limit("m") is None


def test_read_proxy_soft_limit_treats_unlimited_as_large():
    with mock.patch.object(run_scenario, "ssh", return_value=mock.Mock(stdout="unlimited\n", returncode=0)):
        assert run_scenario.read_proxy_soft_limit("m") == run_scenario.NOFILE_UNLIMITED


def test_limit_command_reads_the_go_binary_not_the_go_tool():
    seen = []

    def fake(host, cmd, check=True):
        seen.append(cmd)
        return mock.Mock(stdout="65536\n", returncode=0)

    with mock.patch.object(run_scenario, "ssh", fake):
        run_scenario.read_proxy_soft_limit("m")
    assert "[/]exe/proxy_online_boutique" in seen[0]
    assert "/proc/$p/limits" in seen[0]
    assert "Max open files" in seen[0]


def test_verify_returns_a_raised_limit():
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", return_value=1048576), \
            mock.patch.object(run_scenario, "step"):
        assert run_scenario.verify_proxy_nofile("m") == 1048576


def test_verify_aborts_when_the_limit_is_still_1024():
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", return_value=1024):
        with pytest.raises(RuntimeError, match="1024"):
            run_scenario.verify_proxy_nofile("m")


def test_verify_waits_for_the_proxy_pid_to_appear():
    reads = [None, None, 65536]
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", side_effect=reads) as read, \
            mock.patch.object(run_scenario.time, "sleep") as sleep, \
            mock.patch.object(run_scenario, "step"):
        assert run_scenario.verify_proxy_nofile("m") == 65536
    assert read.call_count == 3
    assert sleep.call_count == 2


def test_verify_aborts_when_the_limit_cannot_be_read():
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", return_value=None), \
            mock.patch.object(run_scenario.time, "sleep"):
        with pytest.raises(RuntimeError, match="could not read"):
            run_scenario.verify_proxy_nofile("m")


def _rl_off_cfg():
    return {
        "infra": {"master_ssh_host": "m", "topfull_src_path": "/src",
                  "venv_activate": "/venv/bin/activate"},
        "topfull_rl": {"enabled": False},
    }


def test_start_master_stack_verifies_the_limit_before_the_cap_check():
    order = []
    with mock.patch.object(run_scenario, "write_remote_script"), \
            mock.patch.object(run_scenario, "ssh", return_value=_ssh_ok()), \
            mock.patch.object(run_scenario, "wait_with_progress"), \
            mock.patch.object(run_scenario, "verify_proxy_nofile",
                              side_effect=lambda *a, **k: order.append("nofile")), \
            mock.patch.object(run_scenario, "ensure_proxy_uncapped",
                              side_effect=lambda *a, **k: order.append("caps")):
        run_scenario.start_master_stack(_rl_off_cfg())
    assert order[:2] == ["nofile", "caps"]


def test_a_low_limit_stops_the_stack_before_the_cap_check():
    with mock.patch.object(run_scenario, "write_remote_script"), \
            mock.patch.object(run_scenario, "ssh", return_value=_ssh_ok()), \
            mock.patch.object(run_scenario, "wait_with_progress"), \
            mock.patch.object(run_scenario, "verify_proxy_nofile",
                              side_effect=RuntimeError("soft limit 1024")), \
            mock.patch.object(run_scenario, "ensure_proxy_uncapped") as caps:
        with pytest.raises(RuntimeError, match="1024"):
            run_scenario.start_master_stack(_rl_off_cfg())
    caps.assert_not_called()


def test_verify_rl_patch_passes_when_the_marker_is_in_both_files():
    out = mock.Mock(stdout="2\n", returncode=0)
    with mock.patch.object(run_scenario, "ssh", return_value=out) as ssh, \
            mock.patch.object(run_scenario, "step"):
        run_scenario.verify_rl_patch("m", "/src")
    cmd = ssh.call_args[0][1]
    assert "RL_TIMEOUT_PATCH v1" in cmd
    assert "/src/overload_detection.py" in cmd and "/src/deploy_rl.py" in cmd


def test_verify_rl_patch_aborts_when_a_file_lacks_the_marker():
    out = mock.Mock(stdout="1\n", returncode=0)
    with mock.patch.object(run_scenario, "ssh", return_value=out):
        with pytest.raises(RuntimeError, match="patch_rl_timeout"):
            run_scenario.verify_rl_patch("m", "/src")


def test_rl_start_checks_the_patch_and_rl_off_does_not():
    cfg = _rl_off_cfg()
    with mock.patch.object(run_scenario, "write_remote_script"), \
            mock.patch.object(run_scenario, "ssh", return_value=mock.Mock(stdout="x deploy_rl.py", returncode=0)), \
            mock.patch.object(run_scenario, "wait_with_progress"), \
            mock.patch.object(run_scenario, "verify_proxy_nofile"), \
            mock.patch.object(run_scenario, "ensure_proxy_uncapped"), \
            mock.patch.object(run_scenario, "verify_rl_patch") as patch_check:
        run_scenario.start_master_stack(cfg)
        patch_check.assert_not_called()
        cfg["topfull_rl"] = {"enabled": True}
        run_scenario.start_master_stack(cfg)
        patch_check.assert_called_once_with("m", "/src")

