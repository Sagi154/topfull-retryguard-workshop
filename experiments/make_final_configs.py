"""Generate experiments/configs/final_configs/ from the locked scenario YAMLs.

Copies only. The sources under experiments/configs/ are not modified.
Burst mode keeps the three ADR 0008 burst keys. Normal mode omits them.
RetryGuard-only sets topfull_rl.enabled to false.

Run from the repo root:
    python experiments/make_final_configs.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIGS = ROOT / "configs"
OUT = CONFIGS / "final_configs"

BURST_KEYS = (
    "burst_rpr:",
    "burst_window_seconds:",
    "burst_min_first_attempts:",
)

# folder under final_configs, filename prefix, baseline source, retryguard source
SCENARIOS = (
    ("1", "s1", "scenario_1_baseline.yaml", "scenario_1_retryguard.yaml"),
    ("2", "s2", "scenario_2_baseline.yaml", "scenario_2_retryguard.yaml"),
    ("3", "s3", "scenario_3_baseline.yaml", "scenario_3_retryguard.yaml"),
    (
        "4/4a_unconstrained",
        "4a_unconstrained",
        "scenario_4a_unconstrained_baseline.yaml",
        "scenario_4a_unconstrained_retryguard.yaml",
    ),
    (
        "4/4a_constrained",
        "4a_constrained",
        "scenario_4a_constrained_baseline.yaml",
        "scenario_4a_constrained_retryguard.yaml",
    ),
    ("4/4b", "4b", "scenario_4b_baseline.yaml", "scenario_4b_retryguard.yaml"),
)

# variant name, source arm ("baseline" or "retryguard"), burst keys, topfull on
VARIANTS = (
    ("rg_only_burst", "retryguard", True, False),
    ("rg_only_normal", "retryguard", False, False),
    ("tf_only", "baseline", True, True),
    ("both_burst", "retryguard", True, True),
    ("both_normal", "retryguard", False, True),
)


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _extract_scale_constraints(text: str) -> str:
    """The scale_constraints block from the S2 baseline (plain Paper-C1)."""
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith("scale_constraints:"))
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith("-") or line.startswith(" "):
            end += 1
            continue
        break
    block = "".join(lines[start:end])
    if not block.endswith(("\n", "\r\n")):
        block += _newline(text)
    return block


def _fill_empty_scale_constraints(text: str, paper_block: str) -> str:
    """S1 sources use scale_constraints: []. Final copies carry Paper-C1."""
    if not re.search(r"^scale_constraints:\s*\[\]\s*$", text, flags=re.M):
        return text
    nl = _newline(text)
    note = (
        "# Paper-C1 millicores (ADR 0009). Frontend 1150m is the HPA pin,"
        + nl
        + "# not a scale_constraint. Written into this final_configs copy;"
        + nl
        + "# the source YAML still has an empty list."
        + nl
    )
    text = re.sub(
        r"^# None — full replica counts, no CPU limits\. Baseline cluster state\.\r?\n",
        "",
        text,
        count=1,
        flags=re.M,
    )
    if not paper_block.endswith(("\n", "\r\n")):
        paper_block += nl
    return re.sub(
        r"^scale_constraints:[ \t]*\[\][ \t]*$",
        (note + paper_block).rstrip("\r\n"),
        text,
        count=1,
        flags=re.M,
    )


def _strip_burst(text: str) -> str:
    kept = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if any(stripped.startswith(key) for key in BURST_KEYS):
            continue
        kept.append(line)
    return "".join(kept)


def _set_topfull_rl(text: str, enabled: bool) -> str:
    value = "true" if enabled else "false"
    if re.search(r"^topfull_rl:\s*$", text, flags=re.M):
        return re.sub(
            r"(^topfull_rl:\s*\r?\n[ \t]*enabled:[ \t]*)(true|false)",
            rf"\g<1>{value}",
            text,
            count=1,
            flags=re.M,
        )
    nl = _newline(text)
    block = f"topfull_rl:{nl}  enabled: {value}{nl}"
    return text.replace(f"retryguard:{nl}", block + f"retryguard:{nl}", 1)


def _set_run_slot(text: str, log_folder: str) -> str:
    text = re.sub(r"^run_number:\s*\d+", "run_number: 1", text, count=1, flags=re.M)
    text = re.sub(
        r"^log_folder:\s*\S+",
        f"log_folder: {log_folder}",
        text,
        count=1,
        flags=re.M,
    )
    return text


def _header(source_name: str, variant: str, burst: bool, nl: str) -> str:
    mode = (
        "Burst mode: the three burst keys are present "
        "(burst_rpr, burst_window_seconds, burst_min_first_attempts)."
        if burst
        else "Normal mode: those three burst keys are omitted."
    )
    lines = [
        "# final_configs copy. Do not edit the source from here.",
        f"# Source: experiments/configs/{source_name}",
        f"# Variant: {variant}.",
        f"# {mode}",
        "#",
    ]
    return nl.join(lines) + nl + nl


def build_one(
    source_text: str,
    source_name: str,
    variant: str,
    burst: bool,
    topfull: bool,
    log_folder: str,
    paper_block: str,
) -> str:
    text = _fill_empty_scale_constraints(source_text, paper_block)
    if not burst:
        text = _strip_burst(text)
    text = _set_topfull_rl(text, topfull)
    text = _set_run_slot(text, log_folder)
    nl = _newline(text)
    return _header(source_name, variant, burst, nl) + text


def generate() -> list[Path]:
    paper_block = _extract_scale_constraints(
        (CONFIGS / "scenario_2_baseline.yaml").read_text(encoding="utf-8")
    )
    written: list[Path] = []
    for folder, prefix, baseline_name, retryguard_name in SCENARIOS:
        sources = {
            "baseline": (CONFIGS / baseline_name).read_text(encoding="utf-8"),
            "retryguard": (CONFIGS / retryguard_name).read_text(encoding="utf-8"),
        }
        names = {"baseline": baseline_name, "retryguard": retryguard_name}
        dest_dir = OUT / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        for variant, arm, burst, topfull in VARIANTS:
            log_folder = f"final_{prefix}_{variant}_run1"
            body = build_one(
                sources[arm],
                names[arm],
                variant,
                burst,
                topfull,
                log_folder,
                paper_block,
            )
            path = dest_dir / f"{prefix}_{variant}.yaml"
            path.write_text(body, encoding="utf-8", newline="")
            written.append(path)
    return written


def main() -> None:
    written = generate()
    print(f"wrote {len(written)} configs under {OUT}")
    for path in written:
        print(path.relative_to(ROOT.parent))


if __name__ == "__main__":
    main()
