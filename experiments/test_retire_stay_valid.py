"""Tests for retire_stay_valid.py. Run: python -m pytest experiments/test_retire_stay_valid.py -v"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import retire_stay_valid as rsv

OLD_A = "Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid."
OLD_B = "Goodput, P95, rejection, and retry numbers do not use that file and remain valid."
OLD_C = "Goodput, P95 and rejection do not use this file."  # a different, true sentence: not rewritten


def test_both_known_sentences_are_rewritten_and_nothing_else():
    text = f"x {OLD_A} y {OLD_B} z {OLD_C}"
    new, n = rsv.rewrite(text)
    assert n == 2
    assert "stay valid" not in new and "remain valid" not in new
    assert OLD_C in new
    assert new.count(rsv.REPLACEMENT) == 2


def test_rewrite_is_idempotent():
    once, _ = rsv.rewrite(OLD_A)
    twice, n = rsv.rewrite(once)
    assert (twice, n) == (once, 0)


def test_the_evidence_report_and_this_plan_are_skipped(tmp_path):
    (tmp_path / rsv.EVIDENCE).write_text(OLD_A, encoding="utf-8")
    (tmp_path / "other.md").write_text(OLD_A, encoding="utf-8")
    changed = rsv.run(tmp_path, write=True)
    assert changed == {"other.md": 1}
    assert (tmp_path / rsv.EVIDENCE).read_text(encoding="utf-8") == OLD_A


def test_dry_run_writes_nothing(tmp_path):
    (tmp_path / "g.md").write_text(OLD_A, encoding="utf-8")
    assert rsv.run(tmp_path, write=False) == {"g.md": 1}
    assert (tmp_path / "g.md").read_text(encoding="utf-8") == OLD_A


def test_crlf_files_keep_their_endings(tmp_path):
    (tmp_path / "g.md").write_bytes(f"a\r\n{OLD_A}\r\n".encode("utf-8"))
    rsv.run(tmp_path, write=True)
    assert b"\r\n" in (tmp_path / "g.md").read_bytes()
