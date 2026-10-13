"""START-line checks for the S3/S4 mode matrix.

Run:
    python experiments/test_s3s4_mode_matrix_gate.py
"""
import unittest

import s3s4_mode_matrix_gate

NORMAL = (
    "2026-10-13T00:00:00Z  START  metric=edge_rpr rpr_threshold=0.40 "
    "rejection_threshold=0.20 reenable_rejection=0.25 "
    "climb_rpr_1_to_2=0.16 climb_rpr_2_to_3=0.32 "
    "climb_interval_seconds=10s sample_interval=1s interval_samples=20s "
    "edges=8 attempts_on=3"
)
BURST = (
    NORMAL
    + " burst_rpr=2.00 burst_window_seconds=5 burst_min_first_attempts=20"
)


class TestStartProblems(unittest.TestCase):
    def test_normal_ok(self):
        self.assertEqual(s3s4_mode_matrix_gate.start_problems(NORMAL, "normal"), [])

    def test_normal_rejects_burst_keys(self):
        problems = s3s4_mode_matrix_gate.start_problems(BURST, "normal")
        self.assertIn("burst keys present on a normal hold", problems)

    def test_burst20_ok(self):
        self.assertEqual(s3s4_mode_matrix_gate.start_problems(BURST, "burst20"), [])

    def test_burst20_requires_bar_2(self):
        problems = s3s4_mode_matrix_gate.start_problems(NORMAL, "burst20")
        self.assertIn("burst_rpr=2.00", problems)

    def test_tf_ignores_the_start_line(self):
        self.assertEqual(s3s4_mode_matrix_gate.start_problems("", "tf"), [])


if __name__ == "__main__":
    unittest.main()
