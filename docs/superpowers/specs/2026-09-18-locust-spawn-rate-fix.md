# Locust spawn-rate isolation + frontend-2× 1.5× / 2× re-run (2026-09-18)

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Root-cause of the flat 1× / 2× / 6× frontend inbound λ series; isolated
> fix via a private Locust launcher; re-ran frontend-2× baselines at 1.5× and
> 2× with a working spawn. Shared `online_boutique_create.sh` left untouched.

Related: [2026-09-17-s2-frontend-2x-user-scale-design.md](2026-09-17-s2-frontend-2x-user-scale-design.md),
[2026-09-17-s2-frontend-2x-quota-design.md](2026-09-17-s2-frontend-2x-quota-design.md).

---

## 1. Bug

On `topfull-load`, untracked
`/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create.sh` starts
three Locust masters with:

```bash
-r $((POSTCHECKOUT / RATE))
-r $((GETPRODUCT / RATE))
-r $((CART / RATE))
```

Locust `-r` is users/sec. YAML `spawn_rate` is exported as `RATE` by
`run_scenario.py`. Scaling both `user_counts` and `spawn_rate` by the same
factor leaves `count/RATE` invariant (~3 for cart, ~1 for getproduct, **0**
for postcheckout). So the old 1× / 2× / 6× probes all ramped the distributed
swarm at ~3 cart users/s; 6× never finished its ramp in 600 s.

`create2.sh` (second swarm) already uses hardcoded `-r` and was not the
blocker. `GETCART` / `POSTCART` env vars are set but unused as `-u`.
`run_scenario.py` exports were correct — no orchestrator change.

## 2. Isolation (do not affect S1–S6)

**Did not edit** shared `online_boutique_create.sh` or `create2.sh`.

Added probe-only launcher:

- Repo: [`experiments/loadgen/online_boutique_create_probe.sh`](../../experiments/loadgen/online_boutique_create_probe.sh)
- VM: `/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_probe.sh`
- Change: three masters use `-r $RATE` (YAML spawn_rate as Locust users/sec)

Only these YAMLs point at it:

- `scenario_2_baseline_frontend_2x_users15.yaml`
- `scenario_2_baseline_frontend_2x_users2.yaml`
- `scenario_2_baseline_frontend_2x_users3.yaml` (prepared; **not run**)

All other configs keep `scripts: [online_boutique_create.sh, online_boutique_create2.sh]`.

### Ramp times with probe launcher (scaled spawn)

| Scale | CART / RATE | Distributed swarm to full `-u` | create2 postcheckout (hardcoded `-r 3`) |
|---|---|---|---|
| 1.5× | 450 / 135 | ~3.3 s | ~10 s |
| 2× | 600 / 180 | ~3.3 s | ~13 s |
| 3× (not run) | 900 / 270 | ~3.3 s | ~20 s |

S1–S6 via shared `create.sh` still ramp cart at ~3 users/s (~100 s for S2).

## 3. Smoke

Exported `CART=300 RATE=90`, ran probe script only. Masters showed:

- postcheckout `-u 20 -r 90` (old formula: `-r 0`)
- getproduct `-u 100 -r 90` (old: `-r 1`)
- cart `-u 300 -r 90` (old: `-r 3`)

Shared `create.sh` still contained `$((CART / RATE))` after smoke.

## 4. Lab sequence

Worker e2-standard-16; master/load e2-standard-8. 300 s cool-off before each
`run_scenario.py`. Frontend `cpu_limit_fraction: 2.0` (2000 m). Baseline only.

| Order | Config | Folder | Result |
|---|---|---|---|
| 1 | users15 run2 | `baseline_frontend_2x_users15_sustained_overload_run2` | pulled |
| 2 | users2 run2 | `baseline_frontend_2x_users2_sustained_overload_run2` | pulled |
| 3 | users3 | — | **skipped** (λ gate) |

## 5. Readout vs 1.0× frontend-2× run1 (λ ≈ 590.7)

| Gate | 1.5× run2 (probe) | 2× run2 (probe) |
|---|---|---|
| Frontend quota | **2000** | **2000** |
| Frontend inbound λ | **529.3** | **490.0** — still not above 570–600; lower than 1.0× |
| Frontend Layer B max CPU | 993 m (ov=0) | 1027 m (ov=0) — under 1600 m |
| Catalog max CPU | 418 m (ov=0) | 400 m (ov=0) |
| Backend `overloaded=1` | none | none |
| Outbound Δ`retry` (frontend) | **0** | **+34** (rec 33 / checkout 1) |
| Locust total mean Fail/s | 118.5 | 287.7 |
| Locust mean Latency95 (ms) | 783 | 930 |
| Locust rows (total.csv) | 542 | 539 |

**λ-gate verdict:** negative after a *working* spawn. Extra Locust users still
do not become extra admitted frontend work under live TopFull + frontend-2×.
Stopped before 3× per plan gate. Uniform user scaling remains the wrong lever
for unconstrained S2 overload on this machine; next levers stay mix reweight /
TopFull-off / S3–S4 constrained backends.

**Do not reinterpret** the earlier 1.5× / 2× / 6× `*_run1` folders as measuring
offered-load scale — they were spawn-capped by `count/RATE`. Those folders and
`campaign_48/` / `august_38/` stay historical.

## 6. YAML slots after this session

- users15 / users2: bumped to **run3** (next free)
- users3: still **run1**, still points at probe script (unused)
- Shared S1–S6 configs unchanged (still `create.sh`)

## 7. Out of scope (unchanged)

- Patching shared `create.sh` / `create2.sh`
- Wiring `GETCART` / `POSTCART` as `-u`
- RetryGuard arms at these loads
- Reinterpreting campaign matrix rows
