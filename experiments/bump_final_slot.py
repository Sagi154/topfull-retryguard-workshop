"""Advance run_number and log_folder on one S2/S3/S4 final_configs YAML.

The campaign file stays the runner input. Rep 1 uses the run1 name already
in the file. After that folder is pulled, bump to run2 and launch again.
After rep 2 is pulled, bump to run3 so a later hold cannot reuse the name
on master.

    python experiments/bump_final_slot.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_PREFIXES = (
    "s2_",
    "s3_",
    "4a_constrained_",
    "4a_unconstrained_",
    "4b_",
)


def _ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def bump_text(text: str) -> str:
    """Advance the two slot lines. The final_configs tree is CRLF; keep each line's ending."""
    lines = text.splitlines(keepends=True)
    current = None
    for line in lines:
        match = re.fullmatch(r"run_number:[ \t]*(\d+)[ \t]*", line.rstrip("\r\n"))
        if match:
            current = int(match.group(1))
            break
    if current is None:
        raise SystemExit("run_number missing")
    nxt = current + 1
    found_folder = False
    out: list[str] = []
    for line in lines:
        ending = _ending(line)
        stripped = line.rstrip("\r\n")
        if re.fullmatch(r"run_number:[ \t]*\d+[ \t]*", stripped):
            out.append(f"run_number: {nxt}{ending}")
            continue
        match = re.fullmatch(r"log_folder:[ \t]*(\S+_run)\d+[ \t]*", stripped)
        if match:
            out.append(f"log_folder: {match.group(1)}{nxt}{ending}")
            found_folder = True
            continue
        out.append(line)
    if not found_folder:
        raise SystemExit("log_folder missing or not final_*_runN")
    return "".join(out)


def bump_file(path: Path) -> int:
    resolved = path if path.is_absolute() else Path.cwd() / path
    parts = resolved.parts
    if "final_configs" not in parts:
        raise SystemExit(f"refusing {path}: not under final_configs")
    if not any(path.name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise SystemExit(f"refusing {path}: not an S2/S3/S4 campaign file")
    original = path.read_bytes().decode("utf-8")
    updated = bump_text(original)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
    match = re.search(r"(?m)^run_number:[ \t]*(\d+)[ \t]*\r?$", updated)
    return int(match.group(1))


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit("usage: python experiments/bump_final_slot.py <yaml>")
    path = Path(argv[1])
    new_run = bump_file(path)
    print(f"{path}: run {new_run - 1} -> {new_run}")


if __name__ == "__main__":
    main(sys.argv)
