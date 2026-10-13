"""Unit tests for experiments/pull_results.py."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pull_results  # noqa: E402

CONFIG = (
    "infra:\n"
    "  master_ssh_host: topfull-master\n"
    "  results_base_path: /remote/results\n"
    "log_folder: run_x\n"
)


class TestPullBuildsTimeline(unittest.TestCase):
    def test_timeline_is_built_and_its_failure_does_not_fail_the_pull(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dest" / "run_x").mkdir(parents=True)
            config = root / "cfg.yaml"
            config.write_text(CONFIG, encoding="utf-8")
            with mock.patch.object(pull_results.run_scenario, "local_results_dir",
                                   return_value=str(root / "dest")), \
                 mock.patch.object(pull_results.subprocess, "run",
                                   return_value=SimpleNamespace(returncode=0)), \
                 mock.patch("run_timeline.build", side_effect=ValueError("no load")) as build:
                out = pull_results.pull_results(str(config))
        self.assertEqual(out, root / "dest" / "run_x")
        build.assert_called_once_with(root / "dest" / "run_x")


if __name__ == "__main__":
    unittest.main()
