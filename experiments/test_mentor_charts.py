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


def _write_full_run_folder(
    run_dir: Path,
    goodput_total: list[float],
    goodput_bottleneck: list[float],
    with_retryguard_log: bool,
) -> None:
    _write_run_folder(run_dir, goodput_total, with_retryguard_log)
    n = len(goodput_bottleneck)
    pd.DataFrame(
        {
            "RPS": goodput_bottleneck,
            "Fail": [0.0] * n,
            "Goodput": goodput_bottleneck,
            "Latency95": [300.0] * n,
            "Latency99": [0.0] * n,
        }
    ).to_csv(run_dir / "postcheckout.csv", index=False)
    envoy_rows = [
        ("2026-09-05T16:51:25Z", "checkoutservice", 1000, 0),
        ("2026-09-05T16:51:30Z", "checkoutservice", 1100, 5),
    ]
    pd.DataFrame(
        envoy_rows,
        columns=["timestamp", "target_service", "upstream_rq_total", "upstream_rq_retry"],
    ).assign(upstream_rq_retry_success=0, upstream_rq_retry_limit_exceeded=0).to_csv(
        run_dir / "envoy_retries_frontend.csv", index=False
    )
    resource_rows = [
        ("2026-09-05T16:51:52Z", "checkoutservice", 10, 1000),
        ("2026-09-05T16:51:57Z", "checkoutservice", 12, 1100),
    ]
    pd.DataFrame(
        resource_rows,
        columns=["timestamp", "service", "cpu_millicores", "memory_working_set_bytes"],
    ).assign(replica_count=1).to_csv(run_dir / "resource_usage.csv", index=False)


class TestGenerateBottleneckScenario(unittest.TestCase):
    def test_writes_total_and_bottleneck_endpoint_charts(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign_root = Path(tmp) / "campaign_48"
            scenario_dir = campaign_root / "S3_targeted_bottleneck"
            for n in (4, 5, 6):
                _write_full_run_folder(
                    scenario_dir / f"baseline_topfull_no_retryguard_targeted_bottleneck_run{n}",
                    [50.0, 55.0], [40.0, 42.0], with_retryguard_log=False,
                )
                _write_full_run_folder(
                    scenario_dir / f"run_topfull_retryguard_targeted_bottleneck_run{n}",
                    [50.0, 58.0], [40.0, 47.0], with_retryguard_log=True,
                )

            curated_dir = Path(tmp) / "charts"
            gallery_dir = Path(tmp) / "charts_gallery"
            mc.generate_bottleneck_scenario(
                "S3_targeted_bottleneck", campaign_root, curated_dir, gallery_dir
            )

            for metric in ("goodput", "p95_latency", "rejection_rate"):
                self.assertTrue((curated_dir / "S3_targeted_bottleneck" / f"total_{metric}.png").exists())
                self.assertTrue(
                    (curated_dir / "S3_targeted_bottleneck" / f"postcheckout_{metric}.png").exists()
                )


class TestGenerateRetriesAndResources(unittest.TestCase):
    def test_writes_retries_and_resource_charts(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign_root = Path(tmp) / "campaign_48"
            scenario_dir = campaign_root / "S3_targeted_bottleneck"
            for n in (4, 5, 6):
                _write_full_run_folder(
                    scenario_dir / f"baseline_topfull_no_retryguard_targeted_bottleneck_run{n}",
                    [50.0, 55.0], [40.0, 42.0], with_retryguard_log=False,
                )
                _write_full_run_folder(
                    scenario_dir / f"run_topfull_retryguard_targeted_bottleneck_run{n}",
                    [50.0, 58.0], [40.0, 47.0], with_retryguard_log=True,
                )

            curated_dir = Path(tmp) / "charts"
            gallery_dir = Path(tmp) / "charts_gallery"
            config = mc.SCENARIOS["S3_targeted_bottleneck"]
            mc.generate_retries_and_resources(
                "S3_targeted_bottleneck", config, campaign_root, curated_dir, gallery_dir
            )

            self.assertTrue(
                (curated_dir / "S3_targeted_bottleneck" / "envoy_retries_frontend_per_target.png").exists()
            )
            self.assertTrue(
                (curated_dir / "S3_targeted_bottleneck" / "envoy_retries_frontend_summed.png").exists()
            )
            self.assertTrue(
                (curated_dir / "S3_targeted_bottleneck" / "resource_cpu_millicores.png").exists()
            )
            self.assertTrue(
                (curated_dir / "S3_targeted_bottleneck" / "resource_memory_working_set_bytes.png").exists()
            )


if __name__ == "__main__":
    unittest.main()
