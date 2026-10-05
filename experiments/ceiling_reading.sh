#!/bin/bash
# One-off readings for the 600 req/s ceiling snapshot. Send over ssh as a script on stdin:
#   ssh <alias> bash -s -- cpu 60 'regex'  < experiments/ceiling_reading.sh
#   ssh topfull-master bash -s -- proxies  < experiments/ceiling_reading.sh
mode="$1"
case "$mode" in
  cpu)
    secs="$2"; pat="${3:-NOMATCH}"
    ta=$(mktemp); tb=$(mktemp)
    a=$(head -n1 /proc/stat); ps -eo pid=,cputimes=,args= > "$ta"
    sleep "$secs"
    b=$(head -n1 /proc/stat); ps -eo pid=,cputimes=,args= > "$tb"
    n=$(nproc)
    echo "$a" "$b" | awk -v n="$n" '{
      # "cpu" plus 10 counters; the second sample starts 11 fields later.
      for (i = 2; i <= 9; i++) { x[i] = $i; y[i] = $(i + 11) }
      ta = 0; tb = 0
      for (i = 2; i <= 9; i++) { ta += x[i]; tb += y[i] }
      d = tb - ta
      idle = (y[5] + y[6]) - (x[5] + x[6])
      printf "nproc %d\nbusy_cores %.2f\nsteal_pct %.2f\n", n, (d - idle) / d * n, (y[9] - x[9]) / d * 100 }'
    echo "### processes matching /$pat/ (percent of one core over ${secs}s)"
    awk -v secs="$secs" -v pat="$pat" 'FNR==NR { ca[$1] = $2; next }
      ($1 in ca) { line = $0; sub(/^ *[0-9]+ +[0-9]+ +/, "", line)
        if (line ~ pat) printf "%6.1f  %s\n", 100 * ($2 - ca[$1]) / secs, substr(line, 1, 100) }' "$ta" "$tb" | sort -rn
    rm -f "$ta" "$tb"
    ;;
  proxies)
    echo "### istio-proxy millicores"
    kubectl top pod --containers -n default | awk 'NR==1 || $2 ~ /istio-proxy/'
    fe=$(kubectl get pod -n default -l app=frontend -o jsonpath='{.items[0].metadata.name}')
    # kubectl top prints millicores ("6m") or whole cores ("2" = 2000m). Rank in millicores.
    hot=$(kubectl top pod --containers -n default | awk '$2 ~ /istio-proxy/ && $1 !~ /^frontend/ { cpu=$3; if (cpu ~ /m$/) sub(/m$/, "", cpu); else cpu = cpu * 1000; print cpu + 0, $1 }' | sort -rn | head -1 | awk '{print $2}')
    for p in $fe $hot; do
      echo "### $p"
      kubectl exec "$p" -n default -c istio-proxy -- sh -c '
        pid=$(ps -eo pid,args | awk "/[e]nvoy -c/ {print \$1; exit}")
        echo "envoy pid ${pid:-none}"
        [ -n "$pid" ] && echo "envoy threads $(ls /proc/$pid/task | wc -l)"
        ps -p "$pid" -o args= | tr " " "\n" | grep -A1 -x -- "--concurrency" || echo "--concurrency absent (default)"'
    done
    ;;
  *)
    echo "usage: cpu <secs> [regex] | proxies" >&2
    exit 2
    ;;
esac
