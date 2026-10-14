"""Slot bump for the S1/S2/S3/S4 mode-matrix YAMLs.

Run:
    python experiments/test_bump_final_slot.py
"""
import tempfile
import unittest
from pathlib import Path

import bump_final_slot


SAMPLE = """\
run_number: 1
log_folder: final_s3_rg_only_normal_run1
"""


class TestBumpText(unittest.TestCase):
    def test_advances_run_number_and_log_folder(self):
        out = bump_final_slot.bump_text(SAMPLE)
        self.assertIn("run_number: 2\n", out)
        self.assertIn("log_folder: final_s3_rg_only_normal_run2\n", out)
        self.assertNotIn("run1", out)

    def test_second_bump_reaches_run3(self):
        out = bump_final_slot.bump_text(bump_final_slot.bump_text(SAMPLE))
        self.assertIn("run_number: 3\n", out)
        self.assertIn("log_folder: final_s3_rg_only_normal_run3\n", out)

    def test_keeps_crlf(self):
        src = SAMPLE.replace("\n", "\r\n")
        out = bump_final_slot.bump_text(src)
        self.assertIn("\r\n", out)
        self.assertNotIn("\n\n", out.replace("\r\n", ""))

    def test_refuses_replay_suffix(self):
        src = SAMPLE.replace("run1", "run1_r2")
        with self.assertRaises(SystemExit):
            bump_final_slot.bump_text(src)


class TestBumpFileGuard(unittest.TestCase):
    def test_file_keeps_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "3" / "s3_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            path.write_bytes(SAMPLE.replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(bump_final_slot.bump_file(path), 2)
            raw = path.read_bytes()
            self.assertIn(b"\r\n", raw)
            self.assertNotIn(b"\n\n", raw.replace(b"\r\n", b""))
            self.assertIn(b"log_folder: final_s3_rg_only_normal_run2\r\n", raw)

    def test_accepts_s1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "1" / "s1_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            text = SAMPLE.replace(
                "final_s3_rg_only_normal", "final_s1_rg_only_normal"
            ).replace("\n", "\r\n")
            path.write_bytes(text.encode("utf-8"))
            self.assertEqual(bump_final_slot.bump_file(path), 2)
            raw = path.read_bytes()
            self.assertIn(b"log_folder: final_s1_rg_only_normal_run2\r\n", raw)
            self.assertIn(b"run_number: 2\r\n", raw)

    def test_refuses_s5(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "5" / "s5_interval_10s.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(SAMPLE, encoding="utf-8")
            with self.assertRaises(SystemExit):
                bump_final_slot.bump_file(path)

    def test_accepts_s2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "2" / "s2_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            text = SAMPLE.replace(
                "final_s3_rg_only_normal", "final_s2_rg_only_normal"
            ).replace("\n", "\r\n")
            path.write_bytes(text.encode("utf-8"))
            self.assertEqual(bump_final_slot.bump_file(path), 2)
            raw = path.read_bytes()
            self.assertIn(b"log_folder: final_s2_rg_only_normal_run2\r\n", raw)
            self.assertIn(b"run_number: 2\r\n", raw)


if __name__ == "__main__":
    unittest.main()
