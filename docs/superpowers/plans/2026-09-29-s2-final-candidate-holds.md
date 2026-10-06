# S2 Final-Candidate Holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the 11 both-off S2 candidate holds from [2026-09-29-s2-final-candidate-holds.md](../../../Guides%20and%20Info/2026-09-29-s2-final-candidate-holds.md) (rounds A–D), then write one final (a)/(b)/(c) report that reads all of them the way [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md) does and picks the S2 table and mix.

**Architecture:** Each hold is a both-off S2 run driven by `experiments/run_scenario.py` with the one YAML `scenario_2_baseline_no_topfull.yaml`. Per-pod CPU limits live in that YAML (`method: cpu_limit`); replica counts are pinned with kubectl/HPA, never via `scale_constraints`. Holds are ordered by table (Checkout-3, Checkout-4, Paper, Hybrid) so the cluster is reshaped only three times. Scoring is `experiments/s2_both_off_abc.py`. Procedure mirrors [2026-09-27-s2-replica-cpu-holds.md](2026-09-27-s2-replica-cpu-holds.md) and steps 1–9 of [2026-09-27-s2-cpu-variant-handoff.md](../../../Guides%20and%20Info/2026-09-27-s2-cpu-variant-handoff.md).

**Tech Stack:** `run_scenario.py`, `pull_results.py`, `s2_both_off_abc.py`, kubectl over `ssh topfull-master`, `gcloud compute`.

## Global Constraints

- Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every hold: 600 s, `spawn_rate` 50, `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`, script `online_boutique_create_v2.sh`.
- `paper_cpu_reconcile: false` and `proxyCPULimit` absent during holds. Replica counts are never in `scale_constraints` (a `replicas` entry is scaled back to 1 after every hold). `redis-cart` container is `redis`; all others `server`. Frontend is 1150 m (paper), not listed.
- Cool-off 360 s after a table is Ready and before its first hold, and 360 s between holds. No cool-off after the last hold. Restore then stop.
- Deployment total (limit × replicas) ≤ 13,360 m. Sidecar request: Paper **90 m**; Checkout-3, Checkout-4, Hybrid **100 m**. If a pod is Pending `Insufficient cpu`, lower `sidecar.istio.io/proxyCPU` on all 11 Deployments only until it schedules and record the value.
- Slots: `baseline_no_topfull_sustained_overload_run60` … `run70` (table below). Runs 58 and 59 exist locally, so 60 is the first free slot. **Never overwrite** run6, run42, run43, run54 or any run ≤ 59.
- Gates per hold (fail → do not launch the next hold *on that table*; capture pod events; see Task 9): `service_capacity.json` millicores match the table; `resource_usage.csv` replica counts equal the pin on every sample (a leaf dropping Ready on the 1 s `grpc_health_probe` is an overload symptom, not a crash — record it, still keep the hold's data); all collector files present; `total.csv` rows ≥ 500; mesh span ≈ hold length (not ~70 min like run53).
- (a) high sample = `(Δ5xx + Δresets)/Δtotal > 0.20`, disable = streak ≥ 30, controlled services = 9 (no frontend / redis-cart). (b) detector `overloaded=1` on ≥ 50% of `topfull_detect.csv` rows; Layer A threshold stays 10000. (c) sum of positive Envoy `retry` increments per caller→target edge. Do not edit the abc-reading file.
- SSH aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Refresh `HostName` per [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) if needed. Before every launch: `ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"`. If a command fails with `\r`, reissue with an LF script.

## Slot map and run order

| Slot | Hold | Table | Sidecar | Mix |
|---|---|---|---|---|
| run60 | A2 | Checkout-3 | 100 m | 150/250/150/20/20 |
| run61 | B1 | Checkout-3 | 100 m | 200/250/200/50/50 |
| run62 | D3 | Checkout-3 | 100 m | 300/200/200/10/10 |
| run63 | A3 | Checkout-3, email 180 m, redis-cart 320 m | 100 m | 150/250/150/20/20 |
| run64 | B2 | Checkout-4 | 100 m | 150/250/150/20/20 |
| run65 | A1 | Paper | 90 m | 340/100/240/10/10 |
| run66 | D2 | Paper | 90 m | 300/200/200/10/10 |
| run67 | D1 | Hybrid | 100 m | 300/200/200/10/10 |
| run68 | C1 | Hybrid | 100 m | 270/200/280/10/10 |
| run69 | C2 | Hybrid | 100 m | 200/250/250/10/10 |
| run70 | C3 | Hybrid | 100 m | better of C1/C2 (Task 7) |

Tables (per-pod millicores × replicas). Checkout-3: frontend 1150×4, checkout 800×3, recommendations 800×3, catalog 600×1, cart 600×1, currency 650×1, shipping 400×1, ad 600×1, payment 200×1, email 200×1, redis-cart 300×1 (12,950 m). Checkout-4: same but checkout ×4, recommendations ×2. Hybrid: frontend 1150×4, checkout 800×2, recommendations **1150×1**, other rows as Checkout-3 (10,900 m). Paper: paper CPU, all backends 1 replica, frontend HPA 1–4 unpinned except pinned at 4 for the hold. Confirm the exact Checkout-3/4 numbers against [2026-09-26-s2-cpu-limits-for-spread.md](../../../Guides%20and%20Info/2026-09-26-s2-cpu-limits-for-spread.md) and write the Hybrid table into that file (Task 1) before use.

---

### Task 1: Preflight and table docs

**Files:**
- Modify: `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md` (add Hybrid table + A3 variant)
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Produces: YAML at run60 / A2 mix, `scale_constraints` filled with the Checkout-3 limits; confirmed-unused slots.

- [ ] **Step 1: Start VMs and refresh SSH**

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default"
```
Expected: 3 nodes/hosts reachable, pods Running 2/2. Update `HostName` in `~/.ssh/config` if SSH times out.

- [ ] **Step 2: Confirm slots run60–run70 are free on master and locally**

```powershell
ssh topfull-master "ls /home/idozacharia/experiments/results | grep -E 'baseline_no_topfull_sustained_overload_run(6[0-9]|70)$' || echo none"
Get-ChildItem experiments/results/campaign_48/S2_sustained_overload -Filter "baseline_no_topfull_sustained_overload_run6[0-9]","baseline_no_topfull_sustained_overload_run70"
```
Expected: `none` and no local folders beyond run60 (if run60+ exist, shift the slot map up and note it).

- [ ] **Step 3: Write the Hybrid table and A3 variant into the CPU-tables doc**, with deployment totals (10,900 m / 12,950 m).

- [ ] **Step 4: Edit the YAML** to `run_number: 60`, `log_folder: baseline_no_topfull_sustained_overload_run60`, `user_counts` 150/250/150/20/20, `paper_cpu_reconcile: false`, and `scale_constraints` = ten `cpu_limit` entries in the Checkout-3 table (checkout 800, recs 800, catalog 600, cart 600, currency 650, shipping 400, ad 600, payment 200, email 200, redis-cart 300 with `container: redis`).

- [ ] **Step 5: Commit**

```powershell
git add "Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "chore: S2 final-candidate holds preflight (run60 Checkout-3)"
```

### Task 2: Checkout-3 table, holds A2 / B1 / D3 (run60–run62)

**Files:** Modify `experiments/configs/scenario_2_baseline_no_topfull.yaml` (between holds: only `run_number`, `log_folder`, `description`, `locust.user_counts`).

- [ ] **Step 1: Pin the table.** With every backend at 1 replica, the YAML's `scale_constraints` patch the CPU at launch. Then pin: frontend HPA `min=max=4`; `kubectl scale deployment/checkoutservice deployment/recommendationservice --replicas=3`; sidecar annotation `sidecar.istio.io/proxyCPU=100m` on all 11 Deployments, `proxyCPULimit` unset.

```powershell
ssh topfull-master "kubectl patch hpa frontend -p '{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}'; kubectl scale deploy/checkoutservice deploy/recommendationservice --replicas=3; kubectl get pods -n default -o wide | grep -v Running"
```
Expected: no Pending; ready counts 4/3/3.

- [ ] **Step 2: Cool off 360 s** (use `AwaitShell`, never shell sleep).

- [ ] **Step 3: Launch run60 (A2)** and, about 2 min in, take the Round 0 snapshot (Task 10, Step 1).

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```
Expected: run completes ~11–12 min wall.

- [ ] **Step 4: Pull and gate.**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/s2_both_off_abc.py experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run60
```
Check the Global Constraints gates. Expected: table printed; note Layer A admitting rows = 0.

- [ ] **Step 5: Bump YAML to run61 / B1 (200/250/200/50/50), cool 360 s, launch, pull, gate. Repeat for run62 / D3 (300/200/200/10/10).**

- [ ] **Step 6: Commit** the three pulled folders (`git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run6{0,1,2}`), message `data: S2 Checkout-3 holds run60-62`.

### Task 3: A3, Checkout-3 with email 180 m / redis-cart 320 m (run63)

- [ ] **Step 1:** In the YAML set `emailservice` `cpu_limit_millicores: 180`, `redis-cart` 320 (total stays 12,950 m); `run_number: 63`, folder `..._run63`, counts 150/250/150/20/20, description names the trim. Replica pin unchanged.
- [ ] **Step 2:** Cool off 360 s, clear `/tmp` files, launch, pull, gate, score.
- [ ] **Step 3:** Commit `data: S2 A3 run63`.

### Task 4: Checkout-4, hold B2 (run64)

- [ ] **Step 1: Reshape.** YAML limits stay Checkout-3 values but email back to 200 and redis-cart 300. Scale: `kubectl scale deploy/checkoutservice --replicas=4`, `deploy/recommendationservice --replicas=2`. Frontend pin stays. Wait for ready/pending 0.
- [ ] **Step 2:** `run_number: 64`, counts 150/250/150/20/20. Cool off 360 s, launch, pull, gate, score. Replica gate failed on run43 (email `replica_count` 0): if it fails again, capture `kubectl describe pod`/events for the email pod and record whether it is a readiness-probe drop.
- [ ] **Step 3:** Commit `data: S2 Checkout-4 run64`.

### Task 5: Paper table, holds A1 / D2 (run65, run66)

- [ ] **Step 1: Restore to paper.** Scale checkout/recommendations to 1; set YAML `scale_constraints: []` with `paper_cpu_reconcile` omitted for a restore pass, or run `reconcile_paper_cpu_limits`, then verify with `kubectl get deploy -o custom-columns=...` that limits are paper. Frontend HPA `min=max=4`; sidecar request **90 m** (`proxyCPU=90m`, no limit).
- [ ] **Step 2:** For the holds keep `scale_constraints: []` and **omit** `paper_cpu_reconcile` (or set true) so the runner holds paper CPU. Run65: `run_number: 65`, 340/100/240/10/10. Cool off 360 s, launch, pull, gate, score. Then run66 / D2: 300/200/200/10/10.
- [ ] **Step 3:** Commit `data: S2 Paper holds run65-66`.

### Task 6: Hybrid table, hold D1 and C1 / C2 (run67–run69)

- [ ] **Step 1: Reshape to Hybrid.** Restore paper first, then YAML `scale_constraints` = Checkout-3 limits with `paper_cpu_reconcile: false`, plus `recommendationservice` `cpu_limit_millicores: 1150`. Scale: checkout 2, recommendations 1. Frontend pin 4, sidecar request 100 m. Confirm no Pending.
- [ ] **Step 2:** run67 / D1 300/200/200/10/10; run68 / C1 270/200/280/10/10; run69 / C2 200/250/250/10/10. Each: bump YAML, cool off 360 s, clear `/tmp`, launch, pull, gate, score.
- [ ] **Step 3:** Commit `data: S2 Hybrid holds run67-69`.

### Task 7: C3 replay (run70)

- [ ] **Step 1: Pick the mix** by score on run68 vs run69: prefer more controlled services with streak ≥ 30, then more with (b) ≥ 0.5, then larger (c) on those edges. If tied, prefer the one that keeps checkout **and** recommendations both clearing (independent pair). Record the choice and the reason in the report.
- [ ] **Step 2:** `run_number: 70`, chosen counts, cool off 360 s, launch, pull, gate, score.
- [ ] **Step 3:** Commit `data: S2 C3 run70`.

### Task 8: Restore the cluster and repo state

- [ ] **Step 1:** Scale all extra replicas to 1; frontend HPA min 1 / max 4; catalog HPA min 1 / max 2; run `reconcile_paper_cpu_limits`; `proxyCPU=100m`, no `proxyCPULimit`. Verify with `kubectl get deploy,hpa`.
- [ ] **Step 2:** YAML to next free slot **run71** with `scale_constraints: []` and no `paper_cpu_reconcile`. Update `experiments/test_topfull_cpu_quotas.py` `TestBothOffYamlRestored` (currently expects run57, stale) to run71.

```powershell
python -m pytest experiments/test_topfull_cpu_quotas.py -q
```
Expected: pass.

- [ ] **Step 3:** Commit `chore: restore S2 both-off YAML to run71`.

### Task 9: Failure handling (applies throughout)

- If a hold fails its gate: capture `kubectl get events -n default --sort-by=.lastTimestamp` and `kubectl describe pod` for the failing pod, keep the folder, do **not** relaunch on the same slot (bump to the next free slot and update the slot map). Skip the remaining holds on that table only if the cause is infrastructure (Pending pods, SSH death before Locust); a leaf readiness dip is recorded, not blocking.
- If a launch dies before Locust (`duplicate session: envoyretry`), kill the stale tmux session and relaunch the same slot.

### Task 10: Round 0 snapshot and optional E1/E2

- [ ] **Step 1: Snapshot, ~2 min into run60** (no extra cluster time): on `topfull-load` read each Locust stats port (8888–8930): `user_count` vs configured, `total_rps / user_count`; per-process CPU and idle CPU of the load VM; on master `kubectl top pod --containers` for frontend `istio-proxy`. Save to `Guides and Info/2026-09-29-s2-round0-ceiling-snapshot.md`.
- [ ] **Step 2 (only if the snapshot does not name the limiter):** short holds, 180 s each, 120 s cool-off, own `log_folder` names (`probe_ceiling_e1_*`, `probe_ceiling_e2_*`), not in the S2 slot range: E1 `emptycart` only at 200 / 400 / 600; E2 mix 200/250/200/200/200. Run them after Task 7, before Task 8. They do not gate anything.

### Task 11: Final (a)/(b)/(c) report

**Files:**
- Create: `Guides and Info/2026-09-29-s2-final-candidate-abc-report.md`
- Modify: `AGENTS.md` §4 (one status bullet), next-free slots line

**Interfaces:** Consumes the 11 pulled folders plus reference folders run6, run42, run43, run54.

- [ ] **Step 1: Score everything**

```powershell
$d = "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run"
python experiments/s2_both_off_abc.py ($d+"6") ($d+"42") ($d+"43") ($d+"54") ($d+"60") ($d+"61") ($d+"62") ($d+"63") ($d+"64") ($d+"65") ($d+"66") ($d+"67") ($d+"68") ($d+"69") ($d+"70") > $env:TEMP\s2_final_abc.md
```
Expected: 15 sections. Read the output before writing.

- [ ] **Step 2: Write the report**, applying the reading rules from the abc-reading file (do not restate the definitions). Sections, in order:
  1. Setup paragraph and a hold index (slot, round label, table, sidecar, mix, Locust rows, gate result).
  2. **(a)** per-service longest inbound streak for all 9 controlled services (+ frontend/redis-cart plain); **bold** = streak ≥ 30.
  3. **(b)** detector overloaded share per service; **bold** ≥ 0.5; confirm Layer A threshold = 10000 / admitting rows 0.
  4. **(c)** retry sum per caller→target edge, top edges per hold, and whether they sit on the (a)/(b)-hot services.
  5. Scorecard vs the pick rule: clears (a) on ≥ 2 controlled services, (b) on ≥ 2 services, (c) in the tens of thousands, **in ≥ 2 replays**; mark independent pair (checkout + recommendations) vs chain (checkout + payment + email).
  6. Answers to the design questions: A1 reproduces run 6? A2 reproduces run 42? A3 email streak ≥ 30? B1/B2 follow mix or table? Round C edge probe (C1 vs C2 vs replay)? Round D: which of Hybrid / Paper / Checkout-3 fits 300/200/200/10/10? Note replica-gate events per hold.
  7. Recommendation: the S2 table + mix, sidecar setting, and remaining risks. Separate measured facts from prediction.
  8. Round 0 result (limiter named or not) and the E1/E2 outcome if run.
  9. Related links.
  Group comparison columns by mix with a bold `**┃**` separator between mix groups.

- [ ] **Step 3: Add the AGENTS.md bullet** (holds run60–run70, headline result, recommendation, next free slot run71, VM state) and update the free-slot lines.

- [ ] **Step 4: Verify** every section above exists and every number in the report traces to `s2_both_off_abc.py` output or a listed CSV (spot-check three cells).

- [ ] **Step 5: Commit and stop VMs**

```powershell
git add "Guides and Info/2026-09-29-s2-final-candidate-abc-report.md" "Guides and Info/2026-09-29-s2-round0-ceiling-snapshot.md" AGENTS.md
git commit -m "docs: S2 final-candidate holds (a)/(b)/(c) report"
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
```
(Stop VMs only if the user has not asked to keep them running.)

---

## Self-review

- Coverage: rounds A (3), B (2), C (3), D (3) = 11 holds run60–run70; Round 0 in Task 10; the final abc report is Task 11.
- Cost: ~11 × 16 min ≈ 3 h, plus three reshapes and the optional E holds (~15 min).
- Open decisions at execution time: C3's mix (Task 7 rule), and whether a table's replica gate blocks its remaining holds (Task 9).
