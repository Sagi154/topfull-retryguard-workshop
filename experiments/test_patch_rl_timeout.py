"""Tests for patch_rl_timeout.py. Run: python -m pytest experiments/test_patch_rl_timeout.py -v

The tests patch temp copies of the upstream files in the TopFull submodule. The submodule
itself is never written.
"""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_rl_timeout as prt

UPSTREAM = (Path(__file__).resolve().parent.parent / "TopFull" / "TopFull_master"
            / "online_boutique_scripts" / "src")


@pytest.fixture
def upstream():
    over = UPSTREAM / "overload_detection.py"
    dep = UPSTREAM / "deploy_rl.py"
    if not over.is_file() or not dep.is_file():
        pytest.skip("TopFull submodule is not checked out")
    return over.read_text(encoding="utf-8"), dep.read_text(encoding="utf-8")


def test_patched_files_are_valid_python(upstream):
    over, dep = prt.apply(*upstream)
    ast.parse(over)
    ast.parse(dep)


def test_requests_get_in_current_rps_has_a_timeout(upstream):
    over, _ = prt.apply(*upstream)
    tree = ast.parse(over)
    method = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "current_rps")
    gets = [c for c in ast.walk(method)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == "get"]
    assert gets, "no requests.get left in current_rps"
    assert all(any(k.arg == "timeout" for k in c.keywords) for c in gets)


def test_the_three_callers_catch_the_exception(upstream):
    over, dep = prt.apply(*upstream)
    assert dep.count("except ProxyStatsUnavailable") == 4  # run(rps), run(apply_v2), add_apis, main loop
    assert 'caller="agent"' in dep
    assert 'caller="add_apis"' in dep
    assert 'caller="clustering"' in over


def test_log_lines_are_present(upstream):
    over, dep = prt.apply(*upstream)
    for token in ("RL_RPS_START", "RL_RPS_END", "RL_RPS_TIMEOUT", "RL_CAP_APPLY"):
        assert token in over
    for token in ("RL_LOOP_START", "RL_SKIP"):
        assert token in dep


def test_detector_init_keeps_default_threshold_on_timeout(upstream):
    over, dep = prt.apply(*upstream)
    assert 'caller="init"' in over
    assert "RL_SKIP where=init" in over
    assert "rps = {}" in over
    assert prt.apply(over, dep) == (over, dep)


def test_marker_is_in_both_files_and_apply_is_idempotent(upstream):
    over, dep = prt.apply(*upstream)
    assert prt.MARKER in over and prt.MARKER in dep
    assert prt.apply(over, dep) == (over, dep)


def test_crlf_files_round_trip(upstream):
    over, dep = (t.replace("\r\n", "\n").replace("\n", "\r\n") for t in upstream)
    new_over, new_dep = prt.apply(over, dep)
    assert "\r\n" in new_over and "\n" not in new_over.replace("\r\n", "")
    ast.parse(new_over.replace("\r\n", "\n"))


def test_a_changed_file_is_refused_not_guessed():
    with pytest.raises(prt.PatchError, match="anchor"):
        prt.apply("print('not overload_detection')\n", "print('not deploy_rl')\n")


def test_runner_and_patch_agree_on_the_marker():
    import run_scenario
    assert run_scenario.RL_PATCH_MARKER == prt.MARKER
