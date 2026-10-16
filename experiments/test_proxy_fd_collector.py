"""Tests for proxy_fd_collector.py. Run: python -m pytest experiments/test_proxy_fd_collector.py -v"""
import csv
import logging
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import proxy_fd_collector as pfc

LIMITS = (
    "Limit                     Soft Limit           Hard Limit           Units\n"
    "Max cpu time              unlimited            unlimited            seconds\n"
    "Max open files            {soft}                 {hard}              files\n"
    "Max locked memory         65536                65536                bytes\n"
)


def make_proc(root: Path, pid: int, cmdline: bytes, fds: int, soft="1024", hard="1048576"):
    d = root / str(pid)
    (d / "fd").mkdir(parents=True)
    for i in range(fds):
        (d / "fd" / str(i)).write_text("", encoding="utf-8")
    (d / "cmdline").write_bytes(cmdline)
    (d / "limits").write_text(LIMITS.format(soft=soft, hard=hard), encoding="utf-8")


GO_EXE = b"/tmp/go-build123/b001/exe/proxy_online_boutique\0"
GO_TOOL = b"go\0run\0proxy_online_boutique.go\0"


class TestFindAndSample(unittest.TestCase):
    def test_finds_the_binary_and_not_the_go_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_proc(root, 100, GO_TOOL, 4)
            make_proc(root, 200, GO_EXE, 7)
            (root / "self").mkdir()
            self.assertEqual(pfc.find_proxy_pids(str(root)), [200])

    def test_sample_reads_fds_and_soft_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_proc(root, 200, GO_EXE, 7, soft="1024")
            rows = pfc.sample_once(1760616000, str(root))
        self.assertEqual(rows, [{"timestamp": "2025-10-16T12:00:00Z",
                                 "pid": 200, "open_fds": 7, "soft_limit": 1024}])

    def test_unlimited_is_minus_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_proc(root, 200, GO_EXE, 2, soft="unlimited", hard="unlimited")
            self.assertEqual(pfc.sample_once(0, str(root))[0]["soft_limit"], -1)

    def test_missing_proc_root_gives_no_rows(self):
        self.assertEqual(pfc.sample_once(0, "/no/such/proc"), [])


class TestRunCollector(unittest.TestCase):
    def test_writes_one_header_and_appends_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proc"
            root.mkdir()
            make_proc(root, 200, GO_EXE, 3)
            out = Path(tmp) / "out"
            out.mkdir()
            times = iter([1000.0, 1000.2, 1001.0, 1001.2])
            pfc.run_collector({"poll_interval_seconds": 1}, out, proc_root=str(root),
                              max_polls=2, clock=lambda: next(times), sleep=lambda s: None)
            pfc.run_collector({"poll_interval_seconds": 1}, out, proc_root=str(root),
                              max_polls=1, clock=lambda: 1002.0, sleep=lambda s: None)
            rows = list(csv.DictReader((out / "proxy_fds.csv").open(encoding="utf-8")))
        self.assertEqual(list(rows[0].keys()), ["timestamp", "pid", "open_fds", "soft_limit"])
        self.assertEqual(len(rows), 3)
        self.assertEqual({r["open_fds"] for r in rows}, {"3"})

    def test_no_proxy_writes_no_csv_and_warns_once_per_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proc"
            root.mkdir()
            out = Path(tmp) / "out"
            out.mkdir()
            with self.assertLogs("proxy_fd_collector", level=logging.WARNING) as logs:
                times = iter([1000.0, 1001.0, 1002.0, 1040.0])
                pfc.run_collector({"poll_interval_seconds": 1}, out, proc_root=str(root),
                                  max_polls=4, clock=lambda: next(times), sleep=lambda s: None)
            self.assertFalse((out / "proxy_fds.csv").exists())
        self.assertEqual(len(logs.records), 2)  # t=1000 and t=1040; not 1001, 1002


if __name__ == "__main__":
    unittest.main()
