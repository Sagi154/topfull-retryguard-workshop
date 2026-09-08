# TopFull throttle metrics — what exists, how to get it

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Inventory of TopFull’s **internal admission / throttle state**: live sources on `topfull-master`, what we already collect (and do not), and how to scrape a time series for future runs. Layer 1 Locust CSVs and the rest of the metric stack: [METRICS-GATHERED.md](METRICS-GATHERED.md). Why `num_agent.csv` is empty: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md).

Nothing in `campaign_48/` or `august_38/` records TopFull’s actual throttle state. `num_agent.csv` was supposed to; it is zeros. You **cannot reconstruct** those counters from the finished runs. Locust `RPS` is only a proxy (completed traffic after the proxy, not the cap the RL set).

The live signals sit on **`topfull-master` while a run is going**. Two are real and easy; extras exist only as prints.

---

## What we already have vs what is missing

| Signal | Where it lives today | Status |
|---|---|---|
| Completed `RPS` / Fail / Goodput per Locust API | Locust CSVs from `metric_collector.py` | Collected. Weak **proxy** for admitted load. |
| `num_agent.csv` | Copied into every run folder | **Empty** (almost all zeros). Do not revive; scrape the sources below instead. |
| Admission **threshold** (cap) per Locust API | `rate_config/<api>` and `:8090/thresholds` | Live on master during a run. **Not** written to results. |
| **Admitted** RPS per Locust API | `:8090/stats` | Live on master during a run. **Not** written to results. |
| Overloaded-service list / RL actions | stdout of tmux `toprl` (`deploy_rl.py`) | Printed, not a CSV. |

Until a collector exists and you **re-run**, you do not have TopFull’s internal throttle history. Existing 48 runs stay “`RPS` as proxy.”

---

## 1. Admission cap per Locust API (the actual throttle)

TopFull’s RL writes one file per API under `proxy_dir` (`global_config.json` → typically `…/src/proxy/rate_config/`):

```
rate_config/getproduct
rate_config/postcheckout
rate_config/getcart
rate_config/postcart
rate_config/emptycart
```

Each file is a single number: **max req/s the proxy is allowed to admit for that API right now**. `overload_detection.apply_threshold_proxy()` does `echo <threshold> > rate_config/<name>` and then signals the Go process to reload.

During a live run:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls -l /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/rate_config/; echo '---'; for f in /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/rate_config/*; do echo \"\$(basename \$f)=\$(cat \$f)\"; done"
```

---

## 2. Admitted RPS from the proxy itself

`overload_detection.current_rps()` already GETs:

```
http://<master>:8090/stats
```

Format is the same `name=value/` text as Locust. This is **how much the proxy let through** that second, per Locust API — not Locust’s completed `RPS`.

During a live run (proxy must be up):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "curl -sS http://127.0.0.1:8090/stats; echo; curl -sS http://127.0.0.1:8090/thresholds"
```

`/thresholds` is the HTTP twin of the `rate_config/` files (used in TopFull’s Train-Ticket recorder). `/stats` is admitted throughput.

---

## How the three RPS-like numbers relate

Together with Locust CSVs you already have:

| Signal | Source | Meaning |
|---|---|---|
| **threshold** | `rate_config/<api>` or `:8090/thresholds` | Cap the RL set (req/s) |
| **admitted_rps** | `:8090/stats` | What the proxy actually forwarded |
| **completed_rps / Fail / Goodput** | Locust CSVs (already collected) | What came back to the client |
| **throttle tightness** (derived) | `admitted / threshold` or `completed vs threshold` | How hard TopFull is clamping |

That last derived column is the missing “controller interaction” series.

Locust APIs here are the same five entry actions (`getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`) — not Kubernetes microservice names. See [METRICS-GATHERED.md](METRICS-GATHERED.md).

---

## 3. Overloaded-service list and RL actions (weaker)

`Detector.detect()` / `set_priority()` / `apply()` run inside `deploy_rl.py` every ~1 s. They print overloaded services and leftover actions to **stdout of tmux session `toprl`**. Nothing writes that to a CSV.

Live peek (messy, not a metric series):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "tmux capture-pane -t toprl -p"
```

---

## How to keep this for analysis (future runs only)

Same pattern as `resource_usage_collector.py` / `envoy_retry_collector.py`:

1. New script on master, poll every 1–5 s.
2. Read `rate_config/*` **and** `GET :8090/stats` (and `/thresholds` if you want a cross-check).
3. Write e.g. `topfull_throttle.csv`:

```
timestamp, api, threshold, admitted_rps
```

4. Wire it in `run_scenario.py` (tmux session, copy from repo, YAML `enabled: true`). `collect_results()` already copies everything under `src/logs/`.

This only helps **future** runs — it will not backfill `campaign_48/` or `august_38/`.
