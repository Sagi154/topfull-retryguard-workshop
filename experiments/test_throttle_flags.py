"""Unit tests for experiments/throttle_flags.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import throttle_flags  # noqa: E402
from test_hold_clock import E, iso, write_csv  # noqa: E402

HEADER = ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"]


def make_hold(root, scenario_dir, variant, name, fresh_until=99, warnings=0,
              total=100, csv=True):
    run = Path(root) / scenario_dir / variant / name
    run.mkdir(parents=True)
    if csv:
        rows = []
        for s in range(total):
            ok = int(s % 5 == 0 and s <= fresh_until)
            rows.append([iso(E + s), "getproduct", 150.0, 10.0, ok, ok])
        write_csv(run / "topfull_throttle.csv", HEADER, rows)
    lines = ["2026-10-13T00:00:00Z  START  x"]
    lines += [f"2026-10-13T00:00:{i % 60:02d}Z  WARNING  thresholds fetch failed: timed out"
              for i in range(warnings)]
    (run / "topfull_throttle_collector.log").write_text("\n".join(lines), encoding="utf-8")
    return run


def hold(name, on=True, flagged=True, warnings=5, tgap=60.0, agap=60.0, tpct=50.0, apct=50.0,
         scenario="S2", mode="burst", variant=None):
    variant = variant or ("both" if on else "rg_only")
    return throttle_flags.HoldFlag(
        path=f"S2_sustained_overload_{mode}/{variant}/{name}", scenario=scenario, mode=mode,
        variant=variant, name=name, topfull_on=on, flagged=flagged, warnings=warnings,
        first_warning="2026-10-13T00:00:00Z" if warnings else None,
        threshold_gap_s=tgap, admitted_gap_s=agap,
        threshold_stale_pct=tpct, admitted_stale_pct=apct,
    )


class TestScan(unittest.TestCase):
    def scan(self, build):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            return throttle_flags.scan(Path(tmp))

    def test_clean_hold_is_not_flagged(self):
        flags = self.scan(lambda r: make_hold(r, "S2_sustained_overload_burst", "both", "run_a"))
        self.assertEqual(len(flags), 1)
        h = flags[0]
        self.assertFalse(h.flagged)
        self.assertEqual(h.threshold_stale_pct, 0.0)
        self.assertTrue(h.topfull_on)
        self.assertEqual((h.scenario, h.mode, h.variant, h.name),
                         ("S2", "burst", "both", "run_a"))

    def test_tail_stale_hold_reports_gap_and_percent_of_span(self):
        flags = self.scan(lambda r: make_hold(
            r, "S4A_topology_position_normal", "tf_only", "run_b", fresh_until=20))
        h = flags[0]
        self.assertTrue(h.flagged)
        self.assertEqual(h.scenario, "S4A")
        self.assertEqual(h.mode, "normal")
        self.assertEqual(h.threshold_gap_s, 79.0)
        self.assertAlmostEqual(h.threshold_stale_pct, 79 / 99 * 100, places=1)
        self.assertAlmostEqual(h.admitted_stale_pct, 79 / 99 * 100, places=1)
        self.assertEqual(h.warnings, 0)

    def test_fetch_warnings_on_a_topfull_off_hold_do_not_flag_it(self):
        flags = self.scan(lambda r: make_hold(
            r, "S2_sustained_overload_burst", "rg_only", "run_c", warnings=3))
        h = flags[0]
        self.assertFalse(h.flagged)
        self.assertFalse(h.topfull_on)
        self.assertEqual(h.warnings, 3)
        self.assertEqual(h.threshold_stale_pct, 0.0)
        self.assertEqual(h.first_warning, "2026-10-13T00:00:00Z")

    def test_missing_csv_is_not_a_flag_even_with_log_warnings(self):
        flags = self.scan(lambda r: make_hold(
            r, "S1_normal_operation_normal", "tf_only", "run_d", csv=False, warnings=2))
        self.assertFalse(flags[0].flagged)

    def test_scan_is_sorted_and_uses_forward_slashes(self):
        def build(root):
            make_hold(root, "S2_sustained_overload_burst", "both", "b")
            make_hold(root, "S1_normal_operation_normal", "both", "a")
        flags = self.scan(build)
        self.assertEqual([h.path for h in flags], [
            "S1_normal_operation_normal/both/a", "S2_sustained_overload_burst/both/b"])


class TestLabels(unittest.TestCase):
    def test_label_separates_topfull_on_and_off(self):
        self.assertEqual(throttle_flags.label(hold("a", on=True)), throttle_flags.TF_ON_LABEL)
        self.assertEqual(throttle_flags.label(hold("a", on=False)), throttle_flags.TF_OFF_LABEL)

    def test_name_pattern_does_not_match_a_longer_name(self):
        pattern = throttle_flags.name_pattern("final_4a_x_run1")
        self.assertTrue(pattern.search("folders `final_4a_x_run1` and more"))
        self.assertFalse(pattern.search("folder final_4a_x_run1_r2"))


STATUS_TEXT = """# STATUS

## Done

- **Matrix A (2026-10-12)** — folders `hold_a` and `hold_b`, 600 s.
- **Matrix B (2026-10-13)** — folder `hold_c`.

## Next free slots

- hold_a is also listed here and must not be touched.
"""


class TestStatusLines(unittest.TestCase):
    def flags(self):
        return [
            hold("hold_a", on=True, warnings=196, tgap=494, agap=494, tpct=69.1, apct=69.1),
            hold("hold_b", on=True, flagged=False),
            hold("hold_c", on=False, flagged=False, warnings=0, tgap=55, agap=55, tpct=6.3, apct=6.3),
            hold("hold_z", on=True, warnings=12, tgap=5, agap=300, tpct=0.0, apct=60.0),
        ]

    def test_sentence_names_flag_stale_time_and_topfull_state(self):
        text = throttle_flags.status_sentence(self.flags()[0])
        self.assertIn("`hold_a` FLAGGED", text)
        self.assertIn("196 fetch warnings", text)
        self.assertIn("threshold stale 494 s (69.1% of span)", text)
        self.assertIn("admitted stale 494 s (69.1% of span)", text)

    def test_gap_only_sentence_uses_the_10_s_rule(self):
        text = throttle_flags.status_sentence(
            hold("hold_gap", on=True, warnings=0, tgap=55, agap=55, tpct=6.3, apct=6.3))
        self.assertIn("no fetch warnings, 10 s stale-gap rule only", text)

    def test_a_topfull_off_hold_is_not_a_status_line(self):
        out = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        # Matrix B already names `hold_c`. The generated sentence must not.
        self.assertIn("folder `hold_c`.", out)
        self.assertNotIn("`hold_c` FLAGGED", out)
        self.assertNotIn("`hold_c` " + throttle_flags.TF_OFF_LABEL, out)
        self.assertNotIn(throttle_flags.TF_OFF_LABEL, out)

    def test_line_goes_on_the_bullet_that_names_the_hold(self):
        out = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        bullets = [l for l in out.split("\n") if l.startswith("- **Matrix")]
        self.assertIn(throttle_flags.AUDIT_TAG, bullets[0])
        self.assertIn("`hold_a` FLAGGED", bullets[0])
        self.assertNotIn("hold_b` FLAGGED", bullets[0])
        self.assertNotIn(throttle_flags.AUDIT_TAG, bullets[1])

    def test_unmatched_hold_goes_to_one_backfill_bullet_before_next_free_slots(self):
        out = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        lines = out.split("\n")
        backfill = [i for i, l in enumerate(lines) if l.startswith("- **Throttle flag backfill")]
        self.assertEqual(len(backfill), 1)
        self.assertIn("`hold_z` FLAGGED", lines[backfill[0]])
        self.assertLess(backfill[0], lines.index("## Next free slots"))
        self.assertEqual(lines[lines.index("## Next free slots") - 1], "")

    def test_sections_after_done_are_untouched_and_apply_is_idempotent(self):
        once = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        self.assertIn("- hold_a is also listed here and must not be touched.", once)
        self.assertNotIn("hold_a` FLAGGED", once.split("## Next free slots")[1])
        self.assertEqual(throttle_flags.apply_status(once, self.flags()), once)

    def test_no_flagged_holds_leaves_the_text_alone(self):
        clean = [hold("hold_a", flagged=False)]
        self.assertEqual(throttle_flags.apply_status(STATUS_TEXT, clean), STATUS_TEXT)


class TestGuideScan(unittest.TestCase):
    def scan(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                (Path(tmp) / name).write_text(text, encoding="utf-8")
            flags = [hold("hold_a", on=True), hold("hold_b", on=False), hold("hold_c", flagged=False)]
            return throttle_flags.scan_guides(flags, Path(tmp))

    def test_a_guide_that_names_the_flag_has_nothing_missing(self):
        rows = self.scan({"g1.md": "## Throttle data quality\n\n| hold_a | **FLAGGED** | 5 |\n"})
        self.assertEqual(len(rows), 1)
        self.assertEqual([h.name for h in rows[0].named], ["hold_a"])
        self.assertEqual(rows[0].missing, ())
        self.assertTrue(rows[0].has_section)

    def test_a_guide_that_only_mentions_the_hold_is_missing_it(self):
        rows = self.scan({"g2.md": "Columns: hold_a, hold_b.\n"})
        self.assertEqual([h.name for h in rows[0].missing], ["hold_a", "hold_b"])
        self.assertFalse(rows[0].has_section)

    def test_clean_holds_and_unrelated_guides_are_ignored(self):
        rows = self.scan({"g3.md": "hold_c only.\n", "g4.md": "nothing here\n"})
        self.assertEqual(rows, [])

    def test_note_has_the_item_17_facts_and_the_off_variant_wording(self):
        on = throttle_flags.guide_note(hold("hold_a", on=True, warnings=196, tgap=494, agap=494))
        self.assertIn("`hold_a` is FLAGGED", on)
        self.assertIn("carried, not measured", on)
        self.assertIn("Goodput, P95, rejection, and retry numbers", on)
        off = throttle_flags.guide_note(hold("hold_b", on=False))
        self.assertIn("no admission cap to lose", off)

    def test_markdown_lists_every_guide_with_counts(self):
        rows = self.scan({"g2.md": "Columns: hold_a, hold_b.\n"})
        text = throttle_flags.guides_markdown(rows)
        self.assertIn("| g2.md | 2 | 1 | 0 | `hold_a`, `hold_b` |", text)

    def test_proxy_fd_evidence_note_is_not_scanned(self):
        rows = self.scan({
            "2026-10-15-proxy-fd-evidence-flagged-holds.md": "hold_a is mentioned here.\n",
        })
        self.assertEqual(rows, [])


class TestRerunList(unittest.TestCase):
    def flags(self):
        return [
            hold("final_s2_both_burst_run1", on=True, tgap=494, agap=494, tpct=69.1, apct=69.1),
            hold("final_s2_both_burst_run2", on=True, flagged=False),
            hold("study6_s2_normal_rgtf1_rep1", on=True, tgap=5, agap=300, tpct=0.0, apct=60.0,
                 mode="normal"),
            hold("final_s2_rg_only_burst_run2", on=False),
        ]

    def test_numbers_affected_follows_which_reads_went_stale(self):
        both = throttle_flags.numbers_affected(self.flags()[0])
        self.assertIn("TopFull cap lines", both)
        self.assertIn("admitted req/s", both)
        admitted_only = throttle_flags.numbers_affected(self.flags()[2])
        self.assertNotIn("TopFull cap lines", admitted_only)
        self.assertIn("admitted req/s", admitted_only)
        none = throttle_flags.numbers_affected(hold("x", tgap=5, agap=5))
        self.assertIn("fetch warnings only", none)

    def test_cell_key_strips_the_run_suffix_and_skips_study_folders(self):
        self.assertEqual(throttle_flags.cell_key(hold("final_4a_constrained_both_burst_run3_r2")),
                         "final_4a_constrained_both_burst")
        self.assertIsNone(throttle_flags.cell_key(hold("study6_s2_normal_rgtf1_rep1")))

    def test_only_topfull_on_flags_get_a_row(self):
        text = throttle_flags.rerun_markdown(self.flags())
        self.assertIn("`final_s2_both_burst_run1`", text)
        self.assertIn("`study6_s2_normal_rgtf1_rep1`", text)
        self.assertNotIn("final_s2_rg_only_burst_run2", text)
        self.assertNotIn("final_s2_both_burst_run2", text)
        self.assertNotIn("Pending", text)
        self.assertNotIn(throttle_flags.TF_OFF_LABEL, text)

    def test_locked_set_and_cell_counts_and_blank_decision(self):
        text = throttle_flags.rerun_markdown(self.flags())
        row = next(l for l in text.splitlines() if l.startswith("| `final_s2_both_burst_run1`"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[1], "yes")
        self.assertEqual(cells[6], "1 clean / 1 flagged")
        self.assertEqual(cells[7], "")
        study = next(l for l in text.splitlines() if l.startswith("| `study6_s2_normal_rgtf1_rep1`"))
        study_cells = [c.strip() for c in study.strip("|").split("|")]
        self.assertEqual(study_cells[1], "no")
        self.assertEqual(study_cells[6], "n/a")

    def test_scenarios_are_grouped_in_order(self):
        text = throttle_flags.rerun_markdown(self.flags())
        self.assertIn("### S2", text)
        self.assertNotIn("## Pending", text)


if __name__ == "__main__":
    unittest.main()
