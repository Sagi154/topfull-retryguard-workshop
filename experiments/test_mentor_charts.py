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


class TestGenerateS5S6Merge(unittest.TestCase):
    def test_writes_overlay_charts_and_toggle_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign_root = Path(tmp) / "campaign_48"
            s6_dir = campaign_root / "S6_forced_recovery"
            s5_dir = campaign_root / "S5_interval_tuning"
            for n in (1, 2, 3):
                _write_run_folder(
                    s6_dir / f"baseline_topfull_no_retryguard_forced_recovery_run{n}",
                    [50.0] * 5, with_retryguard_log=False,
                )
                _write_run_folder(
                    s6_dir / f"run_topfull_retryguard_forced_recovery_run{n}",
                    [50.0] * 5, with_retryguard_log=True,
                )
            for interval in ("10s", "20s", "30s", "60s"):
                for n in (3, 4, 5):
                    _write_run_folder(
                        s5_dir / f"run_topfull_retryguard_interval_{interval}_run{n}",
                        [50.0] * 5, with_retryguard_log=True,
                    )

            curated_dir = Path(tmp) / "charts"
            gallery_dir = Path(tmp) / "charts_gallery"
            goodput_path, rejection_path = mc.generate_s5_s6_merge(
                campaign_root, curated_dir, gallery_dir
            )

            self.assertTrue(goodput_path.exists())
            self.assertTrue(rejection_path.exists())
            timeline_path = curated_dir / "S6_forced_recovery" / "s5_toggle_timeline.md"
            self.assertTrue(timeline_path.exists())
            self.assertIn("10s", timeline_path.read_text(encoding="utf-8"))


def _write_retryguard_log(
    run_dir: Path,
    events: list[tuple[str, str, str]],
) -> None:
    """Write a parseable retryguard.log.

    ``events`` is a list of (iso_timestamp, service, direction) after a
    START line. Pass an empty list for a START-only log.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["2026-09-05T16:52:18Z  START  threshold=0.20\n"]
    for ts, service, direction in events:
        extra = (
            "rejection=0.60  consecutive_high=2  attempts=0"
            if direction == "ON→OFF"
            else "rejection=0.05  consecutive_low=3  attempts=3"
        )
        lines.append(f"{ts}  {service}  {direction}   {extra}\n")
    (run_dir / "retryguard.log").write_text("".join(lines), encoding="utf-8")


class TestCollectToggleEvents(unittest.TestCase):
    def test_includes_off_to_on_from_later_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            run1 = Path(tmp) / "run1"
            run2 = Path(tmp) / "run2"
            _write_retryguard_log(
                run1,
                [("2026-09-05T16:53:18Z", "checkoutservice", "ON→OFF")],
            )
            _write_retryguard_log(
                run2,
                [("2026-09-05T16:58:18Z", "cartservice", "OFF→ON")],
            )

            events = mc._collect_toggle_events([run1, run2])

            directions = {(e["service"], e["direction"]) for e in events}
            self.assertIn(("checkoutservice", "ON→OFF"), directions)
            self.assertIn(("cartservice", "OFF→ON"), directions)
            elapsed = [e["elapsed_seconds"] for e in events]
            self.assertEqual(elapsed, sorted(elapsed))

    def test_deduplicates_same_service_direction_elapsed_across_repeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dirs = []
            for n in (1, 2, 3):
                run_dir = Path(tmp) / f"run{n}"
                _write_retryguard_log(
                    run_dir,
                    [("2026-09-05T16:53:18Z", "checkoutservice", "ON→OFF")],
                )
                run_dirs.append(run_dir)

            events = mc._collect_toggle_events(run_dirs)

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["service"], "checkoutservice")
            self.assertEqual(events[0]["direction"], "ON→OFF")
            self.assertAlmostEqual(events[0]["elapsed_seconds"], 60.0)

    def test_returns_empty_list_when_no_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dirs = [Path(tmp) / "run1", Path(tmp) / "run2"]
            for run_dir in run_dirs:
                run_dir.mkdir()

            self.assertEqual(mc._collect_toggle_events(run_dirs), [])


if __name__ == "__main__":
    unittest.main()
