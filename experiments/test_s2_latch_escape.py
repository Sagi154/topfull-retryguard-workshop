"""Unit tests for s2_latch_escape (synthetic series only; no result folders)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_latch_escape as esc


def tick(t, arrival, hole=False, sojourn_ms=None, concurrency=None, usable=None):
    if usable is None:
        usable = (not hole) and arrival is not None
    return {
        "t": float(t),
        "timestamp": f"2026-01-01T00:00:{int(t):02d}Z" if t < 60 else "2026-01-01T00:01:00Z",
        "dt": 5.0 if hole else 1.0,
        "hole": hole,
        "usable": usable,
        "arrival": None if hole else arrival,
        "sojourn_ms": sojourn_ms,
        "concurrency": concurrency,
        "p50_ms": None,
        "d_count": 1 if concurrency is not None else 0,
    }


class TestFirstSustained(unittest.TestCase):
    def test_never_when_below(self):
        series = [tick(i, 100) for i in range(20)]
        self.assertIsNone(esc.first_sustained(series, 560, 5))

    def test_detects_first_crossing(self):
        series = [tick(i, 100) for i in range(10)]
        series += [tick(10 + i, 600) for i in range(5)]
        series += [tick(20 + i, 100) for i in range(5)]
        self.assertEqual(esc.first_sustained(series, 560, 5), 10.0)

    def test_short_blip_does_not_count(self):
        series = [tick(i, 100) for i in range(5)]
        series += [tick(5 + i, 600) for i in range(3)]  # only 3
        series += [tick(8 + i, 100) for i in range(5)]
        self.assertIsNone(esc.first_sustained(series, 560, 5))

    def test_hole_resets_streak(self):
        series = [tick(i, 600) for i in range(3)]
        series.append(tick(3, None, hole=True))
        series += [tick(4 + i, 600) for i in range(4)]
        # After hole, only 4 usable high ticks — need 5.
        self.assertIsNone(esc.first_sustained(series, 560, 5))
        series += [tick(8, 600)]
        self.assertEqual(esc.first_sustained(series, 560, 5), 4.0)

    def test_edge_exactly_threshold_fails(self):
        series = [tick(i, 560) for i in range(10)]
        self.assertIsNone(esc.first_sustained(series, 560, 5))
        series = [tick(i, 560.1) for i in range(5)]
        self.assertEqual(esc.first_sustained(series, 560, 5), 0.0)


class TestRateSeriesAndLittles(unittest.TestCase):
    def test_concurrency_is_sum_over_dt(self):
        # Two rows 1 s apart: delta sum_ms = 2000, count = 10 -> sojourn 200 ms,
        # concurrency = 2.0 / 1 = 2.0
        rows = [
            {"timestamp": "2026-01-01T00:00:00Z", "total": "0",
             "rq_time_sum_ms": "0", "rq_time_count": "0",
             "rq_time_buckets": "{}"},
            {"timestamp": "2026-01-01T00:00:01Z", "total": "10",
             "rq_time_sum_ms": "2000", "rq_time_count": "10",
             "rq_time_buckets": "{}"},
        ]
        series = esc.rate_series(rows, esc.ts("2026-01-01T00:00:00Z"))
        self.assertEqual(len(series), 1)
        self.assertAlmostEqual(series[0]["arrival"], 10.0)
        self.assertAlmostEqual(series[0]["sojourn_ms"], 200.0)
        self.assertAlmostEqual(series[0]["concurrency"], 2.0)
        self.assertFalse(series[0]["hole"])

    def test_scrape_hole_marked(self):
        rows = [
            {"timestamp": "2026-01-01T00:00:00Z", "total": "0",
             "rq_time_sum_ms": "0", "rq_time_count": "0"},
            {"timestamp": "2026-01-01T00:00:05Z", "total": "50",
             "rq_time_sum_ms": "5000", "rq_time_count": "50"},
        ]
        series = esc.rate_series(rows, esc.ts("2026-01-01T00:00:00Z"))
        self.assertTrue(series[0]["hole"])
        self.assertIsNone(series[0]["arrival"])
        self.assertFalse(series[0]["usable"])


class TestLatchOnset(unittest.TestCase):
    def test_onset_from_first_sojourn_hit(self):
        # Sparse sojourn (every 5th tick) still counts as onset on first hit.
        series = []
        for i in range(10):
            soj = 500.0 if i == 5 else None
            series.append(tick(i, 150, sojourn_ms=soj))
        self.assertEqual(esc.latch_onset(series), 5.0)

    def test_fallback_to_sustained_arrival(self):
        series = [tick(i, 20, sojourn_ms=100) for i in range(3)]
        series += [tick(3 + i, 150, sojourn_ms=None) for i in range(5)]
        self.assertEqual(esc.latch_onset(series), 3.0)

    def test_no_onset_without_arrival(self):
        series = [tick(i, 10, sojourn_ms=500) for i in range(10)]
        # sojourn hits but arrival too low for primary; fallback also fails
        self.assertIsNone(esc.latch_onset(series))


class TestReconcileAndSurvival(unittest.TestCase):
    def test_reconcile_matrix(self):
        self.assertEqual(
            esc.reconcile_label({"old_label": "released", "escaped": True}), "agree")
        self.assertEqual(
            esc.reconcile_label({"old_label": "sticky", "escaped": False}), "agree")
        self.assertEqual(
            esc.reconcile_label({"old_label": "other", "escaped": False}),
            "other_as_never")
        self.assertEqual(
            esc.reconcile_label({"old_label": "sticky", "escaped": True}),
            "disagree_sticky_escaped")

    def test_survival(self):
        scores = [
            {"escaped": True, "escape_s": 100},
            {"escaped": True, "escape_s": 250},
            {"escaped": False, "escape_s": None},
            {"escaped": False, "escape_s": None},
        ]
        s = esc.survival(scores, horizons=(120, 300, 600))
        # At 120: runs with escape>120 or never = 250, never, never = 3/4
        self.assertAlmostEqual(s[120], 0.75)
        # At 300: only the two never = 2/4
        self.assertAlmostEqual(s[300], 0.5)
        self.assertAlmostEqual(s[600], 0.5)


class TestTailTrim(unittest.TestCase):
    def test_service_rows_drops_last_five(self):
        inbound = [
            {"service": "frontend", "timestamp": f"2026-01-01T00:00:{i:02d}Z",
             "total": str(i)}
            for i in range(20)
        ]
        rows = esc.service_rows(inbound, "frontend")
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[-1]["total"], "14")


if __name__ == "__main__":
    unittest.main()
