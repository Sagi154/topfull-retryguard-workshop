"""Generate the 15 replay YAMLs from locked final_configs/ copies.

Only run_number and log_folder differ from the source.
S2 both_normal is run 4 because analysis_s2_both_normal_run3 already exists.
Every other slot is run 3.

Run: python experiments/make_analysis_runs_replay_configs.py
"""
from __future__ import annotations

from pathlib import Path

import make_analysis_runs_configs as base

OUT = Path(__file__).resolve().parent / "configs" / "analysis_runs_replay"

# (group, source dir under final_configs/, prefix, variant, run_number)
_GROUPS = [
    ("s2", "2", "s2", {"both_normal": 4}),
    ("s3", "3", "s3", {}),
    ("s4a_unconstrained", "4/4a_unconstrained", "4a_unconstrained", {}),
]
SLOTS = [
    (group, src_dir, prefix, variant, overrides.get(variant, 3))
    for group, src_dir, prefix, overrides in _GROUPS
    for variant in base.VARIANTS
]


def build_text(source_text: str, log_folder: str, run_number: int) -> str:
    return base.build_text(source_text, log_folder, run_number)


def generate(out_dir: Path | None = None) -> list[Path]:
    root = OUT if out_dir is None else out_dir
    written = []
    for group, src_dir, prefix, variant, n in SLOTS:
        src = base.SRC / src_dir / f"{prefix}_{variant}.yaml"
        log_folder = f"analysis_{prefix}_{variant}_run{n}"
        dest = root / group / f"{prefix}_{variant}_run{n}.yaml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            build_text(src.read_text(encoding="utf-8"), log_folder, n),
            encoding="utf-8", newline="\n")
        written.append(dest)
    return written


if __name__ == "__main__":
    for path in generate():
        print(path)
