#!/usr/bin/env python3
"""Generate the 2026-10-09 re-enable sweep (set A) and S3/S4 (set B) YAMLs.

Template is the locked Paper-C1 RetryGuard-only Scenario 2 config. Each hold
is a deep copy with the study overrides applied. Run order inside a set is
repeat 1 shuffled, then repeat 2 shuffled, from one Random seeded per set.

    python experiments/make_study_configs.py --write
"""

from __future__ import annotations

import argparse
import copy
import random
from pathlib import Path

import yaml

TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "configs" / "scenario_2_retryguard_no_topfull.yaml"
)
OUT_DIR = Path(__file__).resolve().parent / "configs" / "study_2026_10_09"
PLAN_FILE = "docs/superpowers/plans/2026-10-09-reenable-rejection-and-s3-s4-runs.md"

S2_COUNTS = {
    "getproduct": 275,
    "postcheckout": 90,
    "getcart": 100,
    "postcart": 90,
    "emptycart": 5,
}
S1_COUNTS = {
    "getproduct": 175,
    "postcheckout": 30,
    "getcart": 70,
    "postcart": 90,
    "emptycart": 5,
}

# (token, topfull_rl.enabled, retryguard.enabled, condition)
SET_A_ARMS = (
    ("rgtf0", False, True, "retryguard"),
    ("rgtf1", True, True, "retryguard"),
)
SET_A_THRESHOLDS = (
    (0.10, "010"),
    (0.15, "015"),
    (0.20, "020"),
)

# (token, scenario_id, scenario_name, deployment, cpu_limit_millicores)
SET_B_SCENARIOS = (
    ("s3", 3, "targeted_bottleneck", "checkoutservice", 300),
    ("s4a", 4, "topology_position_A", "productcatalogservice", 300),
    ("s4b", 4, "topology_position_B", "emailservice", 40),
)
SET_B_ARMS = (
    ("tf1rg0", True, False, "baseline"),
    ("tf0rg1", False, True, "retryguard"),
    ("tf1rg1", True, True, "retryguard"),
)

SET_A_SEED = 20261009
SET_B_SEED = 20261010


def _load_template() -> dict:
    with TEMPLATE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _replace_cpu_limit(cfg: dict, deployment: str, millicores: int) -> None:
    matches = [row for row in cfg["scale_constraints"] if row["deployment"] == deployment]
    if len(matches) != 1:
        raise KeyError(f"{deployment} appears {len(matches)} times in scale_constraints")
    matches[0]["cpu_limit_millicores"] = millicores


def _apply_common(cfg: dict, *, topfull: bool, retryguard: bool, condition: str,
                  reenable: float, log_folder: str, user_counts: dict) -> None:
    cfg["condition"] = condition
    cfg["duration_seconds"] = 600
    cfg["locust"]["user_counts"] = dict(user_counts)
    cfg["topfull_rl"]["enabled"] = topfull
    cfg["retryguard"]["enabled"] = retryguard
    cfg["retryguard"]["reenable_rejection"] = reenable
    cfg["log_folder"] = log_folder


def _set_a_cells() -> list[dict]:
    cells = []
    for reenable, token in SET_A_THRESHOLDS:
        for arm, topfull, retryguard, condition in SET_A_ARMS:
            cells.append({
                "set": "A",
                "reenable": reenable,
                "arm": arm,
                "topfull": topfull,
                "retryguard": retryguard,
                "condition": condition,
                "log_stem": f"study2_s2_rr{token}_{arm}",
                "scenario_id": 2,
                "scenario_name": "sustained_overload",
                "user_counts": S2_COUNTS,
                "limit": None,
            })
    return cells


def _set_b_cells() -> list[dict]:
    cells = []
    for token, scenario_id, scenario_name, deployment, millicores in SET_B_SCENARIOS:
        for arm, topfull, retryguard, condition in SET_B_ARMS:
            cells.append({
                "set": "B",
                "reenable": 0.15,
                "arm": arm,
                "topfull": topfull,
                "retryguard": retryguard,
                "condition": condition,
                "log_stem": f"study2_{token}_{arm}",
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "user_counts": S1_COUNTS,
                "limit": (deployment, millicores),
            })
    return cells


def _blocked_order(cells: list[dict], seed: int) -> list[dict]:
    """Shuffle repeat 1, then repeat 2, from one Random. order_index starts at 1."""
    rng = random.Random(seed)
    ordered = []
    for rep in (1, 2):
        block = [dict(cell, rep=rep) for cell in cells]
        rng.shuffle(block)
        ordered.extend(block)
    for index, cell in enumerate(ordered, start=1):
        cell["order_index"] = index
    return ordered


def _materialize(template: dict, cell: dict) -> dict:
    cfg = copy.deepcopy(template)
    cfg["scenario_id"] = cell["scenario_id"]
    cfg["scenario_name"] = cell["scenario_name"]
    log_folder = f"{cell['log_stem']}_rep{cell['rep']}"
    counts = cell["user_counts"]
    mix = "/".join(
        str(counts[k])
        for k in ("getproduct", "postcheckout", "getcart", "postcart", "emptycart")
    )
    limit_note = ""
    if cell["limit"] is not None:
        deployment, millicores = cell["limit"]
        limit_note = f" {deployment} cpu_limit_millicores={millicores}."
    cfg["description"] = (
        f"Study 2026-10-09 {log_folder}: {cell['scenario_name']} {mix}, "
        f"reenable_rejection={cell['reenable']:.2f}, "
        f"topfull_rl={cell['topfull']}, retryguard={cell['retryguard']}."
        f"{limit_note} Paper-C1, paper_cpu_reconcile false, "
        "restart_before_hold checkoutservice and recommendationservice."
    )
    _apply_common(
        cfg,
        topfull=cell["topfull"],
        retryguard=cell["retryguard"],
        condition=cell["condition"],
        reenable=cell["reenable"],
        log_folder=log_folder,
        user_counts=cell["user_counts"],
    )
    if cell["limit"] is not None:
        deployment, millicores = cell["limit"]
        _replace_cpu_limit(cfg, deployment, millicores)
    path = OUT_DIR / f"{cell['order_index']:02d}_{cell['set']}_{log_folder}.yaml"
    return {
        "path": path,
        "set": cell["set"],
        "order_index": cell["order_index"],
        "cfg": cfg,
    }


def build_configs() -> list[dict]:
    template = _load_template()
    ordered = _blocked_order(_set_a_cells(), SET_A_SEED)
    ordered.extend(_blocked_order(_set_b_cells(), SET_B_SEED))
    return [_materialize(template, cell) for cell in ordered]


def write_configs(cfgs: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        "# Generated by experiments/make_study_configs.py\n"
        f"# Plan: {PLAN_FILE}\n"
    )
    for item in cfgs:
        text = header + yaml.safe_dump(item["cfg"], sort_keys=False, default_flow_style=False)
        Path(item["path"]).write_text(text, encoding="utf-8", newline="\n")


def format_order_table(cfgs: list[dict]) -> str:
    rows = sorted(cfgs, key=lambda c: (c["set"], c["order_index"]))
    lines = [
        f"{'set':<4} {'order':>5}  {'log_folder':<40}  {'tf':<5} {'rg':<5} {'cond':<10} reenable",
    ]
    for item in rows:
        cfg = item["cfg"]
        lines.append(
            f"{item['set']:<4} {item['order_index']:>5}  {cfg['log_folder']:<40}  "
            f"{str(cfg['topfull_rl']['enabled']):<5} {str(cfg['retryguard']['enabled']):<5} "
            f"{cfg['condition']:<10} {cfg['retryguard']['reenable_rejection']:.2f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 2026-10-09 study configs.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write YAMLs under experiments/configs/study_2026_10_09/ and print the order table.",
    )
    args = parser.parse_args()
    cfgs = build_configs()
    if not args.write:
        parser.error("pass --write to emit the study YAMLs")
    write_configs(cfgs)
    print(format_order_table(cfgs))


if __name__ == "__main__":
    main()
