"""
test_mentor_charts_plots.py — Smoke tests for mentor_charts_plots.py.
These verify each plotting function runs without error on small
synthetic data and writes a non-empty PNG; they do not inspect pixel
content.

Run:
    python experiments/test_mentor_charts_plots.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mentor_charts_plots as mcp


class TestPlotTimeseriesComparison(unittest.TestCase):
    def test_writes_nonempty_png_without_toggle_events(self):
        baseline_avg = pd.DataFrame(
            {"mean": [10.0, 12.0, 11.0], "min": [8.0, 10.0, 9.0], "max": [12.0, 14.0, 13.0]}
        )
        rg_avg = pd.DataFrame(
            {"mean": [10.0, 20.0, 25.0], "min": [9.0, 18.0, 23.0], "max": [11.0, 22.0, 27.0]}
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_timeseries_comparison(
                baseline_avg, rg_avg, title="Test", ylabel="Goodput", out_path=out_path
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)

    def test_writes_nonempty_png_with_toggle_events(self):
        baseline_avg = pd.DataFrame({"mean": [10.0, 12.0], "min": [8.0, 10.0], "max": [12.0, 14.0]})
        rg_avg = pd.DataFrame({"mean": [10.0, 20.0], "min": [9.0, 18.0], "max": [11.0, 22.0]})
        toggle_events = [{"elapsed_seconds": 1.0, "service": "checkoutservice", "direction": "ON→OFF"}]
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_timeseries_comparison(
                baseline_avg, rg_avg, title="Test", ylabel="Goodput",
                out_path=out_path, toggle_events=toggle_events,
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)


class TestPlotMultiLine(unittest.TestCase):
    def test_writes_nonempty_png_with_one_line_per_column(self):
        df = pd.DataFrame(
            {"frontend": [10.0, 12.0, 11.0], "cartservice": [5.0, 6.0, 7.0]},
            index=[0.0, 5.0, 10.0],
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_multi_line(df, title="Test", ylabel="CPU (millicores)", out_path=out_path)
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)

    def test_handles_empty_dataframe_without_raising(self):
        df = pd.DataFrame()
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_multi_line(df, title="Test", ylabel="CPU", out_path=out_path)
            self.assertTrue(out_path.exists())


class TestPlotSideBySideComparison(unittest.TestCase):
    def test_writes_nonempty_png_with_two_panels(self):
        baseline_a = pd.DataFrame({"mean": [10.0, 11.0], "min": [9.0, 10.0], "max": [11.0, 12.0]})
        rg_a = pd.DataFrame({"mean": [10.0, 15.0], "min": [9.0, 14.0], "max": [11.0, 16.0]})
        baseline_b = pd.DataFrame({"mean": [8.0, 9.0], "min": [7.0, 8.0], "max": [9.0, 10.0]})
        rg_b = pd.DataFrame({"mean": [8.0, 12.0], "min": [7.0, 11.0], "max": [9.0, 13.0]})
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_side_by_side_comparison(
                pair_a=(baseline_a, rg_a),
                pair_b=(baseline_b, rg_b),
                title="Test",
                ylabel="Goodput",
                label_a="S4A: ProductCatalog",
                label_b="S4B: Payment",
                out_path=out_path,
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
