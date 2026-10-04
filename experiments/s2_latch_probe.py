"""Helpers for the S2 checkout-latch probe series (runs 108-127).

CLI:
  python experiments/s2_latch_probe.py config <treatment> <slot>   # writes configs/scenario_2_latch_probe.yaml
  python experiments/s2_latch_probe.py prep <treatment>            # prints bash for: ssh topfull-master bash -s
  python experiments/s2_latch_probe.py gate <treatment> <slot>     # exit 0 = pass
  python experiments/s2_latch_probe.py score <slot> [--root newvms|campaign]
"""
import copy
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_both_off_canon as canon  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE_CONFIG = HERE / "configs" / "scenario_2_baseline_no_topfull.yaml"
OUT_CONFIG = HERE / "configs" / "scenario_2_latch_probe.yaml"
NEW_VMS = str(REPO / "experiments" / "results" / "new vms" /
              "baseline_no_topfull_sustained_overload_run%d")
CAMPAIGN = canon.ROOT

BASE_COUNTS = {"getproduct": 275, "postcheckout": 90, "getcart": 100,
               "postcart": 90, "emptycart": 5}
CHECKOUT_MC, RECS_MC = 800, 1150

# treatment -> overrides. Keys: spawn_rate, counts, checkout_cpu, recs_cpu,
# checkout_replicas, restart.
TREATMENTS = {
    "control": {},
    "spawn10": {"spawn_rate": 10},
    "restart": {"restart": True},
    "recs_users310": {"counts": {"getproduct": 310}},
    "recs_cpu1000": {"recs_cpu": 1000},
    "ck_cpu1000": {"checkout_cpu": 1000},
    "ck_rep2": {"checkout_replicas": 2},
    "pc120": {"counts": {"postcheckout": 120}},
    "ck_rep2_pc120": {"checkout_replicas": 2, "counts": {"postcheckout": 120}},
}


def _set_cpu(cfg, dep, mc):
    for c in cfg["scale_constraints"]:
        if c["deployment"] == dep and c["method"] == "cpu_limit":
            c["cpu_limit_millicores"] = mc
            return
    raise KeyError(f"no cpu_limit constraint for {dep}")


def build_config(base: dict, treatment: str, slot: int) -> dict:
    t = TREATMENTS[treatment]
    cfg = copy.deepcopy(base)
    cfg["run_number"] = slot
    cfg["log_folder"] = f"baseline_no_topfull_sustained_overload_run{slot}"
    cfg["description"] = (f"Both controllers off. Paper-C1. Latch probe, treatment "
                          f"{treatment}, run89 mix base.")
    cfg["locust"]["user_counts"] = {**BASE_COUNTS, **t.get("counts", {})}
    cfg["locust"]["spawn_rate"] = t.get("spawn_rate", 50)
    if "checkout_cpu" in t:
        _set_cpu(cfg, "checkoutservice", t["checkout_cpu"])
    if "recs_cpu" in t:
        _set_cpu(cfg, "recommendationservice", t["recs_cpu"])
    if "checkout_replicas" in t:
        cfg["scale_constraints"].append({
            "deployment": "checkoutservice", "namespace": "default",
            "method": "replicas", "replicas": t["checkout_replicas"]})
    if t.get("restart"):
        cfg["restart_before_hold"] = {
            "deployments": ["checkoutservice", "recommendationservice"],
            "settle_seconds": 60}
    return cfg


def expected_replicas(treatment: str) -> dict:
    out = {"frontend": 4}
    out["checkoutservice"] = TREATMENTS[treatment].get("checkout_replicas", 1)
    return out


_PREP = """set -e
patch_cpu() {
  kubectl patch deployment "$1" -n default -p \
    "{\\"spec\\":{\\"template\\":{\\"spec\\":{\\"containers\\":[{\\"name\\":\\"server\\",\\"resources\\":{\\"limits\\":{\\"cpu\\":\\"$2\\"},\\"requests\\":{\\"cpu\\":\\"$2\\"}}}]}}}}"
}
patch_cpu checkoutservice @CK@m
patch_cpu recommendationservice @RC@m
kubectl scale deployment/checkoutservice -n default --replicas=@REP@
kubectl rollout status deployment/checkoutservice -n default --timeout=240s
kubectl rollout status deployment/recommendationservice -n default --timeout=240s
echo "--- pods"
kubectl get pods -n default -o wide
echo "--- pending"
kubectl get pods -n default --field-selector=status.phase=Pending --no-headers
echo "--- end"
"""


def prep_script(treatment: str) -> str:
    t = TREATMENTS[treatment]
    s = (_PREP.replace("@CK@", str(t.get("checkout_cpu", CHECKOUT_MC)))
              .replace("@RC@", str(t.get("recs_cpu", RECS_MC)))
              .replace("@REP@", str(t.get("checkout_replicas", 1))))
    return s.replace("\r", "")


def is_blend(o: dict) -> bool:
    s = o["svc"]
    g = lambda svc, k: s.get(svc, {}).get(k, 0) or 0  # noqa: E731
    return (g("recommendationservice", "streak") >= 10 and g("recommendationservice", "ov") >= 10
            and g("checkoutservice", "streak") >= 10 and g("checkoutservice", "ov") >= 10
            and (g("emailservice", "ov") >= 10 or g("paymentservice", "ov") >= 10))


def classify(o: dict) -> str:
    s = o["svc"]
    ck = s.get("checkoutservice", {}).get("streak", 0) or 0
    rc = s.get("recommendationservice", {}).get("streak", 0) or 0
    ret = o["edges"].get(("frontend", "recommendationservice"), 0)
    if ck >= 400 and rc == 0:
        return "sticky"
    # 70_000 is under run 101's 76,303 frontend→recommendations retries
    # and above the 50,000 count that stays "other".
    if ret >= 70000:
        return "released"
    return "other"


def _ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timestamp()


def sojourn_window(root: str, n: int, lo: int = 90, hi: int = 150) -> dict:
    """Checkout inbound mean sojourn (ms) and share of ticks above 500 ms, lo..hi s
    after the first checkout row. Clock is the collector's, not Locust's."""
    path = os.path.join(root % n, "service_inbound.csv")
    rows = [r for r in csv.DictReader(open(path)) if r["service"] == "checkoutservice"]
    if len(rows) < 2:
        return {"mean_ms": None, "share_over_500": None, "ticks": 0}
    t0 = _ts(rows[0]["timestamp"])
    vals = []
    for a, b in zip(rows, rows[1:]):
        t = _ts(b["timestamp"]) - t0
        if not (lo <= t <= hi):
            continue
        dc = float(b["rq_time_count"]) - float(a["rq_time_count"])
        ds = float(b["rq_time_sum_ms"]) - float(a["rq_time_sum_ms"])
        if dc > 0:
            vals.append(ds / dc)
    if not vals:
        return {"mean_ms": None, "share_over_500": None, "ticks": 0}
    return {"mean_ms": round(sum(vals) / len(vals), 1),
            "share_over_500": round(sum(v > 500 for v in vals) / len(vals), 2),
            "ticks": len(vals)}


def gate(n: int, treatment: str, root: str = NEW_VMS):
    canon.ROOT = root
    d = root % n
    problems, notes = [], []
    need = ["service_inbound.csv", "service_edges.csv", "topfull_detect.csv",
            "resource_usage.csv", "total.csv", "service_capacity.json"]
    missing = [f for f in need if not os.path.exists(os.path.join(d, f))]
    if missing:
        return False, [f"missing {missing}"]
    rows = sum(1 for _ in open(os.path.join(d, "total.csv"))) - 1
    o = canon.score(n)
    q, s = o["q"], o["svc"]
    notes.append(f"rows {rows} span {round(q.get('span', 0))} gap2 {q.get('gap2_pct')}")
    if rows < 500:
        problems.append(f"total.csv rows {rows} < 500")
    if not (480 <= q.get("span", 0) <= 900):
        problems.append(f"mesh span {q.get('span')} outside 480-900")
    if q.get("gap2_pct", 100) > 10:
        problems.append(f"gap2_pct {q.get('gap2_pct')} > 10")
    exp = expected_replicas(treatment)
    for svc, v in s.items():
        if svc == "__master_node__" or "rmode" not in v:
            continue
        want = exp.get(svc, 1)
        if v["rmode"] != want:
            problems.append(f"{svc} replica mode {v['rmode']} != {want}")
        if v.get("rzero", 0) > 0 and svc in ("checkoutservice", "recommendationservice"):
            notes.append(f"WARN {svc} rzero {v['rzero']}")
    return not problems, problems + notes


def score_line(n: int, root: str) -> str:
    canon.ROOT = root
    o = canon.score(n)
    s = o["svc"]
    f = lambda svc, k: s.get(svc, {}).get(k)  # noqa: E731
    soj = sojourn_window(root, n)
    ret_r = o["edges"].get(("frontend", "recommendationservice"), 0)
    ret_c = o["edges"].get(("frontend", "checkoutservice"), 0)
    return (f"run{n} {classify(o)} blend={is_blend(o)} "
            f"ck streak/ov {f('checkoutservice','streak')}/{f('checkoutservice','ov')} "
            f"recs streak/ov {f('recommendationservice','streak')}/{f('recommendationservice','ov')} "
            f"email_ov {f('emailservice','ov')} pay_ov {f('paymentservice','ov')} "
            f"retries f>recs {int(ret_r)} f>ck {int(ret_c)} "
            f"ck_sojourn_90_150 {soj['mean_ms']}ms over500 {soj['share_over_500']}")


def main(argv):
    cmd = argv[1]
    if cmd == "config":
        base = yaml.safe_load(open(BASE_CONFIG, encoding="utf-8"))
        cfg = build_config(base, argv[2], int(argv[3]))
        OUT_CONFIG.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        print(f"wrote {OUT_CONFIG} for {argv[2]} run{argv[3]}")
        return 0
    if cmd == "prep":
        sys.stdout.buffer.write(prep_script(argv[2]).encode())
        return 0
    if cmd == "gate":
        ok, lines = gate(int(argv[3]), argv[2])
        print("\n".join(lines))
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    if cmd == "score":
        root = CAMPAIGN if "--root" in argv and argv[argv.index("--root") + 1] == "campaign" else NEW_VMS
        print(score_line(int(argv[2]), root))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
