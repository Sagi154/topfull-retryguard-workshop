"""
test_mentor_charts.py — Tests for the mentor_charts.py orchestration
script against a small synthetic campaign folder (no dependency on the
real experiments/results/campaign_48/ data).

Run:
    python experiments/test_mentor_charts.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mentor_charts as mc


def _write_run_folder(run_dir: Path, goodput_values: list[float], with_retryguard_log: bool) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    n = len(goodput_values)
    pd.DataFrame(
        {
            "RPS": goodput_values,
            "Fail": [0.0] * n,
            "Goodput": goodput_values,
            "Latency95": [200.0] * n,
            "Latency99": [0.0] * n,
        }
    ).to_csv(run_dir / "total.csv", index=False)
    if with_retryguard_log:
        (run_dir / "retryguard.log").write_text(
            "2026-09-05T16:52:18Z  START  threshold=0.20\n", encoding="utf-8"
        )


class TestGenerateSimpleScenario(unittest.TestCase):
    def test_writes_goodput_p95_rejection_charts_for_baseline_and_rg(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign_root = Path(tmp) / "campaign_48"
            scenario_dir = campaign_root / "S1_normal_op"
            for n in (4, 5, 6):
                _write_run_folder(
                    scenario_dir / f"baseline_topfull_no_retryguard_normal_op_run{n}",
                    [50.0, 55.0, 60.0],
                    with_retryguard_log=False,
                )
                _write_run_folder(
                    scenario_dir / f"run_topfull_retryguard_normal_op_run{n}",
                    [50.0, 56.0, 61.0],
                    with_retryguard_log=True,
                )

            curated_dir = Path(tmp) / "charts"
            gallery_dir = Path(tmp) / "charts_gallery"
            mc.generate_simple_scenario("S1_normal_op", campaign_root, curated_dir, gallery_dir)

            for metric in ("goodput", "p95_latency", "rejection_rate"):
                self.assertTrue(
                    (curated_dir / "S1_normal_op" / f"total_{metric}.png").exists(),
                    f"missing curated chart for {metric}",
                )


if __name__ == "__main__":
    unittest.main()
