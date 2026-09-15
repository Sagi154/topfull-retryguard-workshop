"""
Compare e2-standard-8 vs e2-standard-16 runs for S1/S2 baseline/RG.
Extracts: frontend CPU, TopFull activation, Locust getcart, RetryGuard toggles.
"""
import pandas as pd
import numpy as np
import os, re

BASE = r"experiments/results/campaign_48"

RUNS = [
    ("S1 run21",      "e2-std-8",           "S1_normal_op/baseline_topfull_no_retryguard_normal_op_run21"),
    ("S1 run22",      "e2-std-16",          "S1_normal_op/baseline_topfull_no_retryguard_normal_op_run22"),
    ("S2-base run17", "e2-std-8",           "S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run17"),
    ("S2-base run20", "e2-std-8 (trunc.)",  "S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run20"),
    ("S2-base run21", "e2-std-16",          "S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run21"),
    ("S2-RG run9",    "e2-std-8",           "S2_sustained_overload/run_topfull_retryguard_sustained_overload_run9"),
    ("S2-RG run10",   "e2-std-16",          "S2_sustained_overload/run_topfull_retryguard_sustained_overload_run10"),
]

SEP = "-" * 100

def rp(name, path, *parts):
    return os.path.join(BASE, path, *parts)

def safe_csv(fp):
    if not os.path.exists(fp):
        return None
    try:
        df = pd.read_csv(fp)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"  [WARN] could not read {fp}: {e}")
        return None


# ─── 1. Frontend CPU ─────────────────────────────────────────────────────────
print("\n" + SEP)
print("TABLE 1 — Frontend CPU (resource_usage.csv, service='frontend')")
print(SEP)
hdr = f"{'Run':<18} {'VM size':<22} {'max CPU (m)':>12} {'p95 CPU (m)':>12} {'rows':>6} {'Exceeds 800m?':>14}"
print(hdr)
print("-" * len(hdr))
for name, vm, path in RUNS:
    df = safe_csv(rp(name, path, "resource_usage.csv"))
    if df is None:
        print(f"{name:<18} {vm:<22} {'N/A':>12} {'N/A':>12} {'N/A':>6} {'N/A':>14}")
        continue
    fe = df[df["service"].str.strip() == "frontend"]
    if fe.empty:
        print(f"{name:<18} {vm:<22} {'no rows':>12} {'no rows':>12} {'0':>6} {'N/A':>14}")
        continue
    mx  = fe["cpu_millicores"].max()
    p95 = fe["cpu_millicores"].quantile(0.95)
    n   = len(fe)
    exc = "YES !" if mx > 800 else "no"
    print(f"{name:<18} {vm:<22} {mx:>12.1f} {p95:>12.1f} {n:>6} {exc:>14}")


# ─── 2. TopFull activation (num_agent + topfull_throttle) ────────────────────
print("\n" + SEP)
print("TABLE 2 — TopFull activation (num_agent.csv + topfull_throttle.csv)")
print(SEP)
hdr2 = f"{'Run':<18} {'VM size':<22} {'min thresh':>10} {'max agents':>10} {'non-zero':>9} {'Active?':>10}"
print(hdr2)
print("-" * len(hdr2))
for name, vm, path in RUNS:
    # num_agent.csv
    df_na = safe_csv(rp(name, path, "num_agent.csv"))
    if df_na is not None and not df_na.empty:
        col = df_na.columns[0]
        agents_max  = df_na[col].max()
        agents_nz   = (df_na[col] > 0).sum()
    else:
        agents_max = agents_nz = "N/A"

    # topfull_throttle.csv
    df_th = safe_csv(rp(name, path, "topfull_throttle.csv"))
    if df_th is not None and not df_th.empty:
        # look for threshold column
        thresh_col = next((c for c in df_th.columns if "threshold" in c.lower()), None)
        if thresh_col:
            min_thresh = df_th[thresh_col].min()
        else:
            min_thresh = "no col"
    else:
        min_thresh = "N/A"

    active = "YES !" if (isinstance(agents_nz, (int,float,np.integer)) and agents_nz > 0) else "no"
    thresh_str = f"{min_thresh:.0f}" if isinstance(min_thresh, (int,float,np.integer,np.floating)) else str(min_thresh)
    anz_str = f"{agents_nz}" if isinstance(agents_nz, (int,float,np.integer)) else str(agents_nz)
    amx_str = f"{agents_max:.0f}" if isinstance(agents_max, (int,float,np.integer,np.floating)) else str(agents_max)
    print(f"{name:<18} {vm:<22} {thresh_str:>10} {amx_str:>10} {anz_str:>9} {active:>10}")


# ─── 3. Locust getcart outcomes ───────────────────────────────────────────────
print("\n" + SEP)
print("TABLE 3 — Locust getcart (getcart.csv, 1-s rows)")
print(SEP)
hdr3 = f"{'Run':<18} {'VM size':<22} {'rows':>6} {'mean RPS':>9} {'p95 lat (ms)':>13} {'fail/s':>8} {'fail%':>7}"
print(hdr3)
print("-" * len(hdr3))
for name, vm, path in RUNS:
    df = safe_csv(rp(name, path, "getcart.csv"))
    if df is None or df.empty:
        print(f"{name:<18} {vm:<22} {'N/A':>6} {'N/A':>9} {'N/A':>13} {'N/A':>8} {'N/A':>7}")
        continue
    # columns: timestamp, requests, failures, median_response_time, avg_response_time, min_response_time, max_response_time, ...
    # p95 usually stored directly or we look for percentile_95
    cols = {c.lower(): c for c in df.columns}
    rows = len(df)
    rps_col = cols.get("requests", cols.get("user_count", None))
    fail_col = cols.get("failures", None)
    p95_col = next((cols[c] for c in cols if "95" in c), None)
    p95_lat = "N/A"
    mean_rps = "N/A"
    fail_rate = "N/A"
    fail_s = "N/A"

    if rps_col:
        mean_rps = f"{df[rps_col].mean():.1f}"
    if p95_col:
        p95_lat = f"{df[p95_col].mean():.0f}"
    if fail_col and rps_col:
        total_req = df[rps_col].sum()
        total_fail = df[fail_col].sum()
        fail_s = f"{df[fail_col].mean():.2f}"
        fail_rate = f"{100*total_fail/total_req:.1f}%" if total_req > 0 else "N/A"

    print(f"{name:<18} {vm:<22} {rows:>6} {mean_rps:>9} {p95_lat:>13} {fail_s:>8} {fail_rate:>7}")


# ─── 4. RetryGuard toggles (RG runs only) ────────────────────────────────────
print("\n" + SEP)
print("TABLE 4 — RetryGuard toggles (retryguard.log, RG runs only)")
print(SEP)
hdr4 = f"{'Run':<18} {'VM size':<22} {'ON->OFF patches':>16} {'OFF->ON patches':>16} {'log lines':>10}"
print(hdr4)
print("-" * len(hdr4))
for name, vm, path in RUNS:
    if "RG" not in name and "retryguard" not in path.lower():
        continue
    fp = rp(name, path, "retryguard.log")
    if not os.path.exists(fp):
        print(f"{name:<18} {vm:<22} {'N/A':>16} {'N/A':>16} {'N/A':>10}")
        continue
    with open(fp, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    on_off = sum(1 for l in lines if "ON->OFF" in l or ("DISABLE" in l and "patch" in l.lower()))
    off_on = sum(1 for l in lines if "OFF->ON" in l or ("ENABLE" in l and "patch" in l.lower()))
    # also look for PATCH lines
    patches_disable = sum(1 for l in lines if "PATCH" in l and ("attempts: 0" in l or "retries: {}" in l or "attempts=0" in l or "disabled" in l.lower()))
    patches_enable  = sum(1 for l in lines if "PATCH" in l and ("attempts: 3" in l or "attempts=3" in l or "enabled" in l.lower()))
    print(f"{name:<18} {vm:<22} {on_off:>16} {off_on:>16} {len(lines):>10}")
    print(f"  (PATCH disable={patches_disable} enable={patches_enable})")

# ─── 5. Sample retryguard.log lines ─────────────────────────────────────────
print("\n" + SEP)
print("DETAIL — RetryGuard sample log lines (first 5 PATCH/toggle events)")
print(SEP)
for name, vm, path in RUNS:
    if "RG" not in name:
        continue
    fp = rp(name, path, "retryguard.log")
    if not os.path.exists(fp):
        continue
    print(f"\n--- {name} ({vm}) ---")
    with open(fp, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    shown = 0
    for l in lines:
        if any(kw in l for kw in ["PATCH", "ON->OFF", "OFF->ON", "DISABLE", "ENABLE", "toggle"]):
            print("  " + l.rstrip())
            shown += 1
            if shown >= 10:
                break
    if shown == 0:
        print("  (no PATCH/toggle lines found)")
        # show last 5 lines as sample
        print("  Last 5 log lines:")
        for l in lines[-5:]:
            print("  " + l.rstrip())

# ─── 6. topfull_throttle detail ──────────────────────────────────────────────
print("\n" + SEP)
print("DETAIL — TopFull throttle min/max/percentile per service")
print(SEP)
for name, vm, path in RUNS:
    fp = rp(name, path, "topfull_throttle.csv")
    df = safe_csv(fp)
    if df is None or df.empty:
        print(f"{name}: N/A")
        continue
    thresh_col = next((c for c in df.columns if "threshold" in c.lower()), None)
    svc_col = next((c for c in df.columns if "service" in c.lower()), None)
    if not thresh_col:
        print(f"{name}: no threshold column, cols={list(df.columns)}")
        continue
    print(f"\n{name} ({vm}) — threshold column: '{thresh_col}', rows: {len(df)}")
    if svc_col:
        for svc, grp in df.groupby(svc_col):
            mn = grp[thresh_col].min()
            mx = grp[thresh_col].max()
            below = (grp[thresh_col] < 10000).sum()
            print(f"  {svc:<30} min={mn:>8.0f}  max={mx:>8.0f}  rows_below_10000={below}")
    else:
        mn = df[thresh_col].min()
        mx = df[thresh_col].max()
        below = (df[thresh_col] < 10000).sum()
        print(f"  all services: min={mn:.0f}  max={mx:.0f}  rows_below_10000={below}")

print("\n" + SEP)
print("Done.")
