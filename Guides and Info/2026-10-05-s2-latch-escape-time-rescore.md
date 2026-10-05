# S2 latch escape-time rescore and frontend concurrency

Offline analysis of existing both-off holds under `experiments/results/new vms/`. No new runs. Script: [`experiments/s2_latch_escape.py`](../experiments/s2_latch_escape.py). Expected-outcome note written before this run: [2026-10-05-s2-latch-escape-what-we-expect.md](2026-10-05-s2-latch-escape-what-we-expect.md). Mechanism: [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md). Replay divergence: [2026-10-03-s2-same-mix-replays-differ.md](2026-10-03-s2-same-mix-replays-differ.md). v2 scorecard: [2026-10-04-s2-latch-probe-v2-results.md](2026-10-04-s2-latch-probe-v2-results.md).

Labels: **(m)** measured, **(i)** inference.

## Definitions

- **Clock.** Locust CSVs have no timestamps. Offsets are seconds after the first `service_inbound.csv` poll (mesh t0). Last 5 inbound polls per service are dropped, same trim as `s2_both_off_canon`.
- **Escape time.** First second where recommendationservice arrival stays **> 560 req/s for 5 consecutive usable 1 s ticks**. Scrape holes (`dt ≥ 1.5 s`) reset the streak (censored, not zero). Else **never** (right-censored at hold end).
- **Latch onset.** First usable tick with checkout sojourn ≥ 480 ms and arrival > 50, or else first sustained checkout arrival > 120 for 5 ticks. Checkout `rq_time_*` often updates only about every 5 s while `total` advances every 1 s, so a consecutive sojourn streak of length 5 almost never forms; the sparse sojourn hit is the primary signature.
- **Latch duration.** `escape_s − onset_s` when both exist.
- **Old label.** sticky / released / other from `s2_latch_probe.classify` (checkout streak ≥ 400 and recs streak 0 → sticky; else frontend→recommendations retries ≥ 70000 → released; else other).

## Short answer

1. **Escape time replaces sticky/released without changing who escaped (m).** On v2, every released hold escapes and every sticky hold is `never`. The three "other" holds (141, 143, 152) are `never` — the same latch class as sticky, cut only by a streak blip or scrape hole. What sticky/released hid is **when** the escape happened: five holds latched for 44–203 s before escaping; the rest of the released set escaped within about 4–22 s of onset.
2. **Frontend concurrency (Little's L) rises in the last ~30 s before escape, but its level does not separate escapes from non-escapes (m).** Pre-escape median L on escaped holds is **lower** than on never-escaped holds (279 vs 327). The proxy tracks frontend CPU only moderately (r ≈ 0.40). **(i)** A rise aligned on escape is consistent with the recommendations storm already starting, not with a concurrency threshold that forecasts the break. A direct queue gauge is still needed if the trigger question stays open.

## v2 primary table (runs 132–153, scored only)

Excluded: run136 and run138 (failed sampling gate). Replacements: run152, run153.

| run | treatment | old | escape_s | onset_s | duration_s | reconcile | peak_recs |
|---|---|---|---|---|---|---|---|
| 132 | control | released | 131 | 127 | 4 | agree | 856 |
| 133 | spawn10 | released | 94 | 90 | 4 | agree | 898 |
| 134 | control | released | 288 | 137 | 151 | agree | 869 |
| 135 | ck_cpu1000_pc120 | released | 291 | 129 | 162 | agree | 844 |
| 137 | ck_rep2_pc120 | released | 143 | 128 | 15 | agree | 861 |
| 139 | control | sticky | never | 134 | — | agree | 501 |
| 140 | ck_rep2_pc120_spawn10 | released | 116 | 94 | 22 | agree | 766 |
| 141 | ck_cpu1000_pc120_spawn10 | other | never | 96 | — | other_as_never | 537 |
| 142 | spawn10 | sticky | never | 98 | — | agree | 488 |
| 143 | control | other | never | 198 | — | other_as_never | 468 |
| 144 | recs_cpu1000_spawn10 | sticky | never | 102 | — | agree | 471 |
| 145 | ck_rep2_pc120_spawn10 | released | 103 | 99 | 4 | agree | 906 |
| 146 | ck_cpu1000_pc120 | released | 331 | 128 | 203 | agree | 852 |
| 147 | control | sticky | never | 137 | — | agree | 474 |
| 148 | recs_cpu1000 | sticky | never | 134 | — | agree | 461 |
| 149 | ck_cpu1000_pc120_spawn10 | sticky | never | 96 | — | agree | 436 |
| 150 | ck_rep2_pc120 | released | 139 | 128 | 11 | agree | 892 |
| 151 | control | released | 176 | 132 | 44 | agree | 856 |
| 152 | recs_cpu1000_spawn10 | other | never | 97 | — | other_as_never | 486 |
| 153 | recs_cpu1000 | released | 247 | 135 | 112 | agree | 907 |

Escaped **11 / 20**. Survival (fraction not yet escaped) at 120 / 300 / 600 s: **0.85 / 0.50 / 0.45**. Escape-time median among escapers: **143 s** (min 94, max 331).

### Late escapes vs early releases (m)

Holds with latch duration ≥ 40 s (latched, then escaped):

| run | treatment | onset | escape | duration |
|---|---|---|---|---|
| 134 | control | 137 | 288 | 151 |
| 135 | ck_cpu1000_pc120 | 129 | 291 | 162 |
| 146 | ck_cpu1000_pc120 | 128 | 331 | 203 |
| 151 | control | 132 | 176 | 44 |
| 153 | recs_cpu1000 | 135 | 247 | 112 |

These are the five late escapes called out in the checkout-latch guide. Early releases (duration ≤ 22 s) include the `ck_rep2*` arms and the first control (132). Sticky and other holds all show an onset and never cross 560.

### v2 controls only

| run | old | escape_s | duration_s | peak_recs |
|---|---|---|---|---|
| 132 | released | 131 | 4 | 856 |
| 134 | released | 288 | 151 | 869 |
| 139 | sticky | never | — | 501 |
| 143 | other | never | — | 468 |
| 147 | sticky | never | — | 474 |
| 151 | released | 176 | 44 | 856 |

Escaped **3 / 6**. Survival at 120 / 300 / 600 s: **1.00 / 0.50 / 0.50**. Reading the controls as escape times rather than sticky/released/other: half never escape; the three that do escape at 131, 176, and 288 s — a spread, not a single ramp-window coin flip.

### Sensitivity (m)

Every (rate ∈ {520, 560, 600}) × (persist ∈ {3, 5, 10}) combination yields the same **11 / 20** escaped set on v2. The 560 / 5 rule is not carrying the classification; the gap between sticky peaks (436–537) and released peaks (766–907) is wide.

## Extended sets (reported separately)

### First latch probe + ck_rep2 replays (v1: 108–131 minus 116)

Escaped **17 / 22**. Survival 120 / 300 / 600 s: **0.95 / 0.36 / 0.27**. Median escape among escapers: **131 s**. Sticky holds 124–126, 129, 131 are `never`. Run110 (old label other) escapes at **651 s** (`other_escaped`) — after a long latch, past a clean 600 s window on a long mesh series. Sensitivity again flat at 17/22 across all nine threshold settings.

### Paper-C1 same-mix holds 94–107

Runs 89 and 92 are not under `new vms/`. Escaped **5 / 14**. Survival: **1.00 / 0.79 / 0.64**. Late escapes: run99 (414 s, duration 283), run101 (500 s, duration 365). Sticky peaks stay ≤ 578 except run100 (peak 683) which still never sustains 5 s above 560. Sensitivity flat at 5/14.

## Frontend concurrency (Little's law)

Per-tick frontend concurrency `L = Δrq_time_sum_ms / 1000 / Δt` on usable 1 s polls with `Δrq_time_count > 0`. Frontend `rq_time_*` is also sparse (usable fraction ~0.38–0.46 on the two checked holds), so L is only defined on a subset of seconds. Gap2 on frontend was 0% on almost every v2 hold (run143 ≈ 0.2%).

### Proxy validation (m)

| run | class | usable_frac | r(L, frontend CPU) | r(L, P50) | n |
|---|---|---|---|---|---|
| 132 | escaped (early) | 0.38 | 0.44 | 0.45 | 264 |
| 139 | never (sticky) | 0.46 | 0.40 | 0.20 | 317 |

L moves with frontend CPU in the right direction. The correlation is moderate, not tight. Treat L as a noisy saturation proxy.

### Event-aligned escape window (m)

For all 11 v2 escapers, frontend L in the last 60 s before escape rises relative to a −60…−10 s baseline (20% rule). Lead time median **27 s** (min 8, max 30; several hit the 30 s lookback edge). At escape, frontend CPU is typically 1000–1700 m.

### Does L separate escapes from non-escapes? (m)

Matched wall-clock window 120–300 s, clipped to end 10 s before escape on escapers:

- Never-escaped (n=9): median of per-hold L medians = **326.7**
- Escaped pre-escape (n=8 with a usable window): median = **279.1**
- Escaped holds above the never-median: **3 / 8**

**(i)** The level of frontend concurrency before escape does **not** mark the holds that will break. Sticky holds can sit at similar or higher L while recommendations stays under 560 (peak 436–537). The aligned rise in the last ~30 s is better read as part of the escape itself (recommendations storm + frontend queueing) than as a prior trigger. This is outcome 2 from the expected-outcome note, with a soft lead-time signal that does not forecast.

## Spot checks

- **Early release (run132):** escape 131 s, onset 127 s, duration 4 s, peak recs 856. Old label released. Agrees.
- **Late escape (run134):** onset 137 s, escape 288 s, duration 151 s, peak 869. Matches the latch guide's "pinned then escaped" reading.
- **Never (run139):** onset 134 s, escape never, peak 501. Old label sticky. Agrees.

## How to reproduce

```powershell
python -m unittest experiments.test_s2_latch_escape
python experiments/s2_latch_escape.py score --set v2
python experiments/s2_latch_escape.py align --set v2
python experiments/s2_latch_escape.py score --set v1
python experiments/s2_latch_escape.py score --set same_mix
```

## Decision for follow-up

The escape-time lens is enough to retire sticky/released as the primary description of these holds. The Little's-law frontend proxy does **not** give a concurrency threshold that separates escapes from non-escapes. Adding `downstream_rq_active` (or a pending gauge) and running more base-mix holds remains optional confirmation work, not required to state the escape-time result.
