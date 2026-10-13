"""Unit tests for experiments/hold_clock.py."""
import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hold_clock  # noqa: E402

E = 1_760_000_000.0
LOCUST_HEADER = ["RPS", "Fail", "Goodput", "Latency95", "Latency99"]


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def frontend_total(epoch: float) -> float:
    """Cumulative frontend requests: load on from E+20 to E+80, rate 50 + (t - E - 20)."""
    x = min(max(epoch - E - 20, 0.0), 60.0)
    return 50 * x + 0.5 * x * x


def make_run(root: Path, stamped: bool = False) -> Path:
    """Synthetic run: 1 s mesh polls E..E+100, 55 Locust rows 1.1 s apart from E+20."""
    run = root / "run"
    write_csv(run / "service_inbound.csv",
              ["timestamp", "service", "total", "2xx", "5xx", "resets"],
              [[iso(E + k), "frontend", frontend_total(E + k), frontend_total(E + k), 0, 0]
               for k in range(101)])
    rows = []
    for i in range(55):
        rps = 50 + 1.1 * i
        row = [rps, 0, rps, 100, 0]
        if stamped:
            row.append(hold_clock.format_utc(E + 20 + 1.1 * i))
        rows.append(row)
    header = LOCUST_HEADER + (["timestamp"] if stamped else [])
    for name in hold_clock.LOCUST_FILES:
        write_csv(run / f"{name}.csv", header, rows)
    return run


class TestFit(unittest.TestCase):
    def test_fit_recovers_start_and_spacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = hold_clock.compute_clock(make_run(Path(tmp)))
        self.assertEqual(clock["method"], "fit")
        self.assertEqual(clock["anchor_rows"], [0, 54])
        start = hold_clock.parse_utc(clock["start_utc"])
        self.assertLessEqual(abs(start - (E + 20)), 1.5)
        self.assertLess(abs(clock["spacing_s"] - 1.1), 0.01)
        self.assertGreater(clock["correlation"], 0.99)
        self.assertFalse(clock["flagged"])

    def test_stamped_run_uses_stamps_and_records_fit_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = hold_clock.compute_clock(make_run(Path(tmp), stamped=True))
        self.assertEqual(clock["method"], "stamped")
        self.assertEqual(clock["start_utc"], hold_clock.format_utc(E + 20))
        self.assertAlmostEqual(clock["spacing_s"], 1.1, delta=0.002)
        self.assertLessEqual(abs(clock["fit_check"]["start_error_s"]), 1.5)


if __name__ == "__main__":
    unittest.main()
