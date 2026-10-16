"""One-shot: replace the "stay valid / remain valid" sentence in Guides and Info/*.md.

    python experiments/retire_stay_valid.py            # dry run: counts per file
    python experiments/retire_stay_valid.py --write

The throttle-flag notes (and the 2026-10-15 re-run guide) said goodput, P95, rejection, and
retry numbers of a flagged hold stay valid because they do not read topfull_throttle.csv.
The proxy descriptor evidence shows they are not safe to assume: a proxy that ran out of
file descriptors refuses new connections on every variant. Only the two known sentences
are rewritten; leftovers are printed for manual review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GUIDES = Path(__file__).resolve().parent.parent / "Guides and Info"
EVIDENCE = "2026-10-15-proxy-fd-evidence-flagged-holds.md"
REPLACEMENT = (
    "Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran "
    f"out of file descriptors refuses new connections on every variant, so whether they are clean "
    f"for this hold is decided by [{EVIDENCE}]({EVIDENCE}), not by this flag."
)
PATTERNS = [
    re.compile(r"Goodput, P95, rejection, and retry numbers do not use `topfull_throttle\.csv` and stay valid\."),
    re.compile(r"Goodput, P95, rejection, and retry numbers do not use that file and remain valid\."),
]


def rewrite(text: str) -> tuple[str, int]:
    total = 0
    for pattern in PATTERNS:
        text, n = pattern.subn(lambda _m: REPLACEMENT, text)
        total += n
    return text, total


def run(guides_dir: Path, write: bool) -> dict:
    changed = {}
    for path in sorted(Path(guides_dir).glob("*.md")):
        if path.name == EVIDENCE:
            continue
        raw = path.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in raw else "\n"
        new, n = rewrite(raw.replace("\r\n", "\n"))
        if n:
            changed[path.name] = n
            if write:
                path.write_bytes(new.replace("\n", eol).encode("utf-8"))
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    changed = run(GUIDES, args.write)
    for name, n in changed.items():
        print(f"{name}: {n}")
    print(f"{'rewrote' if args.write else 'would rewrite'} {sum(changed.values())} sentence(s) in {len(changed)} file(s)")
    for path in sorted(GUIDES.glob("*.md")):
        if path.name == EVIDENCE:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if re.search(r"(stay|stays|remain)s? valid", line) and "Goodput" in line:
                print(f"REVIEW {path.name}:{number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
