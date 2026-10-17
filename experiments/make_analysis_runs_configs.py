"""Generate the 60 analysis-run YAMLs from the locked final_configs/ copies.

Only run_number and log_folder differ from the source. Run: python experiments/make_analysis_runs_configs.py
"""
from __future__ import annotations

import re
from pathlib import Path

CONFIGS = Path(__file__).resolve().parent / "configs"
SRC = CONFIGS / "final_configs"
OUT = CONFIGS / "analysis_runs"

# (group folder, source dir under final_configs/, file-name prefix)
GROUPS = [
    ("s1", "1", "s1"),
    ("s2", "2", "s2"),
    ("s3", "3", "s3"),
    ("s4a_constrained", "4/4a_constrained", "4a_constrained"),
    ("s4a_unconstrained", "4/4a_unconstrained", "4a_unconstrained"),
    ("s4b", "4/4b", "4b"),
]
VARIANTS = ["rg_only_normal", "both_normal", "tf_only",
            "rg_only_burst", "both_burst"]
REPEATS = (1, 2)


def build_text(source_text: str, log_folder: str, run_number: int) -> str:
    text = re.sub(r"^run_number:\s*\d+", f"run_number: {run_number}",
                  source_text, count=1, flags=re.M)
    text, n = re.subn(
        r"^log_folder:\s*\S+",
        f"log_folder: {log_folder}",
        text, count=1, flags=re.M)
    if n != 1:
        raise ValueError("source has no log_folder line")
    return text


def generate() -> list[Path]:
    written = []
    for group, src_dir, prefix in GROUPS:
        out_dir = OUT / group
        out_dir.mkdir(parents=True, exist_ok=True)
        for variant in VARIANTS:
            src = SRC / src_dir / f"{prefix}_{variant}.yaml"
            source_text = src.read_text(encoding="utf-8")
            for n in REPEATS:
                log_folder = f"analysis_{prefix}_{variant}_run{n}"
                dest = out_dir / f"{prefix}_{variant}_run{n}.yaml"
                dest.write_text(build_text(source_text, log_folder, n),
                                encoding="utf-8", newline="\n")
                written.append(dest)
    return written


if __name__ == "__main__":
    for p in generate():
        print(p)
