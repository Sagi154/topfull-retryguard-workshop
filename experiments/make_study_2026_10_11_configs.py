#!/usr/bin/env python3
"""Generate the 2026-10-11 S2-tuning (4 holds) and S3/S4A/S4B topology (10
holds) study YAMLs.

Template is the locked Paper-C1 RetryGuard-only Scenario 2 config. Each cell
is a deep copy with the study overrides applied: scenario id/name, Locust
user counts, one scale_constraints CPU override (S3/S4A/S4B only), the tuned
RetryGuard parameter set, topfull_rl.enabled, log_folder, and description.
`restart_before_hold` is dropped if the template still has it. Checkout and
recommendations stay up.

    python experiments/make_study_2026_10_11_configs.py --write
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml

TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "configs" / "scenario_2_retryguard_no_topfull.yaml"
)
OUT_DIR = Path(__file__).resolve().parent / "configs" / "study_2026_10_11"
PLAN_FILE = "docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-holds.md"

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

# Tuned RetryGuard parameter set, shared by all 14 holds in this study.
TUNED_RETRYGUARD = {
    "interval_samples": 20,
    "retries_threshold": 0.4,
    "climb_rpr_1_to_2": 0.16,
    "climb_rpr_2_to_3": 0.32,
    "climb_interval_seconds": 10,
    "reenable_rejection": 0.25,
}

CELLS = [
    # (order, file, scenario_id, scenario_name, user_counts, limits, topfull, log_folder, note)
    (1, "01_s2_tune_rgtf0_rep1.yaml", 2, "sustained_overload", S2_COUNTS, [],
     False, "study4_s2_tune_rgtf0_rep1", "S2 tuned RetryGuard params, repeat 1, TopFull off."),
    (2, "02_s2_tune_rgtf1_rep1.yaml", 2, "sustained_overload", S2_COUNTS, [],
     True, "study4_s2_tune_rgtf1_rep1", "S2 tuned RetryGuard params, repeat 1, TopFull on."),
    (3, "03_s2_tune_rgtf0_rep2.yaml", 2, "sustained_overload", S2_COUNTS, [],
     False, "study4_s2_tune_rgtf0_rep2", "S2 tuned RetryGuard params, repeat 2, TopFull off."),
    (4, "04_s2_tune_rgtf1_rep2.yaml", 2, "sustained_overload", S2_COUNTS, [],
     True, "study4_s2_tune_rgtf1_rep2", "S2 tuned RetryGuard params, repeat 2, TopFull on."),
    (5, "05_s3_ck300_rgtf0.yaml", 3, "targeted_bottleneck", S1_COUNTS,
     [("checkoutservice", 300)], False, "study4_s3_ck300_rgtf0",
     "S3 checkoutservice 300m, tuned RetryGuard params, TopFull off."),
    (6, "06_s3_ck300_rgtf1.yaml", 3, "targeted_bottleneck", S1_COUNTS,
     [("checkoutservice", 300)], True, "study4_s3_ck300_rgtf1",
     "S3 checkoutservice 300m, tuned RetryGuard params, TopFull on."),
    (7, "07_s4a_pc400_u140_rgtf0.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 140}, [("productcatalogservice", 400)], False,
     "study4_s4a_pc400_u140_rgtf0",
     "S4A productcatalogservice 400m, postcart 90->140, TopFull off."),
    (8, "08_s4a_pc400_u140_rgtf1.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 140}, [("productcatalogservice", 400)], True,
     "study4_s4a_pc400_u140_rgtf1",
     "S4A productcatalogservice 400m, postcart 90->140, TopFull on."),
    (9, "09_s4a_pc400_u190_rgtf0.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 190}, [("productcatalogservice", 400)], False,
     "study4_s4a_pc400_u190_rgtf0",
     "S4A productcatalogservice 400m, postcart 90->190, TopFull off."),
    (10, "10_s4a_pc400_u190_rgtf1.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 190}, [("productcatalogservice", 400)], True,
     "study4_s4a_pc400_u190_rgtf1",
     "S4A productcatalogservice 400m, postcart 90->190, TopFull on."),
    (11, "11_s4b_em50_rgtf0.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 50)], False, "study4_s4b_em50_rgtf0",
     "S4B emailservice 50m, tuned RetryGuard params, TopFull off."),
    (12, "12_s4b_em50_rgtf1.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 50)], True, "study4_s4b_em50_rgtf1",
     "S4B emailservice 50m, tuned RetryGuard params, TopFull on."),
    (13, "13_s4b_em60_rgtf0.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 60)], False, "study4_s4b_em60_rgtf0",
     "S4B emailservice 60m, tuned RetryGuard params, TopFull off."),
    (14, "14_s4b_em60_rgtf1.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 60)], True, "study4_s4b_em60_rgtf1",
     "S4B emailservice 60m, tuned RetryGuard params, TopFull on."),
]


def _load_template() -> dict:
    with TEMPLATE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _replace_cpu_limit(cfg: dict, deployment: str, millicores: int) -> None:
    matches = [row for row in cfg["scale_constraints"] if row["deployment"] == deployment]
    if len(matches) != 1:
        raise KeyError(f"{deployment} appears {len(matches)} times in scale_constraints")
    matches[0]["cpu_limit_millicores"] = millicores


def _materialize(template: dict, cell: tuple) -> dict:
    order, fname, scenario_id, scenario_name, user_counts, limits, topfull, log_folder, note = cell
    cfg = copy.deepcopy(template)
    cfg.pop("restart_before_hold", None)
    cfg["scenario_id"] = scenario_id
    cfg["scenario_name"] = scenario_name
    cfg["run_number"] = 1
    cfg["condition"] = "retryguard"
    cfg["locust"]["user_counts"] = dict(user_counts)
    cfg["topfull_rl"]["enabled"] = topfull
    rg = cfg["retryguard"]
    rg["enabled"] = True
    for key, value in TUNED_RETRYGUARD.items():
        rg[key] = value
    for deployment, millicores in limits:
        _replace_cpu_limit(cfg, deployment, millicores)
    cfg["log_folder"] = log_folder
    mix = "/".join(
        str(user_counts[k])
        for k in ("getproduct", "postcheckout", "getcart", "postcart", "emptycart")
    )
    cfg["description"] = f"Study 2026-10-11 {log_folder} ({mix}): {note}"
    return {"path": OUT_DIR / fname, "order": order, "cfg": cfg}


def build_configs() -> list[dict]:
    template = _load_template()
    return [_materialize(template, cell) for cell in CELLS]


def write_configs(items: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = f"# Generated by experiments/make_study_2026_10_11_configs.py\n# Plan: {PLAN_FILE}\n"
    for item in items:
        text = header + yaml.safe_dump(item["cfg"], sort_keys=False, default_flow_style=False)
        Path(item["path"]).write_text(text, encoding="utf-8", newline="\n")


def format_order_table(items: list[dict]) -> str:
    rows = sorted(items, key=lambda c: c["order"])
    lines = [
        f"{'order':>5}  {'log_folder':<32}  {'sid':>3} {'scenario_name':<20}  {'tf':<5}  user_counts",
    ]
    for item in rows:
        cfg = item["cfg"]
        counts = cfg["locust"]["user_counts"]
        mix = "/".join(str(counts[k]) for k in
                        ("getproduct", "postcheckout", "getcart", "postcart", "emptycart"))
        lines.append(
            f"{item['order']:>5}  {cfg['log_folder']:<32}  {cfg['scenario_id']:>3} "
            f"{cfg['scenario_name']:<20}  {str(cfg['topfull_rl']['enabled']):<5}  {mix}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 2026-10-11 study configs.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write YAMLs under experiments/configs/study_2026_10_11/ and print the order table.",
    )
    args = parser.parse_args()
    items = build_configs()
    if not args.write:
        parser.error("pass --write to emit the study YAMLs")
    write_configs(items)
    print(format_order_table(items))


if __name__ == "__main__":
    main()
