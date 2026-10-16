"""Tests for proxy_fd_decisions.py. Run: python -m pytest experiments/test_proxy_fd_decisions.py -v"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import proxy_fd_decisions as pfd

HEADER = "timestamp,api,threshold,admitted_rps,threshold_fresh,admitted_fresh\n"


def make_hold(root: Path, scenario: str, variant: str, name: str, *, flagged: bool):
    d = root / scenario / variant / name
    d.mkdir(parents=True)
    rows = ["2026-10-13T00:00:00Z,getproduct,10000,0,1,1"]
    rows.append("2026-10-13T00:%s:00Z,getproduct,10000,0,1,1" % ("05" if flagged else "00"))
    (d / "topfull_throttle.csv").write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return d


def make_yaml(configs: Path, rel: str, run_number: int):
    p = configs / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"run_number: {run_number}\nlog_folder: x_run{run_number}\n", encoding="utf-8")


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "final results"
    configs = tmp_path / "final_configs"
    for rel, n in {
        "2/s2_tf_only.yaml": 4, "2/s2_both_burst.yaml": 4, "2/s2_both_normal.yaml": 3,
        "2/s2_rg_only_normal.yaml": 3,
        "4/4a_constrained/4a_constrained_rg_only_burst.yaml": 7,
        "4/4a_constrained/4a_constrained_rg_only_normal.yaml": 5,
        "4/4a_constrained/4a_constrained_tf_only.yaml": 5,
        "4/4a_constrained/4a_constrained_both_burst.yaml": 5,
    }.items():
        make_yaml(configs, rel, n)
    # one of the eleven, flagged
    make_hold(root, "S2_sustained_overload_normal", "tf_only", "final_s2_tf_only_run2", flagged=True)
    # a confounded S4A-constrained hold (flagged, not one of the three affected)
    make_hold(root, "S4A_topology_position_burst", "both", "final_4a_constrained_both_burst_run3", flagged=True)
    # a healthy-through-stall S4A-unconstrained hold (flagged)
    make_hold(root, "S4A_topology_position_burst", "both", "final_4a_unconstrained_both_burst_run2_r2", flagged=True)
    # a clean hold and a folder the audit never saw
    make_hold(root, "S1_normal_operation_normal", "tf_only", "final_s1_tf_only_run1", flagged=False)
    make_hold(root, "S2_sustained_overload_normal", "tf_only", "final_s2_tf_only_run3", flagged=True)
    return root, configs


def test_legacy_flag_counts_every_variant(tree):
    root, _ = tree
    rows = pfd.legacy_flagged(root)
    flagged = {name for name, _variant, f in rows if f}
    assert flagged == {"final_s2_tf_only_run2", "final_4a_constrained_both_burst_run3",
                       "final_4a_unconstrained_both_burst_run2_r2", "final_s2_tf_only_run3"}


def test_next_slot_reads_the_yaml(tree):
    _, configs = tree
    assert pfd.next_slot(configs, "2/s2_tf_only.yaml") == 4


def test_the_eleven_rows_are_the_evidence_reports_eleven():
    names = [h.name for h in pfd.AFFECTED]
    assert len(names) == 11 and len(set(names)) == 11
    assert names[:6] == [
        "final_s2_both_burst_run1", "study6_s2_normal_rgtf1_rep1", "study6_s2_normal_rgtf1_rep2",
        "study6_s2_normal_rgtf0_rep1", "study6_s2_normal_rgtf0_rep2", "final_s2_tf_only_run2",
    ]
    assert names[6:9] == [
        "final_4a_constrained_rg_only_burst_run2",
        "final_4a_constrained_rg_only_normal_run2_r2",
        "final_4a_constrained_tf_only_run2",
    ]
    assert names[9:] == ["final_s2_tf_only_run3", "final_s2_both_burst_run3"]


def test_render_has_all_sections_and_blank_decisions(tree):
    root, configs = tree
    audit = "`final_s2_tf_only_run2` and `final_4a_constrained_both_burst_run3` are in the audit."
    text = pfd.render(root, configs, audit)
    for heading in ("## A. Materially affected", "## B. Flagged, not recommended", "## C. Confounded",
                    "## D. Not in the 2026-10-15 audit"):
        assert heading in text
    row = next(l for l in text.splitlines() if l.startswith("| `final_s2_tf_only_run2`"))
    assert row.endswith("|  |")            # blank Decision cell
    assert "| 4 |" in row                   # next free slot from the YAML
    assert "| yes |" in row                 # in the locked final_ set
    c_row = next(l for l in text.splitlines() if l.startswith("| `final_4a_constrained_both_burst_run3`"))
    assert "| 5 |" in c_row and c_row.endswith("|  |")


def test_unconstrained_flagged_holds_are_not_recommended(tree):
    root, configs = tree
    text = pfd.render(root, configs, "")
    b = text.split("## B.")[1].split("## C.")[0]
    assert "final_4a_unconstrained_both_burst_run2_r2" in b
    assert "healthy" in b


def test_holds_missing_from_the_audit_are_listed(tree):
    root, configs = tree
    audit = "`final_s2_tf_only_run2` `final_4a_constrained_both_burst_run3` `final_4a_unconstrained_both_burst_run2_r2` `final_s1_tf_only_run1`"
    text = pfd.render(root, configs, audit)
    d = text.split("## D.")[1]
    assert "`final_s2_tf_only_run3`" in d
    assert "`final_s2_tf_only_run2`" not in d
