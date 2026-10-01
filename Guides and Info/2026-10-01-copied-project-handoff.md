# Handoff: workshop VMs on yoavnm98's project

The three workshop machines were copied off `networks-workshop` onto Yoav's billing account and checked with two both-off holds (run85, then the Hybrid replay run86). Continue on the copy. Leave the originals stopped.

## Where things stand

Signed in on this PC as `yoavnm98@gmail.com`. `gcloud config` project is `project-76deda76-55f1-42d2-abb` (console name "My First Project", number `444439345310`). Billing account **My Billing Account** `01ACD5-87C15F-010D84` (ILS). Yoav confirmed the $300 welcome credit covers this project. Compute Engine is enabled. The three VMs are **TERMINATED**.

| VM | Type | Internal IP | Disk |
|---|---|---|---|
| `topfull-master` | e2-standard-8 | 10.128.0.3 | 32 GB pd-balanced |
| `topfull-worker-1` | e2-standard-16 | 10.128.0.4 | 32 GB pd-balanced |
| `topfull-load` | e2-standard-8 | 10.128.0.2 | 50 GB pd-balanced |

Zone `us-central1-a`. Disks were created from snapshots of the stopped `networks-workshop` disks, then those temporary snapshots were deleted. Each dest disk still records `sourceSnapshot` `topfull-*-copy`. Internal addresses `topfull-master-ip`, `topfull-worker-1-ip`, and `topfull-load-ip` are reserved on the default subnet. Firewall `topfull-allow-app` allows tcp `6443`, `8090`, `30440`, `10250`, `15010`, `15012`, `15014`, `15017`.

`networks-workshop` still has the original three VMs, also **TERMINATED**. Do not start them for new holds. Do not delete them.

SSH aliases stay `topfull-master`, `topfull-worker-1`, `topfull-load`. Linux user is `idozacharia`. Key is `C:\Users\Yoav\.ssh\id_ed25519`. Public IPs are ephemeral and have swapped between worker and load after a stop/start. After every start, rewrite the three `HostName` lines and run `ssh-keygen -R` on the old and new public IPs before the first SSH.

This PC's Python for the runner is `C:\Users\Yoav\AppData\Local\Programs\Python\Python312\python.exe` (PyYAML installed). `python` on `PATH` is the Windows Store stub and fails.

Regional `E2_CPUS` showed a limit of 24 before the copy, and `CPUS_ALL_REGIONS` is 32. The three machines are exactly 32 vCPUs and did start together. Do not add a fourth VM or a larger type without checking quota. A free-trial account cannot request a quota increase.

While all three run, cost is about $1 per hour of the welcome credit. Disks stay billed while stopped (about $11 per month for 114 GB). Stop them when the session ends unless Yoav asks to leave them up.

## What run85 was

Both-off replay of the run84 mix, 600 s, on the copy. Mix **325 / 80 / 100 / 90 / 5**, `spawn_rate` 50, TopFull RL off, RetryGuard off, paper CPU reconcile on. Folder:

`experiments/results/copy verification/baseline_no_topfull_sustained_overload_run85`

Write-up: [2026-10-01-s2-copy-verification-run85.md](2026-10-01-s2-copy-verification-run85.md).

The pipeline matches run84: Locust 569 rows, mesh span 686 s, gap2 0%, Layer A threshold only 0 or 10000, last value 10000. The scorecard does not. run84 held frontend at 4 replicas for every resource sample and is a lens-blend **miss**. run85 scaled frontend 1 → 3 (never 4) and is a **near-miss**: recommendations streak 426 and overloaded 472/635, checkout streak 22 and overloaded 133/635, payment overloaded 5. Frontend → recommendations retries 288,235 versus 149,129 on run84. getproduct goodput 25 req/s versus 142.

`service_capacity.json` limits also differ. run84 recorded checkout / catalog / cart / email at 800 / 800 / 800 / 120. run85 is the current paper table in `experiments/topfull_cpu_quotas.py`: 615 / 1535 / 1920 / 155. Frontend and recommendations are 1150 m on both.

Do not overwrite run85, run86, run68, run70, run84, or the earlier both-off folders.

## What run86 was

Both-off Hybrid replay of run68 / run70, 600 s, on the copy. Mix **270 / 200 / 280 / 10 / 10**, `spawn_rate` 50. Frontend HPA pinned at 4, checkout scaled to 2, catalog HPA max 1, Hybrid CPU table, `paper_cpu_reconcile: false`. Folder:

`experiments/results/copy verification/baseline_no_topfull_sustained_overload_run86`

Write-up: [2026-10-01-s2-copy-verification-run86.md](2026-10-01-s2-copy-verification-run86.md).

The pin held: frontend 4/134 resource samples, checkout 2/134, Hybrid limits in `service_capacity.json`. Layer A threshold is only 0 or 10000, last value 10000. Recommendations matches the pair on arrival (~710 req/s), sojourn (~473 ms), overloaded share (83% vs ~90%), and frontend→recommendations retries (270,387 vs 240k–248k). It does not match on streak (212 vs 16–17), checkout detector share (42.6% vs ~1%), or mesh poll spacing (gap2 65% vs 0%). Storefront total goodput was 122 req/s versus 156 and 171.

After the pull, paper CPU was restored, `frontend-hpa` set back to min 1 / max 4, catalog HPA max back to 2, and checkout scaled back to 1. Sidecar request stayed 100 m with no `proxyCPULimit`.

## Next slot

`experiments/configs/scenario_2_baseline_no_topfull.yaml` is unused **run87**. `scale_constraints` is empty. `paper_cpu_reconcile` is omitted, so the runner applies the current paper table. Locust counts in that file are leftovers from run86 (270/200/280/10/10) and have not been launched as run87. Change them before the next hold. `experiments/test_topfull_cpu_quotas.py` `TestBothOffYamlRestored` expects run87.

## How to start the copy

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a
gcloud compute instances list --format="table(name,status,networkInterfaces[0].networkIP,networkInterfaces[0].accessConfigs[0].natIP)"
```

Update `~/.ssh/config`, clear stale host keys, then:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=15 topfull-master "kubectl get nodes"
ssh -o BatchMode=yes -o ConnectTimeout=15 topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=15 topfull-load "hostname; whoami"
```

`whoami` must be `idozacharia`. Worker OS hostname is `topfull-worker1`. Wait until both nodes are Ready before `run_scenario.py`. Clear `/tmp/rg_*.sh` and `/tmp/envoy_retry_params.json` on master first.

Launch with the Python 3.12 path above, not `python`. Pull with `experiments/pull_results.py`. Stop the three VMs when finished.

## Read next

- Hybrid replay versus run68/run70: [2026-10-01-s2-copy-verification-run86.md](2026-10-01-s2-copy-verification-run86.md)
- Earlier copy check versus run84: [2026-10-01-s2-copy-verification-run85.md](2026-10-01-s2-copy-verification-run85.md)
- The pair run86 replayed: [2026-09-29-s2-final-candidate-abc-report.md](2026-09-29-s2-final-candidate-abc-report.md)
- (a)/(b)/(c): [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- SSH aliases: [CONNECT-VMS.md](CONNECT-VMS.md). That playbook, `.cursor/rules/topfull-ssh.mdc`, and [infra/vm-ips.env](../infra/vm-ips.env) already name `project-76deda76-55f1-42d2-abb`. Members: `yoavnm98@gmail.com` (Owner), `idozacharia@gmail.com` and `sagi151ps@gmail.com` (Editor).
