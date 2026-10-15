"""Stale stretches of topfull_throttle.csv, for the graphs and the flag reports.

A stretch is a span with no fresh threshold read for longer than STALE_GAP_S (10 s).
This is the same comparison analysis_score.throttle_quality uses after Task 9
(head, middle, and tail gaps all count; a gap of exactly 10 s is not a stretch).
Task 9 sets THROTTLE_STALE_S = 10 so the two constants match. Rows are never dropped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STALE_GAP_S = 10.0
# Keep in step with run_timeline.THROTTLE_CARRY_S: the solid cap line already carries a
# fresh cap forward this long, so the dashed stale line starts after it.
CARRY_S = 6
NO_CAP = 10000.0
REQUIRED = {"api", "hold_s", "threshold", "threshold_fresh"}


def stale_stretches(hold_s, fresh, gap_s: float = STALE_GAP_S) -> list[tuple[float, float]]:
    """(start, end) of every gap between fresh reads longer than gap_s.

    The first row and the last row are anchors, so a hold whose reads never start,
    or stop early, has a head or tail stretch.
    """
    t = np.asarray(hold_s, dtype=float)
    ok = np.asarray(fresh, dtype=bool)
    if t.size == 0:
        return []
    anchors = [float(t[0])] + [float(x) for x in t[ok]] + [float(t[-1])]
    return [(a, b) for a, b in zip(anchors, anchors[1:]) if b - a > gap_s]


def _by_api(df: pd.DataFrame):
    if df is None or df.empty or not REQUIRED <= set(df.columns):
        return
    for api, group in df.groupby("api", sort=True):
        group = group.dropna(subset=["hold_s"]).sort_values("hold_s")
        if not group.empty:
            yield str(api), group


def stale_cap_series(
    df: pd.DataFrame,
    gap_s: float = STALE_GAP_S,
    carry_s: float = CARRY_S,
    no_cap: float = NO_CAP,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Carried (non-fresh) cap values inside a stale stretch, per API.

    Points start carry_s after the last fresh read, where the solid line stops.
    10000 (no cap) and 0 (empty read) are left out, as they are for fresh reads.
    """
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for api, group in _by_api(df):
        t = group["hold_s"].to_numpy(dtype=float)
        fresh = group["threshold_fresh"].to_numpy(dtype=float) == 1
        cap = group["threshold"].to_numpy(dtype=float)
        keep = np.zeros(t.size, dtype=bool)
        for start, end in stale_stretches(t, fresh, gap_s):
            keep |= (t > start + carry_s) & (t <= end) & ~fresh
        keep &= (cap > 0) & (cap < no_cap)
        if keep.any():
            out[api] = (t[keep], cap[keep])
    return out


def stale_bands(df: pd.DataFrame, gap_s: float = STALE_GAP_S) -> list[tuple[float, float]]:
    """Stale stretches of every API, merged where they overlap."""
    spans: list[tuple[float, float]] = []
    for _api, group in _by_api(df):
        t = group["hold_s"].to_numpy(dtype=float)
        fresh = group["threshold_fresh"].to_numpy(dtype=float) == 1
        spans.extend(stale_stretches(t, fresh, gap_s))
    spans.sort()
    merged: list[tuple[float, float]] = []
    for lo, hi in spans:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged
