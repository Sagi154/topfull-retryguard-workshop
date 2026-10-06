"""CPU steal from /proc/stat samples (snapshots and background sampler series).

CLI:
  python experiments/steal_stat.py <run_dir> [<run_dir> ...]        # one line per run
  python experiments/steal_stat.py --md <run_dir> [<run_dir> ...]   # markdown table rows
Files read from <run_dir>/state/: steal_t0_<node>.txt, steal_end_<node>.txt,
steal_series_<node>.txt for node in master, worker, load. The hold window is the first
and last timestamp of <run_dir>/service_inbound.csv (UTC).
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal",
          "guest", "guest_nice"]
NODES = ("master", "worker", "load")


def parse_cpu_line(line: str) -> dict:
    """Parse '[epoch] cpu  user nice ...' from /proc/stat. Missing trailing fields are 0."""
    parts = line.split()
    if "cpu" not in parts[:2]:
        raise ValueError(f"not an aggregate cpu line: {line!r}")
    i = parts.index("cpu")
    epoch = float(parts[0]) if i == 1 else None
    vals = [int(x) for x in parts[i + 1:]]
    vals += [0] * (len(FIELDS) - len(vals))
    out = dict(zip(FIELDS, vals[:len(FIELDS)]))
    out["epoch"] = epoch
    return out


def total_jiffies(s: dict) -> int:
    """user..steal. guest and guest_nice are already counted inside user and nice."""
    return sum(s[k] for k in FIELDS[:8])


def steal_pct(a: dict, b: dict) -> float:
    """Percent of CPU time stolen between two samples (a earlier than b)."""
    dt = total_jiffies(b) - total_jiffies(a)
    ds = b["steal"] - a["steal"]
    if dt <= 0 or ds < 0:
        raise ValueError("counters did not advance (reboot or reordered samples)")
    return 100.0 * ds / dt


def parse_snapshot(text: str):
    """node_steal.sh snap output -> (sample_a, sample_b) from the proc_stat_a / proc_stat_b sections."""
    out, key = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("### "):
            key = line[4:]
            continue
        if key in ("proc_stat_a", "proc_stat_b") and line and key not in out:
            out[key] = parse_cpu_line(line)
    if "proc_stat_a" not in out or "proc_stat_b" not in out:
        raise ValueError("snapshot lacks proc_stat_a / proc_stat_b")
    return out["proc_stat_a"], out["proc_stat_b"]


def read_series(path) -> list:
    """Sampler file: one '<epoch> cpu ...' line per sample. Bad lines are skipped."""
    out = []
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    for line in text.splitlines():
        try:
            s = parse_cpu_line(line)
        except ValueError:
            continue
        if s["epoch"] is not None:
            out.append(s)
    return out


def window_stats(series: list, lo: float, hi: float):
    """Steal % over [lo, hi] (first to last sample inside it), plus the worst consecutive-sample %."""
    w = [s for s in series if lo <= s["epoch"] <= hi]
    if len(w) < 2:
        return None
    worst = 0.0
    for a, b in zip(w, w[1:]):
        try:
            worst = max(worst, steal_pct(a, b))
        except ValueError:
            pass
    return {"pct": steal_pct(w[0], w[-1]), "max_interval_pct": worst, "samples": len(w)}


def _utc(ts: str) -> float:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def hold_window(run_dir) -> tuple:
    with open(Path(run_dir) / "service_inbound.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return _utc(rows[0]["timestamp"]), _utc(rows[-1]["timestamp"])


def score_run(run_dir) -> dict:
    run_dir = Path(run_dir)
    state = run_dir / "state"
    lo, hi = hold_window(run_dir)
    out = {}
    for node in NODES:
        r = {"hold_pct": None, "max_interval_pct": None, "samples": 0,
             "t0_pct": None, "end_pct": None}
        series = state / f"steal_series_{node}.txt"
        if series.exists():
            try:
                w = window_stats(read_series(series), lo, hi)
            except ValueError:
                w = None
            if w:
                r.update(hold_pct=w["pct"], max_interval_pct=w["max_interval_pct"],
                         samples=w["samples"])
        for tag in ("t0", "end"):
            snap = state / f"steal_{tag}_{node}.txt"
            if snap.exists():
                try:
                    a, b = parse_snapshot(snap.read_text(encoding="utf-8-sig", errors="replace"))
                    r[f"{tag}_pct"] = steal_pct(a, b)
                except ValueError:
                    pass
        out[node] = r
    return out


def _f(x):
    return "n/a" if x is None else f"{x:.2f}"


def format_line(label: str, scored: dict) -> str:
    parts = [f"{n} {_f(scored[n]['hold_pct'])}% (max {_f(scored[n]['max_interval_pct'])}, "
             f"n={scored[n]['samples']})" for n in NODES]
    return f"{label} steal " + " | ".join(parts)


def md_row(label: str, scored: dict) -> str:
    cells = [f"{_f(scored[n]['hold_pct'])} / {_f(scored[n]['max_interval_pct'])}" for n in NODES]
    return f"| {label} | " + " | ".join(cells) + " |"


def main(argv):
    md = "--md" in argv
    dirs = [a for a in argv[1:] if a != "--md"]
    if not dirs:
        print(__doc__)
        return 2
    if md:
        print("| Run | master hold % / max | worker hold % / max | load hold % / max |")
        print("|---|---|---|---|")
    for d in dirs:
        label = Path(d).name.replace("baseline_no_topfull_sustained_overload_", "")
        scored = score_run(d)
        print(md_row(label, scored) if md else format_line(label, scored))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
