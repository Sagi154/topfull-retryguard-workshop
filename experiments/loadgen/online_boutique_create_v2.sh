#!/bin/bash
#
# online_boutique_create_v2.sh — drop-in replacement for
# TopFull/TopFull_loadgen/online_boutique_create.sh (+ create2.sh), fixing two
# problems documented in
# docs/superpowers/specs/2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md:
#
#   1. GETCART / POSTCART do nothing today. The upstream scripts route
#      getcart + postcart + emptycart through ONE combined Locust process
#      (`--tags getcart postcart emptycart -u $CART`), so the split between
#      those three tags is silently governed by the locustfile's fixed task
#      weights (30:15:15), not by the per-scenario GETCART/POSTCART YAML
#      values. Here, each of getcart / postcart / emptycart gets its OWN
#      Locust process with its own `-u`, driven by its own env var
#      (GETCART / POSTCART / EMPTYCART).
#
#   2. `-r` (spawn rate) used to be computed as `$((count / RATE))` — i.e. a
#      BIGGER RATE produced a SLOWER ramp (fewer users/sec), the opposite of
#      what the name suggests, and for our (much smaller than TopFull's)
#      target user counts this integer division often rounded down to 0-3
#      users/sec, taking minutes to reach target population. Here, RATE (or
#      a per-tag RATE_* override) is used DIRECTLY as Locust's `-r` users/sec.
#
# This file lives under experiments/ (NOT under TopFull/, which is a
# read-only upstream submodule) and is meant to be deployed next to the
# existing create.sh / create2.sh on topfull-load, then referenced from a
# scenario YAML's `locust.scripts:` list. It does NOT modify or replace the
# existing scripts — they are untouched and still the default.
#
# Requires exactly one change to be adopted end-to-end: run_scenario.py's
# ENV_MAP currently exports emptycart's count as `CART` (a name the upstream
# scripts merged with getcart/postcart). To use this script, that one map
# entry needs to become "emptycart": "EMPTYCART" — see the design doc for
# the exact line. Nothing else about run_scenario.py or the YAML schema
# needs to change: `locust.user_counts.{getproduct,postcheckout,getcart,
# postcart,emptycart}` and `locust.spawn_rate` already exist and already
# flow through as GETPRODUCT/POSTCHECKOUT/GETCART/POSTCART/RATE env vars.
#
# ── Env vars (all optional; ${VAR:-default} mirrors the pattern already
#    patched onto the deployed copies of create.sh/create2.sh — see
#    Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md §7) ──────────────────────
#
#   HOST                  Locust --host target.
#                          Default: http://10.8.0.4:30440 (Istio ingress NodePort;
#                          same fixed value the upstream scripts hardcode)
#   GETPRODUCT            getproduct user count.              Default: 300
#   POSTCHECKOUT          postcheckout user count.             Default: 60
#   GETCART               getcart user count (own process).    Default: 150
#   POSTCART              postcart user count (own process).   Default: 150
#   EMPTYCART             emptycart user count (own process).  Default: 150
#   RATE                  Global spawn rate (users/sec), used DIRECTLY as
#                         Locust `-r` for every tag unless overridden below.
#                         Default: 50
#   RATE_GETPRODUCT / RATE_POSTCHECKOUT / RATE_GETCART / RATE_POSTCART /
#   RATE_EMPTYCART        Optional per-tag spawn-rate override. Default: $RATE.
#   DURATION_MIN          Locust `-t` in minutes. Empty = run untimed;
#                         run_scenario.py already stops Locust itself at
#                         `duration_seconds` via stop_locust(), so this is a
#                         belt-and-suspenders safety valve, not required.
#                         Default: "" (untimed, matches create2.sh's style)
#   WORKERS_GETPRODUCT    Distributed worker-process count for the
#   WORKERS_POSTCHECKOUT  two highest-volume tags (sharding pattern kept from
#                         create.sh — see design doc for why the defaults
#                         here are much lower than TopFull's own 10-20:
#                         our frozen capacity numbers are far below their
#                         Azure D48ds_v5 x3 testbed).
#                         Default: WORKERS_GETPRODUCT=4, WORKERS_POSTCHECKOUT=2
#   LOCUST_BIN            Path to the locust binary.
#                         Default: /home/idozacharia/TopFull/venv/bin/locust
#                         (matches the venv path patched into the deployed
#                         create.sh/create2.sh)
#
# All five tags can also run single-process (WORKERS_*=0) if that is ever
# enough throughput — see the design doc for the sizing rationale.
#
set -u

HOST="${HOST:-http://10.8.0.4:30440}"

GETPRODUCT="${GETPRODUCT:-300}"
POSTCHECKOUT="${POSTCHECKOUT:-60}"
GETCART="${GETCART:-150}"
POSTCART="${POSTCART:-150}"
EMPTYCART="${EMPTYCART:-150}"

RATE="${RATE:-50}"
RATE_GETPRODUCT="${RATE_GETPRODUCT:-$RATE}"
RATE_POSTCHECKOUT="${RATE_POSTCHECKOUT:-$RATE}"
RATE_GETCART="${RATE_GETCART:-$RATE}"
RATE_POSTCART="${RATE_POSTCART:-$RATE}"
RATE_EMPTYCART="${RATE_EMPTYCART:-$RATE}"

DURATION_MIN="${DURATION_MIN:-}"
WORKERS_GETPRODUCT="${WORKERS_GETPRODUCT:-4}"
WORKERS_POSTCHECKOUT="${WORKERS_POSTCHECKOUT:-2}"
LOCUST_BIN="${LOCUST_BIN:-/home/idozacharia/TopFull/venv/bin/locust}"

TIME_FLAG=()
if [[ -n "$DURATION_MIN" ]]; then
  TIME_FLAG=(-t "${DURATION_MIN}m")
fi

# Locust's SimpleHTTPRequestHandler stats server (module-level in
# locust_online_boutique.py) reads one port number from stdin at process
# startup, for every process (master, worker, or standalone) — the upstream
# scripts feed this from small `ports/<port>` files checked into
# TopFull/TopFull_loadgen/ports/. Rather than depend on that checked-in
# range (shared with create.sh/create2.sh, and only covering ports up to
# 8930), this script creates its own port files on demand in a private
# `ports_v2/` directory, in an unused range (91xx-93xx) so it can never
# collide with a concurrently-running upstream script.
mkdir -p ports_v2
ensure_port() {
  local port="$1"
  [[ -f "ports_v2/$port" ]] || echo "$port" > "ports_v2/$port"
}

# ── postcheckout: master + workers (sharding pattern kept from create.sh) ──
tmux kill-session -t v2_postcheckout 2>/dev/null
tmux new-session -d -s v2_postcheckout

ensure_port 9101
tmux new-window -d -t v2_postcheckout \
  "$LOCUST_BIN -f locust_online_boutique.py --host=$HOST --tags postcheckout \
   --master-bind-port=9001 --master --expect-workers=$WORKERS_POSTCHECKOUT \
   --headless -u $POSTCHECKOUT -r $RATE_POSTCHECKOUT ${TIME_FLAG[@]+"${TIME_FLAG[@]}"} \
   < ports_v2/9101"
for i in $(seq 1 "$WORKERS_POSTCHECKOUT"); do
  port=$((9101 + i))
  ensure_port "$port"
  tmux new-window -d -t v2_postcheckout \
    "$LOCUST_BIN -f locust_online_boutique.py --host=$HOST --tags postcheckout \
     --worker --master-port=9001 --master-host=127.0.0.1 < ports_v2/$port"
done

# ── getproduct: master + workers (sharding pattern kept from create.sh) ──
tmux kill-session -t v2_getproduct 2>/dev/null
tmux new-session -d -s v2_getproduct

ensure_port 9201
tmux new-window -d -t v2_getproduct \
  "$LOCUST_BIN -f locust_online_boutique.py --host=$HOST --tags getproduct \
   --master-bind-port=9002 --master --expect-workers=$WORKERS_GETPRODUCT \
   --headless -u $GETPRODUCT -r $RATE_GETPRODUCT ${TIME_FLAG[@]+"${TIME_FLAG[@]}"} \
   < ports_v2/9201"
for i in $(seq 1 "$WORKERS_GETPRODUCT"); do
  port=$((9201 + i))
  ensure_port "$port"
  tmux new-window -d -t v2_getproduct \
    "$LOCUST_BIN -f locust_online_boutique.py --host=$HOST --tags getproduct \
     --worker --master-port=9002 --master-host=127.0.0.1 < ports_v2/$port"
done

# ── getcart / postcart / emptycart: THREE INDEPENDENT single-process
#    sessions — the actual fix for problem #1. No sharding by default:
#    at our target scale (tens to a few hundred users per tag) a single
#    Locust process is plenty; raise WORKERS_* equivalents here yourself
#    (copy the master/worker block above) only if a future scenario needs
#    more than a few hundred rps out of one of these three tags.
declare -A CART_TAG_COUNT=( [getcart]="$GETCART" [postcart]="$POSTCART" [emptycart]="$EMPTYCART" )
declare -A CART_TAG_RATE=( [getcart]="$RATE_GETCART" [postcart]="$RATE_POSTCART" [emptycart]="$RATE_EMPTYCART" )
declare -A CART_TAG_PORT=( [getcart]=9301 [postcart]=9302 [emptycart]=9303 )

for tag in getcart postcart emptycart; do
  session="v2_${tag}"
  port="${CART_TAG_PORT[$tag]}"
  tmux kill-session -t "$session" 2>/dev/null
  tmux new-session -d -s "$session"
  ensure_port "$port"
  tmux new-window -d -t "$session" \
    "$LOCUST_BIN -f locust_online_boutique.py --host=$HOST --tags $tag \
     --headless -u ${CART_TAG_COUNT[$tag]} -r ${CART_TAG_RATE[$tag]} \
     ${TIME_FLAG[@]+"${TIME_FLAG[@]}"} < ports_v2/$port"
done
