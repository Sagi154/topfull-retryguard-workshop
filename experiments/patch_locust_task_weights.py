#!/usr/bin/env python3
"""
One-shot patch for locust_online_boutique.py on the loadgen VM.

Adopts Ron Nezer's @task() weight remix — see
docs/superpowers/specs/2026-09-21-loadgen-shape-ron-migration-design.md,
decision 2: postcheckout 50->500, getcart 30->100, postcart 15->1,
emptycart 15->1, getproduct 150->100.

These weights only matter when several Locust tags share one swarm and
Locust splits users between them by weight. Under this repo's adopted
loadgen shape (one independent single-tag swarm per tag — see
experiments/loadgen/online_boutique_create_v2.sh) they are currently
inert for every scenario we run. They are ported here anyway, for
fidelity with Ron's tree, per the same decision.

Usage (on the loadgen VM, after this file is deployed there):
    python3 patch_locust_task_weights.py
"""
from pathlib import Path

TARGET = Path(
    "/home/idozacharia/TopFull/TopFull_loadgen/locust_online_boutique.py"
)

# (function name, old @task weight, new @task weight)
WEIGHT_CHANGES = [
    ("checkout_slow", 50, 500),        # @tag('postcheckout')
    ("viewCart_slow", 30, 100),        # @tag('getcart')
    ("addToCart_slow", 15, 1),         # @tag('postcart')
    ("emptyCart_slow", 15, 1),         # @tag('emptycart')
    ("browseProduct_slow", 150, 100),  # @tag('getproduct')
]


def patch_text(text: str) -> str:
    """
    Apply the weight remix to `text` and return the result.

    Idempotent: if a function's weight is already at its target value,
    that function is left untouched (handles both "already fully patched"
    and "partially hand-patched" inputs identically). Raises SystemExit
    without changing anything if a function's weight is at neither the old
    nor the new value — that means locust_online_boutique.py's shape
    changed and this patch needs a human to re-check it.
    """
    for func_name, old_weight, new_weight in WEIGHT_CHANGES:
        new_block = f"@task({new_weight})\n    def {func_name}(self):"
        if new_block in text:
            continue
        old_block = f"@task({old_weight})\n    def {func_name}(self):"
        if old_block not in text:
            raise SystemExit(
                f"ERROR: found neither @task({old_weight}) nor "
                f"@task({new_weight}) immediately before 'def {func_name}' — "
                "locust_online_boutique.py may have changed; aborting "
                "without changing anything"
            )
        text = text.replace(old_block, new_block, 1)
    return text


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    patched = patch_text(text)
    if patched == text:
        print("ALREADY_PATCHED")
        return
    TARGET.write_text(patched, encoding="utf-8")
    print("PATCHED_OK")


if __name__ == "__main__":
    main()
