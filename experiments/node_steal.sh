#!/bin/bash
# CPU steal capture for one node. Sent over ssh as a script on stdin; the mode follows "--":
#   ssh <alias> bash -s -- snap                 < experiments/node_steal.sh
#   ssh <alias> bash -s -- start /tmp/file.txt  < experiments/node_steal.sh
#   ssh <alias> bash -s -- stop  /tmp/file.txt  < experiments/node_steal.sh
# snap  : /proc/stat cpu line, a 10 s vmstat (its "st" column is steal), a 1 s mpstat if
#         installed, then the /proc/stat cpu line again (so one snapshot is a 10 s steal reading).
# start : appends "<epoch> <cpu line>" every 5 s to the file until stopped.
# stop  : stops that sampler.
mode="$1"
cpu_line() { echo "$(date +%s) $(head -n 1 /proc/stat)"; }
case "$mode" in
  snap)
    echo "### proc_stat_a"
    cpu_line
    echo "### vmstat_10s"
    if command -v vmstat >/dev/null 2>&1; then vmstat 10 2; else echo "vmstat unavailable"; sleep 10; fi
    echo "### mpstat"
    if command -v mpstat >/dev/null 2>&1; then mpstat 1 1; else echo "mpstat unavailable"; fi
    echo "### proc_stat_b"
    cpu_line
    ;;
  start)
    out="$2"
    if [ -f "$out.pid" ]; then kill "$(cat "$out.pid")" 2>/dev/null || true; fi
    : > "$out"
    nohup bash -c 'while true; do echo "$(date +%s) $(head -n 1 /proc/stat)"; sleep 5; done' >> "$out" 2>/dev/null < /dev/null &
    echo $! > "$out.pid"
    echo "sampler started pid $(cat "$out.pid") -> $out"
    ;;
  stop)
    out="$2"
    if [ -f "$out.pid" ]; then kill "$(cat "$out.pid")" 2>/dev/null || true; rm -f "$out.pid"; fi
    echo "sampler stopped; $(wc -l < "$out") lines in $out"
    ;;
  *)
    echo "usage: snap | start <file> | stop <file>" >&2
    exit 2
    ;;
esac
