"""Did TopFull's proxy and RL loop keep running through a hold?

    python experiments/topfull_health.py "<run_dir>" ["<run_dir>" ...]

Reads topfull_proxy.log and topfull_rl.log (stamped by run_scenario.py) and
topfull_throttle_collector.log. Holds pulled before 2026-10-15 have no proxy
or RL log; the report says "missing" for those.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROXY_LOG = "topfull_proxy.log"
RL_LOG = "topfull_rl.log"
THROTTLE_LOG = "topfull_throttle_collector.log"
MONITOR_TICK = "-------------------------"
STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(.*)$")
APPLY = re.compile(r"Apply threshold to\s+(\S+)\s+:\s+(\S+)")
PROXY_TICK_GAP_S = 5
RL_SILENCE_S = 30


def parse_ts(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def read_stamped(path: Path) -> list[tuple[datetime, str]]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = STAMP.match(line)
        if m:
            out.append((parse_ts(m.group(1)), m.group(2)))
    return out


@dataclass
class Gap:
    seconds: float
    start: datetime | None


def longest_gap(times: list[datetime], end: datetime | None) -> Gap:
    """Longest wait between consecutive times, including the wait from the last one to `end`."""
    points = sorted(times)
    if end is not None and points and end > points[-1]:
        points.append(end)
    best = Gap(0.0, None)
    for a, b in zip(points, points[1:]):
        seconds = (b - a).total_seconds()
        if seconds > best.seconds:
            best = Gap(seconds, a)
    return best


def _fmt(t: datetime | None) -> str:
    return t.strftime("%H:%M:%SZ") if t is not None else "none"


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def throttle_times(run_dir: Path) -> tuple[datetime | None, datetime | None]:
    """(first `fetch failed` stamp, last stamp) of the throttle collector log."""
    path = run_dir / THROTTLE_LOG
    if not path.exists():
        return None, None
    entries = read_stamped(path)
    first_fail = next((t for t, text in entries if "fetch failed" in text), None)
    end = max((t for t, _ in entries), default=None)
    return first_fail, end


def proxy_line(run_dir: Path, end: datetime | None) -> str:
    path = run_dir / PROXY_LOG
    if not path.exists():
        return f"proxy: {PROXY_LOG} missing"
    entries = read_stamped(path)
    ticks = [t for t, text in entries if text.strip() == MONITOR_TICK]
    applies = [t for t, text in entries if APPLY.search(text)]
    gap = longest_gap(ticks, end)
    return (
        f"proxy: lines={len(entries)} ticks={len(ticks)} "
        f"longest_tick_gap_s={gap.seconds:.0f} from {_fmt(gap.start)} "
        f"tick_gap_over_{PROXY_TICK_GAP_S}s={_yes(gap.seconds > PROXY_TICK_GAP_S)} "
        f"applies={len(applies)} last_apply={_fmt(max(applies, default=None))}"
    )


def rl_line(run_dir: Path, end: datetime | None) -> str:
    path = run_dir / RL_LOG
    if not path.exists():
        return f"rl: {RL_LOG} missing"
    entries = read_stamped(path)
    gap = longest_gap([t for t, _ in entries], end)
    return (
        f"rl: lines={len(entries)} longest_silence_s={gap.seconds:.0f} from {_fmt(gap.start)} "
        f"rl_silent_over_{RL_SILENCE_S}s={_yes(gap.seconds > RL_SILENCE_S)}"
    )


def report(run_dir: Path) -> str:
    first_fail, end = throttle_times(run_dir)
    return "\n".join([
        f"TopFull health: {run_dir.name}",
        f"throttle: first_fetch_failure={_fmt(first_fail)} end={_fmt(end)}",
        proxy_line(run_dir, end),
        rl_line(run_dir, end),
    ])


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    for arg in argv:
        print(report(Path(arg)))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
