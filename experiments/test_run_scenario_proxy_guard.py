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
