"""
test_compare_runs.py — unit tests for the replica-scaling comparison script.

Run:
    python experiments/test_compare_runs.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_runs as cr


def _ts(start: datetime, seconds: int) -> str:
    return (start + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, header: str, rows: list[str]) -> None:
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


class TestSteadyWindow(unittest.TestCase):
    def test_locust_drops_first_60_and_last_10(self):
        rows = [{"RPS": str(i)} for i in range(80)]
        got = cr.locust_steady_rows(rows)
        self.assertEqual([r["RPS"] for r in got], [str(i) for i in range(60, 70)])

    def test_locust_too_short_is_empty(self):
        self.assertEqual(cr.locust_steady_rows([{"RPS": "1"}] * 50), [])

    def test_timestamp_bounds_drop_head_and_tail(self):
        start = datetime(2026, 9, 23, 19, 0, 0, tzinfo=timezone.utc)
        times = [start + timedelta(seconds=i) for i in range(80)]
        bounds = cr.steady_bounds(times)
        self.assertIsNotNone(bounds)
        self.assertEqual(bounds[0], start + timedelta(seconds=60))
        self.assertEqual(bounds[1], start + timedelta(seconds=69))
        self.assertFalse(cr.in_window(times[59], bounds))
        self.assertTrue(cr.in_window(times[60], bounds))
        self.assertTrue(cr.in_window(times[69], bounds))
        self.assertFalse(cr.in_window(times[70], bounds))


class TestSimultaneousOverload(unittest.TestCase):
    def test_max_and_mean_count_services_in_same_tick(self):
        start = datetime(2026, 9, 23, 19, 0, 0, tzinfo=timezone.utc)
        # 80 ticks; only the steady window (t=60..70 inclusive) is counted.
        rows = ["timestamp,service,cadvisor_cpu,quota,alpha,utilization,overloaded"]
        for sec in range(80):
            fe_ovl = 1 if sec >= 60 else 0
            ck_ovl = 1 if sec in (62, 63, 64) else 0
            rows.append(f"{_ts(start, sec)},frontend,100,1150,0.8,0.1,{fe_ovl}")
            rows.append(f"{_ts(start, sec)},checkoutservice,100,615,0.8,0.1,{ck_ovl}")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "topfull_detect.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            got = cr.simultaneous_overload(run_dir)
        self.assertTrue(got["available"])
        self.assertEqual(got["max"], 2)
        # 10 ticks (60..69): 3 ticks with 2 services, 7 with 1 → mean 1.3
        self.assertAlmostEqual(got["mean"], 1.3)
        self.assertEqual(got["n_ticks"], 10)


class TestMissingFiles(unittest.TestCase):
    def test_empty_folder_is_na_not_an_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = cr.analyze_run(Path(tmp), "empty")
        self.assertFalse(report["simultaneous"]["available"])
        self.assertIn("topfull_detect.csv", report["simultaneous"]["reason"])
        self.assertFalse(report["inbound"]["available"])
        self.assertFalse(report["utilization"]["available"])
        self.assertIn("n/a", cr._sim_cell(report))
        md = cr.render_markdown([report])
        self.assertIn("n/a (no worker_cpu.txt)", md)
        self.assertIn("n/a (no load_cpu.txt)", md)

    def test_missing_top_logs_do_not_block_master(self):
        start = datetime(2026, 9, 23, 19, 0, 0, tzinfo=timezone.utc)
        rows = ["timestamp,service,cpu_millicores,memory_working_set_bytes,replica_count"]
        for sec in range(80):
            rows.append(f"{_ts(start, sec)},__master_node__,4000,1000,1")
            rows.append(f"{_ts(start, sec)},frontend,100,1000,1")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "resource_usage.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            (run_dir / "service_capacity.json").write_text(
                '{"frontend": {"cpu_limit_millicores": 1150}}', encoding="utf-8"
            )
            machines = cr.machine_summary(run_dir)
            util = cr.utilization_summary(run_dir)
        self.assertTrue(machines["master"]["available"])
        self.assertAlmostEqual(machines["master"]["cores_max"], 4.0)
        self.assertFalse(machines["worker"]["available"])
        self.assertTrue(util["available"])


class TestTopLog(unittest.TestCase):
    def test_parses_idle_into_cores_used(self):
        text = (
            "top - 19:00:00 up 1 day\n"
            "%Cpu(s): 10.0 us,  5.0 sy,  0.0 ni, 80.0 id,  5.0 wa\n"
            "%Cpu(s): 20.0 us,  5.0 sy,  0.0 ni, 75.0 id,  0.0 wa\n"
            "  PID USER  PR  NI VIRT RES SHR S %CPU %MEM TIME+ COMMAND\n"
            "  11 user  20   0    1   1   1 S 42.0  1.0 0:01 locust\n"
        )
        got = cr.parse_top_log(text, 16)
        self.assertTrue(got["available"])
        self.assertAlmostEqual(got["cores_max"], 4.0)  # 25% of 16
        self.assertAlmostEqual(got["locust_cpu_max"], 42.0)


if __name__ == "__main__":
    unittest.main()
