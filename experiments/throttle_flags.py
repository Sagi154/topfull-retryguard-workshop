"""Throttle-flag reports over experiments/results/final results.

    python experiments/throttle_flags.py audit  [--root DIR]
    python experiments/throttle_flags.py status [--root DIR] [--write]
    python experiments/throttle_flags.py guides [--root DIR] [--notes]
    python experiments/throttle_flags.py rerun  [--root DIR] [--out PATH]

The flag rule is analysis_score.throttle_quality, with one extra gate: a TopFull-off
variant (`rg_only`, `both_off`) is never flagged. A TopFull-on hold is flagged when the
collector log has any `fetch failed` WARNING, or any API goes longer than
analysis_score.THROTTLE_STALE_S (10 s) with no fresh threshold or admitted
read. A missing or empty topfull_throttle.csv is not a flag.
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
    quality = analysis_score.throttle_quality(
        rows, run_dir / "topfull_throttle_collector.log", topfull_on=topfull_on)
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


def _warnings_text(h: HoldFlag) -> str:
    if h.warnings:
        return f"{h.warnings} fetch warnings"
    return f"no fetch warnings, {throttle_stale.STALE_GAP_S:g} s stale-gap rule only"


def status_sentence(h: HoldFlag) -> str:
    return (
        f"`{h.name}` {label(h)}: {_warnings_text(h)}; "
        f"threshold stale {h.threshold_gap_s:.0f} s ({h.threshold_stale_pct:.1f}% of span), "
        f"admitted stale {h.admitted_gap_s:.0f} s ({h.admitted_stale_pct:.1f}% of span)."
    )


def apply_status(text: str, flags: list[HoldFlag]) -> str:
    """Append a throttle line to the Done bullet that names each flagged hold.

    Works on LF text. Idempotent: returns the text unchanged once the audit tag is in it.
    """
    flagged = [h for h in flags if h.flagged]
    if not flagged or AUDIT_TAG in text:
        return text
    lines = text.split("\n")
    done = lines.index("## Done")
    end = next(i for i in range(done + 1, len(lines)) if lines[i].startswith("## "))
    per_bullet: dict[int, list[str]] = defaultdict(list)
    unmatched: list[str] = []
    for h in flagged:
        pattern = name_pattern(h.name)
        hit = next((i for i in range(done + 1, end)
                    if lines[i].startswith("- ") and pattern.search(lines[i])), None)
        if hit is None:
            unmatched.append(status_sentence(h))
        else:
            per_bullet[hit].append(status_sentence(h))
    for index, sentences in per_bullet.items():
        lines[index] = f"{lines[index]} {AUDIT_TAG} {' '.join(sentences)}"
    if unmatched:
        at = end
        while at > done + 1 and lines[at - 1] == "":
            at -= 1
        lines.insert(at, f"{BACKFILL_HEAD} {AUDIT_TAG} {' '.join(unmatched)}")
    return "\n".join(lines)


def write_status(path: Path, flags: list[HoldFlag]) -> bool:
    """Rewrite STATUS.md keeping its line endings. Returns False when nothing changed."""
    raw = Path(path).read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    new = apply_status(raw.replace("\r\n", "\n"), flags)
    if new == raw.replace("\r\n", "\n"):
        return False
    Path(path).write_bytes(new.replace("\n", eol).encode("utf-8"))
    return True


@dataclass(frozen=True)
class GuideRow:
    guide: str
    mentioned: tuple
    named: tuple
    has_section: bool

    @property
    def missing(self) -> tuple:
        named = {h.name for h in self.named}
        return tuple(h for h in self.mentioned if h.name not in named)


def scan_guides(flags: list[HoldFlag], guides_dir: Path) -> list[GuideRow]:
    # This evidence note rejects the standard "stay valid" sentence, so it is not a scenario write-up to annotate.
    skip = {AUDIT_PATH.name, RERUN_PATH.name, "2026-10-15-proxy-fd-evidence-flagged-holds.md"}
    flagged = [h for h in flags if h.flagged]
    rows = []
    for path in sorted(Path(guides_dir).glob("*.md")):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        mentioned, named = [], []
        for h in flagged:
            pattern = name_pattern(h.name)
            hits = [line for line in lines if pattern.search(line)]
            if not hits:
                continue
            mentioned.append(h)
            if any("FLAGGED" in line for line in hits):
                named.append(h)
        if mentioned:
            rows.append(GuideRow(path.name, tuple(mentioned), tuple(named),
                                 "Throttle data quality" in text))
    return rows


def guides_markdown(rows: list[GuideRow]) -> str:
    out = [
        "| Guide | Flagged holds mentioned | TopFull on | Named FLAGGED | Missing |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        missing = ", ".join(f"`{h.name}`" for h in row.missing) or "none"
        on = sum(1 for h in row.mentioned if h.topfull_on)
        out.append(f"| {row.guide} | {len(row.mentioned)} | {on} | {len(row.named)} | {missing} |")
    return "\n".join(out)


def _on_handling(h: HoldFlag) -> str:
    """Carry only the series whose gap is over the stale limit. The other series is measured."""
    stale = analysis_score.THROTTLE_STALE_S
    cap_carried = h.threshold_gap_s > stale
    admitted_carried = h.admitted_gap_s > stale
    if not cap_carried and not admitted_carried:
        return "Fetch warnings only; no number is lost."
    clauses = []
    filters = []
    if cap_carried:
        clauses.append("the cap is carried, not measured")
        filters.append("`threshold_fresh==1`")
    else:
        clauses.append("the cap is measured")
    if admitted_carried:
        clauses.append("admitted req/s is carried, not measured")
        filters.append("`admitted_fresh==1`")
    else:
        clauses.append("admitted req/s is measured")
    body = clauses[0][0].upper() + clauses[0][1:] + "; " + clauses[1]
    if len(filters) == 2:
        filt = f"{filters[0]} and {filters[1]}"
        pronoun = "them"
    else:
        filt = filters[0]
        pronoun = "it"
    return f"{body}; filter {pronoun} on {filt} and do not quote {pronoun} as measured."


def guide_note(h: HoldFlag) -> str:
    """One paste-ready sentence per ANALYSIS-TEMPLATE.md item 17."""
    facts = (
        f"{_warnings_text(h)}; longest no-fresh threshold read {h.threshold_gap_s:.0f} s, "
        f"longest no-fresh admitted read {h.admitted_gap_s:.0f} s"
    )
    if h.topfull_on:
        handling = _on_handling(h)
    else:
        handling = (
            "That hold has TopFull off, so it is N/A: TopFull off and is not a flag. "
            "It has no admission cap to lose."
        )
    return (
        f"`{h.name}` is {label(h)} ({facts}). {handling} "
        f"Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid."
    )


def numbers_affected(h: HoldFlag) -> str:
    stale = analysis_score.THROTTLE_STALE_S
    parts = []
    if h.threshold_gap_s > stale:
        parts.append("TopFull cap lines and the live-cap table")
    if h.admitted_gap_s > stale:
        parts.append("admitted req/s")
    if not parts:
        return f"fetch warnings only; no stretch over {stale:g} s, so no number is lost"
    return "; ".join(parts)


def cell_key(h: HoldFlag) -> str | None:
    """Same scenario, mode, variant, and constraint, without the run number. final_ only."""
    if not h.name.startswith("final_"):
        return None
    return CELL_SUFFIX.sub("", h.name)


def _cell_text(h: HoldFlag, flags: list[HoldFlag]) -> str:
    key = cell_key(h)
    if key is None:
        return "n/a"
    siblings = [o for o in flags if cell_key(o) == key]
    flagged = sum(1 for o in siblings if o.flagged)
    return f"{len(siblings) - flagged} clean / {flagged} flagged"


def rerun_markdown(flags: list[HoldFlag]) -> str:
    flagged_on = [h for h in flags if h.flagged and h.topfull_on]
    out = [
        "# TopFull-on throttle flags: re-run decision list",
        "",
        "Generated by `python experiments/throttle_flags.py rerun`. Source: "
        "[2026-10-15-throttle-flag-audit.md](2026-10-15-throttle-flag-audit.md). "
        "Nothing was re-run. A re-run is the user's decision and bumps `run_number` in the "
        "scenario YAML per [STATUS.md](../STATUS.md) \"Next free slots\"; it never reuses a folder name.",
        "",
        f"{len(flagged_on)} TopFull-on holds are flagged. Goodput, P95, rejection, and retry numbers "
        "do not use `topfull_throttle.csv` and stay valid for every hold below. Only the cap and "
        "admitted-rate numbers named in the \"Numbers affected\" column are carried, not measured.",
        "",
        "How to read the columns: **In locked set** is `yes` for a `final_` folder (the current "
        "locked mode matrices) and `no` for an older study or earlier-lock folder, which AGENTS.md "
        "already calls not comparable. **Cell** counts the `final_` holds with the same scenario, "
        "mode, variant, and constraint: how many are clean and how many are flagged. **Decision** "
        "is left blank for the user (`re-run` / `keep`).",
        "",
    ]
    for scenario in SCENARIO_ORDER:
        group = [h for h in flagged_on if h.scenario == scenario]
        if not group:
            continue
        out += [
            f"### {scenario}",
            "",
            "| Hold | In locked set | Fetch warnings | Threshold stale s (% of span) | "
            "Admitted stale s (% of span) | Numbers affected | Cell | Decision |",
            "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        ]
        for h in sorted(group, key=lambda x: x.path):
            out.append(
                f"| `{h.name}` | {'yes' if h.name.startswith('final_') else 'no'} | {h.warnings} | "
                f"{h.threshold_gap_s:.0f} ({h.threshold_stale_pct:.1f}%) | "
                f"{h.admitted_gap_s:.0f} ({h.admitted_stale_pct:.1f}%) | "
                f"{numbers_affected(h)} | {_cell_text(h, flags)} |  |"
            )
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "status", "guides", "rerun"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub.choices["status"].add_argument("--write", action="store_true")
    sub.choices["guides"].add_argument("--notes", action="store_true")
    sub.choices["rerun"].add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    flags = scan(args.root)
    if args.cmd == "audit":
        print(audit_text(flags))
        return 0
    if args.cmd == "status":
        if args.write:
            changed = write_status(STATUS_PATH, flags)
            print("STATUS.md updated" if changed else "STATUS.md unchanged (already applied or no flags)")
        else:
            raw = STATUS_PATH.read_bytes().decode("utf-8").replace("\r\n", "\n")
            new = apply_status(raw, flags)
            before = set(raw.split("\n"))
            for line in new.split("\n"):
                if line not in before:
                    print(line + "\n")
        return 0
    if args.cmd == "guides":
        rows = scan_guides(flags, GUIDES_DIR)
        print(guides_markdown(rows))
        if args.notes:
            for row in rows:
                if not row.missing:
                    continue
                print(f"\n### {row.guide}\n")
                for h in row.missing:
                    print(f"- {guide_note(h)}")
        return 0
    if args.cmd == "rerun":
        text = rerun_markdown(flags)
        if args.out:
            args.out.write_bytes(text.encode("utf-8"))
            print(f"wrote {args.out}")
        else:
            print(text)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
