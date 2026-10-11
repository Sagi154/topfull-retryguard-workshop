---
name: rho-estimate-report
description: >-
  Retired. Do not generate rho_estimate_report.md. Use when someone asks
  for a rho report, lambda/W/mu_sat in the run folder, or the old
  RetryGuard toggle summary from rho_estimate_report.py. Score the hold
  with experiments/analysis_score.py and write the guide from Guides and
  Info/ANALYSIS-TEMPLATE.md.
---

# Rho report is retired

Score the run with:

```powershell
python experiments/analysis_score.py <run_dir>
```

Write the guide from [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md). Arrival rate, sojourn, the share of requests above 500 ms, edge rpr, climb streaks, and toggles are in that output.

`experiments/rho_estimate_report.py` stays in the tree so an old `rho_estimate_report.md` can be regenerated. `pull_results.py` does not call it.
