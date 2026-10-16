"""Generate Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md.

    python experiments/proxy_fd_decisions.py [--root DIR] [--out PATH] [--check]

Source of the effect sizes: Guides and Info/2026-10-15-proxy-fd-evidence-flagged-holds.md.
Source of the next free slot: the `run_number` already written in the YAML that owns the cell
(STATUS.md "Next free slots" mirrors those numbers). Nothing is re-run; the Decision column
is left blank for the user.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import throttle_flags  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CONFIGS = REPO / "experiments" / "configs" / "final_configs"
OUT_PATH = REPO / "Guides and Info" / "2026-10-16-proxy-fd-rerun-decisions.md"
EVIDENCE = "2026-10-15-proxy-fd-evidence-flagged-holds.md"
TOPFULL_ON_VARIANTS = ("both", "tf_only")


@dataclass(frozen=True)
class Hold:
    name: str
    path: str      # under final results/
    yaml: str      # under final_configs/
    onset: str
    goodput: str
    p95: str
    rejection: str
    effect: str


AFFECTED = [
    Hold("final_s2_both_burst_run1", "S2_sustained_overload_burst/both/final_s2_both_burst_run1",
         "2/s2_both_burst.yaml", "120 s", "350 → 374", "422 → 621", "0.16 → 0.31",
         "shortfall 65 req/s; the next minute drops 53 req/s and adds 232 ms of P95 beyond cleans"),
    Hold("study6_s2_normal_rgtf1_rep1", "S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep1",
         "2/s2_both_normal.yaml", "103 s", "346 → 400", "352 → 549", "0.13 → 0.26",
         "shortfall 51 req/s; the next minute drops 103 req/s and adds 307 ms of P95"),
    Hold("study6_s2_normal_rgtf1_rep2", "S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep2",
         "2/s2_both_normal.yaml", "65 s", "314 → 385", "226 → 459", "0.05 → 0.30",
         "shortfall 94 req/s; minute rejection +0.25 against +0.09"),
    Hold("study6_s2_normal_rgtf0_rep1", "S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1",
         "2/s2_rg_only_normal.yaml", "50 s", "242 → 321", "272 → 456", "0.03 → 0.41",
         "shortfall 142 req/s; rejection in the next minute +0.49 against +0.09. Edge rpr stays 0.007"),
    Hold("study6_s2_normal_rgtf0_rep2", "S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep2",
         "2/s2_rg_only_normal.yaml", "69 s", "305 → 367", "360 → 461", "0.06 → 0.34",
         "shortfall 96 req/s; minute rejection +0.38 against +0.08"),
    Hold("final_s2_tf_only_run2", "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2",
         "2/s2_tf_only.yaml", "333 s", "402 → 317", "564 → 1318", "0.17 → 0.31",
         "shortfall 120 req/s; the next minute is −114 req/s and +697 ms against controls that are flat"),
    Hold("final_4a_constrained_rg_only_burst_run2",
         "S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2",
         "4/4a_constrained/4a_constrained_rg_only_burst.yaml", "37 s", "175 → 29", "610 → 316", "0.15 → 0.94",
         "shortfall 49 req/s on top of the constrained collapse; minute rejection +0.77 against +0.42"),
    Hold("final_4a_constrained_rg_only_normal_run2_r2",
         "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2_r2",
         "4/4a_constrained/4a_constrained_rg_only_normal.yaml", "36 s", "156 → 22", "570 → 322", "0.20 → 0.95",
         "shortfall 39 req/s; minute rejection +0.66 against +0.43"),
    Hold("final_4a_constrained_tf_only_run2",
         "S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2",
         "4/4a_constrained/4a_constrained_tf_only.yaml", "47 s", "182 → 24", "592 → 597", "0.33 → 0.96",
         "shortfall 45 req/s; the next minute drops another 149 req/s versus cleans and edge rpr rises to 1.32"),
    Hold("final_s2_tf_only_run3", "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3",
         "2/s2_tf_only.yaml", "187 s", "176 → 88", "858 → 1330", "0.53 → 0.73",
         "direct proxy log (429 accept4 lines from 189 s); shortfall 140 req/s; pre-onset goodput already far below clean S2 (that hold was pinned)"),
    Hold("final_s2_both_burst_run3", "S2_sustained_overload_burst/both/final_s2_both_burst_run3",
         "2/s2_both_burst.yaml", "50 s", "238 → 310", "252 → 426", "0.07 → 0.44",
         "direct proxy log (568 accept4 lines from 50 s); shortfall 146 req/s (level still rises: 50 s is inside the ramp); minute rejection +0.37 against +0.09"),
]
AFFECTED_NAMES = {h.name for h in AFFECTED}

# Flagged, and the evidence report does not recommend a re-run. (name, reason)
NOT_RECOMMENDED = [
    ("final_s2_both_burst_run2", "mild: full-window goodput shortfall 30 req/s; goodput 243 → 450"),
    ("final_s2_rg_only_burst_run2", "brief: 16 timeouts and a 45 s gap at 567 s; goodput 400 → 412"),
    ("study7_s2_normal_rgtf1_rep1", "brief: 40 timeouts, 105 s gap at 511 s; real local dip, hold average 475 → 450"),
    ("final_s3_rg_only_normal_run1", "brief and unlike accept4: no fetch warning, 55 s gap, clock fit correlation 0.11"),
    ("s2_burst20_rgtf0", "healthy through 555 s stale: goodput 299 → 530, rejection 0.03 → 0.05"),
]


def yaml_for(variant: str, name: str) -> str | None:
    """YAML (under final_configs/) that owns a final_4a_constrained_* cell."""
    if "4a_constrained" not in name:
        return None
    mode = "burst" if "burst" in name else "normal"
    stem = {
        ("rg_only", "burst"): "4a_constrained_rg_only_burst",
        ("rg_only", "normal"): "4a_constrained_rg_only_normal",
        ("tf_only", "normal"): "4a_constrained_tf_only",
        ("tf_only", "burst"): "4a_constrained_tf_only",
        ("both", "burst"): "4a_constrained_both_burst",
        ("both", "normal"): "4a_constrained_both_normal",
    }[(variant, mode)]
    return f"4/4a_constrained/{stem}.yaml"


def legacy_flagged(root: Path) -> list[tuple[str, str, bool]]:
    """(name, variant, flagged) for every hold, by the collector rule at EVERY variant."""
    out = []
    for run_dir in sorted(p for p in Path(root).glob("*/*/*") if p.is_dir()):
        rows = analysis_score._rows(run_dir / "topfull_throttle.csv")
        q = analysis_score.throttle_quality(
            rows, run_dir / "topfull_throttle_collector.log", topfull_on=True)
        out.append((run_dir.name, run_dir.parent.name, bool(q["flagged"] and q["has_csv"])))
    return out


def next_slot(configs_root: Path, yaml_rel: str) -> int:
    data = yaml.safe_load((Path(configs_root) / yaml_rel).read_text(encoding="utf-8"))
    return int(data["run_number"])


def _variant_of(root: Path, name: str) -> str:
    return next(p.parent.name for p in Path(root).glob(f"*/*/{name}"))


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def render(root: Path, configs_root: Path, audit_text: str) -> str:
    root, configs_root = Path(root), Path(configs_root)
    legacy = legacy_flagged(root)
    flagged = [(n, v) for n, v, f in legacy if f]
    on = [n for n, v in flagged if v in TOPFULL_ON_VARIANTS]
    scanned = {n for n, _v, _f in legacy}
    missing = [n for n in sorted(scanned) if not throttle_flags.name_pattern(n).search(audit_text)]
    missing_flagged = [n for n in missing if any(n == fn for fn, _ in flagged)]
    out = [
        "# Proxy descriptor re-run decisions",
        "",
        f"Generated by `python experiments/proxy_fd_decisions.py`. Effect sizes are copied from [{EVIDENCE}]({EVIDENCE}) "
        "(read its corrections box first). **Nothing here has been re-run.** A re-run happens only after the "
        "descriptor and RL-timeout fixes have passed the verification hold in "
        "[the 2026-10-16 plan](../docs/superpowers/plans/2026-10-16-proxy-fd-limit-and-rl-stall-flag.md) Task 7, and only "
        "for rows the user marks in the Decision column. The next free slot is the `run_number` already written in the "
        "YAML that owns the cell (STATUS.md \"Next free slots\" lists the same numbers); a re-run bumps `run_number` and "
        "`log_folder` in that YAML only.",
        "",
        f"Counts: `final results/` holds {len(legacy)} run folders; flagged by the collector rule at every variant: "
        f"{len(flagged)} ({len(on)} TopFull on, {len(flagged) - len(on)} off). `rg_only` holds are in scope here: "
        "every Locust request goes through the proxy, so a proxy that ran out of descriptors damages them too.",
        "",
        "## A. Materially affected (11)",
        "",
        "| Hold | Variant | TopFull | In the locked `final_` set | Onset | Goodput req/s | P95 ms | Rejection | Versus clean controls | YAML | Next free run_number | Decision |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for h in AFFECTED:
        variant = h.path.split("/")[1]
        out.append(
            f"| `{h.name}` | {variant} | {'on' if variant in TOPFULL_ON_VARIANTS else 'off'} | "
            f"{_yn(h.name.startswith('final_'))} | {h.onset} | {h.goodput} | {h.p95} | {h.rejection} | "
            f"{h.effect} | `{h.yaml}` | {next_slot(configs_root, h.yaml) if (configs_root / h.yaml).exists() else 'n/a'} |  |"
        )
    out += [
        "",
        "`study6_*` holds are not in the locked `final_` set; a re-run of their cell would be a `final_` hold in the S2 YAML, not a replacement of the study folder.",
        "",
        "## B. Flagged, not recommended for re-run",
        "",
        "| Hold | Why |",
        "| --- | --- |",
    ]
    present = {n for n, _ in flagged}
    for name, why in NOT_RECOMMENDED:
        if name in present:
            out.append(f"| `{name}` | {why} |")
    unconstrained = sorted(n for n, _v in flagged if "4a_unconstrained" in n)
    for name in unconstrained:
        out.append(f"| `{name}` | healthy through the stall: goodput stays near 720 req/s and rejection near 0 |")
    out += [
        "",
        "## C. Confounded S4A-constrained flagged holds",
        "",
        "Any stall damage sits on the clean S4A-constrained collapse floor (goodput about 40 req/s, rejection about 0.93), "
        "so it cannot be separated from the catalog bottleneck. Confounded does not mean unaffected. "
        "After the fixes a re-run would measure the collapse without a stall; whether that is worth a slot is the user's call.",
        "",
        "| Hold | Variant | TopFull | In the locked `final_` set | YAML | Next free run_number | Decision |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for name, variant in sorted(flagged):
        if name in AFFECTED_NAMES:
            continue
        rel = yaml_for(variant, name)
        if rel is None:
            continue
        slot = next_slot(configs_root, rel) if (configs_root / rel).exists() else "n/a"
        out.append(
            f"| `{name}` | {variant} | {'on' if variant in TOPFULL_ON_VARIANTS else 'off'} | "
            f"{_yn(name.startswith('final_'))} | `{rel}` | {slot} |  |"
        )
    out += [
        "",
        "## D. Not in the 2026-10-15 audit",
        "",
        f"The audit file lists 144 holds; `final results/` held {len(legacy)} when this was generated. "
        "Folders whose name does not appear in the audit:",
        "",
    ]
    out += [f"- `{n}`" + (" (flagged)" if n in missing_flagged else "") for n in missing] or ["- none"]
    out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--root", type=Path, default=throttle_flags.DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true", help="print counts only, write nothing")
    args = parser.parse_args(argv)
    legacy = legacy_flagged(args.root)
    flagged = [r for r in legacy if r[2]]
    print(f"runs={len(legacy)} flagged_any_variant={len(flagged)}")
    if args.check:
        return 0
    audit = throttle_flags.AUDIT_PATH.read_text(encoding="utf-8")
    text = render(args.root, DEFAULT_CONFIGS, audit)
    if args.out.exists():
        print(f"[ERROR] {args.out} exists; delete it by hand first (this tool never overwrites).", file=sys.stderr)
        return 1
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
