"""Throttle-flag reports over experiments/results/final results.

    python experiments/throttle_flags.py audit  [--root DIR]
    python experiments/throttle_flags.py status [--root DIR] [--write]
    python experiments/throttle_flags.py guides [--root DIR] [--notes]
    python experiments/throttle_flags.py rerun  [--root DIR] [--out PATH]

The flag rule is analysis_score.throttle_quality, with one extra gate: a TopFull-off
variant (`rg_only`, `both_off`) is never flagged. A TopFull-on hold is flagged when the
collector log has any `fetch failed` WARNING, or any API goes longer than
analysis_score.THROTTLE_STALE_S (10 s after Task 9; 30 s until that task lands) with no
fresh threshold or admitted read. A missing or empty topfull_throttle.csv is not a flag.
Nothing here edits a run folder.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import throttle_stale  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO / "experiments" / "results" / "final results"
STATUS_PATH = REPO / "STATUS.md"
GUIDES_DIR = REPO / "Guides and Info"
RERUN_PATH = GUIDES_DIR / "2026-10-15-throttle-flag-rerun-decisions.md"
AUDIT_PATH = GUIDES_DIR / "2026-10-15-throttle-flag-audit.md"
AUDIT_TAG = "Throttle flags (2026-10-15 audit):"
BACKFILL_HEAD = "- **Throttle flag backfill (2026-10-15)** — holds with no Done bullet of their own."
TOPFULL_ON_VARIANTS = ("both", "tf_only")
# Decided 2026-10-15: TopFull-off holds are not flags. This label is what `label()`
# returns for them; status, guides, and rerun only iterate holds with flagged=True.
TF_ON_LABEL = "FLAGGED"
TF_OFF_LABEL = "N/A: TopFull off"
CELL_SUFFIX = re.compile(r"_run\d+(?:_r\d+)?$")
SCENARIO_ORDER = ("S1", "S2", "S3", "S4A", "S4B")


@dataclass(frozen=True)
class HoldFlag:
    path: str
    scenario: str
    mode: str
    variant: str
    name: str
    topfull_on: bool
    flagged: bool
    warnings: int
    first_warning: str | None
    threshold_gap_s: float
    admitted_gap_s: float
    threshold_stale_pct: float
    admitted_stale_pct: float


def label(h: HoldFlag) -> str:
    return TF_ON_LABEL if h.topfull_on else TF_OFF_LABEL


def name_pattern(name: str) -> re.Pattern:
    """The folder name as a whole token: `_r2` and `_run10` do not match `run1`."""
    return re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])")


def _stale_pct(rows: list[dict], key: str) -> float:
    """Worst API's share of its first-to-last span inside a stretch over STALE_GAP_S."""
    by_api: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("timestamp"):
            by_api[row.get("api", "")].append(row)
    worst = 0.0
    for series in by_api.values():
        series.sort(key=lambda r: r["timestamp"])
        stamps = [analysis_score.parse_ts(r["timestamp"]) for r in series]
        t = np.array([(s - stamps[0]).total_seconds() for s in stamps])
        span = float(t[-1] - t[0])
        if span <= 0:
            continue
        fresh = np.array([int(float(r.get(key) or 0)) == 1 for r in series])
        inside = sum(hi - lo for lo, hi in throttle_stale.stale_stretches(t, fresh))
        worst = max(worst, 100.0 * inside / span)
    return worst


def scan_hold(root: Path, run_dir: Path) -> HoldFlag:
    scenario_dir, variant, name = run_dir.relative_to(root).parts
    rows = analysis_score._rows(run_dir / "topfull_throttle.csv")
    topfull_on = variant in TOPFULL_ON_VARIANTS
    # Do not pass topfull_on into throttle_quality here. That parameter arrives in
    # Task 9. Until then the scorer still flags a TopFull-off hold, and this AND
    # is what keeps those holds out of flagged.
    quality = analysis_score.throttle_quality(rows, run_dir / "topfull_throttle_collector.log")
    return HoldFlag(
        path="/".join((scenario_dir, variant, name)),
        scenario=scenario_dir.split("_", 1)[0],
        mode=scenario_dir.rsplit("_", 1)[1],
        variant=variant,
        name=name,
        topfull_on=topfull_on,
        flagged=bool(quality["flagged"] and quality["has_csv"] and topfull_on),
        warnings=int(quality["warnings"]),
        first_warning=quality["first_warning"],
        threshold_gap_s=float(quality["threshold_gap_s"] or 0.0),
        admitted_gap_s=float(quality["admitted_gap_s"] or 0.0),
        threshold_stale_pct=_stale_pct(rows, "threshold_fresh"),
        admitted_stale_pct=_stale_pct(rows, "admitted_fresh"),
    )


def scan(root: Path) -> list[HoldFlag]:
    root = Path(root)
    run_dirs = sorted(p for p in root.glob("*/*/*") if p.is_dir())
    return sorted((scan_hold(root, p) for p in run_dirs), key=lambda h: h.path)


def audit_text(flags: list[HoldFlag]) -> str:
    flagged = [h for h in flags if h.flagged]
    on = [h for h in flagged if h.topfull_on]
    lines = [
        f"runs={len(flags)} flagged={len(flagged)} "
        f"topfull_on_flagged={len(on)} topfull_off_flagged={len(flagged) - len(on)}",
    ]
    for h in flagged:
        lines.append(
            f"{h.path}  {'on' if h.topfull_on else 'off'}  warnings={h.warnings}  "
            f"gap_s={h.threshold_gap_s:.0f}/{h.admitted_gap_s:.0f}  "
            f"stale_pct={h.threshold_stale_pct:.1f}/{h.admitted_stale_pct:.1f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "status", "guides", "rerun"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    flags = scan(args.root)
    if args.cmd == "audit":
        print(audit_text(flags))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
