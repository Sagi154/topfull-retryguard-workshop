# final_configs

Copies of the locked S1–S4 scenario YAMLs. The originals under `experiments/configs/` stay where they are. S5 and S6 are not in this folder.

New holds use these files and are pulled into `experiments/results/analysis_runs_results/` (rule from 2026-10-16; `final results/` is closed).

Regenerate with `python experiments/make_final_configs.py`. That script only writes this tree.

## Layout

| Folder | Scenario |
|---|---|
| `1/` | S1 Normal Operation. Mix 175 / 30 / 70 / 90 / 5. Paper-C1. |
| `2/` | S2 Sustained Overload. Mix 275 / 90 / 100 / 90 / 5. Paper-C1. |
| `3/` | S3 Targeted Bottleneck. S1 mix. `checkoutservice` 200m. |
| `4/4a_unconstrained/` | S4A. Mix 50 / 20 / 50 / 600 / 5. Plain Paper-C1. |
| `4/4a_constrained/` | S4A. Same mix. `productcatalogservice` 100m. |
| `4/4b/` | S4B. S1 mix. `emailservice` 50m. |

Each folder has five files. The name is `<prefix>_<variant>.yaml` (`s1_`, `s2_`, `s3_`, `4a_unconstrained_`, `4a_constrained_`, `4b_`).

| Variant | RetryGuard | TopFull | `final results/` variant | Mode folder |
|---|---|---|---|---|
| `rg_only_burst` | on, three burst keys present | off | `rg_only` | `burst` |
| `rg_only_normal` | on, three burst keys omitted | off | `rg_only` | `normal` |
| `tf_only` | off | on | `tf_only` | `normal` |
| `both_burst` | on, three burst keys present | on | `both` | `burst` |
| `both_normal` | on, three burst keys omitted | on | `both` | `normal` |

Burst mode is `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal mode omits those three keys. `tf_only` keeps them because it is a copy of the baseline YAML, but RetryGuard is off, so they are unused. Its mode folder is `normal`, as in the existing `tf_only` holds.

S3 and 4A constrained are at `run_number: 3` (`log_folder` `..._run3`). The other folders are `run_number: 1` and `log_folder: final_<prefix>_<variant>_run1`. Bump both on that file before a repeat. These slots are separate from the historical `scenario_*.yaml` counters.

## Where results go

`run_scenario.py` and `pull_results.py` read the config and send every run to `experiments/results/analysis_runs_results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. The `scp` line the runner prints at the end already has that path. `python experiments/pull_results.py <config>` pulls there. The `log_folder` name does not affect the destination. `campaign_48/` is never a target.

Scenario folder names: `S1_normal_operation`, `S2_sustained_overload`, `S3_targeted_bottleneck`, `S4A_topology_position`, `S4B_topology_position`.

S1 source YAMLs have `scale_constraints: []`. The copies in `1/` write the Paper-C1 table so the hold states the limits. The source files are unchanged.
