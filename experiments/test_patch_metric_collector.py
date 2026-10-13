"""Unit tests for experiments/patch_metric_collector.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_metric_collector as patch  # noqa: E402

HEADER = 'w.writerow(["RPS", "Fail", "Goodput", "Latency95", "Latency99"])'
SOURCE = (
    "import requests\nimport time\nimport csv\n\n"
    "def record():\n"
    "    for api in apis:\n"
    "        with open(filename, \"a\") as f:\n"
    "            w = csv.writer(f)\n"
    f"            {HEADER}\n"
    "    with open(filename, \"a\") as f:\n"
    "        w = csv.writer(f)\n"
    f"        {HEADER}\n"
) + patch.OLD


class TestPatch(unittest.TestCase):
    def test_adds_a_last_timestamp_column_once(self):
        text = patch.add_row_timestamps(patch.add_try_guard(SOURCE))
        self.assertIn("from datetime import datetime, timezone\n", text)
        self.assertEqual(text.count('"Latency99", "timestamp"])'), 2)
        self.assertIn("w.writerow([rps, fail, rps-fail, latency95, latency99, stamp])", text)
        self.assertIn("total_latency99/len(apis), stamp])", text)
        self.assertLess(text.index("            metric = c.query()\n"),
                        text.index("            stamp = datetime.now(timezone.utc)"))
        self.assertEqual(patch.add_row_timestamps(patch.add_try_guard(text)), text)


if __name__ == "__main__":
    unittest.main()
