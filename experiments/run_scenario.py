#!/usr/bin/env python3
from __future__ import annotations

"""
run_scenario.py - Experiment runner for TopFull + RetryGuard scenarios.

Reads a scenario YAML config and orchestrates the full experiment:
  1. Pre-flight cluster health check
  2. Apply topology constraints (kubectl scale / cpu_limit)
  3. Start master stack (proxy -> deploy_rl -> metric_collector)
  4. Deploy this repo's RetryGuard / Envoy / resource collectors onto master, then start them
  5. Start Locust on the load-gen VM
  6. Wait for the configured duration
  7. Stop everything cleanly
  8. Copy logs to the results folder
  9. Restore topology to original state

Usage (from repo root, on Windows):
    python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml

Requirements:
    pip install pyyaml
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import yaml
from pathlib import Path
from datetime import datetime

import topfull_cpu_quotas

# --------------------------------------------------------------------------- #
#  SSH / SCP helpers
# --------------------------------------------------------------------------- #

def ssh(host: str, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a single command on a remote host via SSH."""
    result = subprocess.run(
        ["ssh",
         "-o", "BatchMode=yes",
         "-o", "ConnectTimeout=10",
         "-o", "ControlMaster=no",
         host, cmd],
        capture_output=True, text=True
    )
    if check and result.returncode not in (0,):
        print(f"\n[ERROR] ssh {host}: rc={result.returncode}")
        print(f"  cmd   : {cmd}")
        if result.stderr.strip():
            print(f"  stderr: {result.stderr.strip()}")
        sys.exit(1)
    return result


def scp_to(local_path: str, host: str, remote_path: str):
    """Copy a local file to a remote host."""
    subprocess.run(
        ["scp",
         "-o", "BatchMode=yes",
         "-o", "ControlMaster=no",
         local_path, f"{host}:{remote_path}"],
        check=True
    )


def write_remote_script(host: str, remote_path: str, content: str):
    """
    Write a bash script to a remote host with guaranteed LF line endings.
    Uses a local temp file + SCP to avoid shell quoting and CRLF issues.
    """
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".sh", delete=False) as f:
        # Always write with LF regardless of OS
        f.write(content.replace("\r\n", "\n").encode("utf-8"))
        tmp = f.name
    try:
        scp_to(tmp, host, remote_path)
        ssh(host, f"chmod +x {remote_path}")
    finally:
        os.unlink(tmp)


def write_remote_json(host: str, remote_path: str, data: dict):
    """Write a JSON file to a remote host."""
    content = json.dumps(data, indent=2)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                     newline="\n") as f:
        f.write(content)
        tmp = f.name
    try:
        scp_to(tmp, host, remote_path)
    finally:
        os.unlink(tmp)


EXPERIMENTS_DIR = Path(__file__).resolve().parent


def deploy_repo_script(host: str, filename: str, remote_path: str) -> None:
    """
    Copy a Python file from this repo's experiments/ directory to master.

    The runner used to upload only params JSON and assume the .py already
    lived at infra.*_script. That silently ran a stale or missing master
    copy. Staging via /tmp then cp/sudo cp handles: /tmp sticky-bit leftovers,
    and dest files owned by another user (directory is o+w, the file may not be).
    """
    local = EXPERIMENTS_DIR / filename
    if not local.is_file():
        print(f"[ERROR] Local script missing: {local}")
        sys.exit(1)

    tmp = f"/tmp/rg_deploy_{filename}"
    ssh(host, f"sudo rm -f {tmp}", check=False)
    scp_to(str(local), host, tmp)

    r = ssh(host, f"cp {tmp} {remote_path} && chmod a+r {remote_path}", check=False)
    if r.returncode != 0:
        r = ssh(
            host,
            f"sudo cp {tmp} {remote_path} && sudo chmod a+r {remote_path}",
            check=False,
        )
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip()
        print(f"[ERROR] Could not deploy {filename} to {host}:{remote_path}")
        if err:
            print(f"  {err}")
        print("  Need write access to the dest path (or passwordless sudo).")
        sys.exit(1)
    step(f"Deployed {filename} -> {remote_path}")


# --------------------------------------------------------------------------- #
#  Load-phase scheduling (pure logic, no I/O — see test_run_scenario.py)
# --------------------------------------------------------------------------- #

class ConfigError(Exception):
    """Raised for malformed scenario YAML that the runner cannot safely execute."""


def resolve_locust_phases(cfg: dict) -> list[dict]:
    """
    Normalize the locust load profile into an ordered list of phases.

    Each returned phase is a dict with keys: at_seconds (int), user_counts
    (dict), spawn_rate (int or None). Phase 0 always starts at at_seconds=0.

    Backward compatible: a config with no `locust.phases` key produces a
    single phase from the legacy `locust.user_counts` / `locust.spawn_rate`
    keys, at_seconds=0 — this must behave identically to the pre-phases
    runner for all 38 existing matrix configs.
    """
    lc = cfg.get("locust", {})
    explicit_phases = lc.get("phases")
    legacy_user_counts = lc.get("user_counts")

    if explicit_phases and legacy_user_counts:
        raise ConfigError(
            "locust.phases and locust.user_counts are mutually exclusive - "
            "put the initial load into phases[0].user_counts instead of "
            "top-level locust.user_counts."
        )

    if not explicit_phases:
        return [{
            "at_seconds": 0,
            "user_counts": lc.get("user_counts", {}),
            "spawn_rate": lc.get("spawn_rate"),
        }]

    phases = []
    for i, p in enumerate(explicit_phases):
        if "at_seconds" not in p:
            raise ConfigError(f"locust.phases[{i}] is missing required key 'at_seconds'")
        phases.append({
            "at_seconds": int(p["at_seconds"]),
            "user_counts": p.get("user_counts", {}),
            "spawn_rate": p.get("spawn_rate", lc.get("spawn_rate")),
        })

    phases.sort(key=lambda p: p["at_seconds"])

    if phases[0]["at_seconds"] != 0:
        raise ConfigError(
            f"locust.phases[0].at_seconds must be 0 (got {phases[0]['at_seconds']})"
        )
    for i in range(1, len(phases)):
        if phases[i]["at_seconds"] <= phases[i - 1]["at_seconds"]:
            raise ConfigError(
                "locust.phases must have strictly increasing at_seconds "
                f"(phase {i - 1} at {phases[i - 1]['at_seconds']}s, "
                f"phase {i} at {phases[i]['at_seconds']}s)"
            )

    duration = cfg.get("duration_seconds")
    if duration is not None:
        for i, p in enumerate(phases):
            if p["at_seconds"] >= duration:
                raise ConfigError(
                    f"locust.phases[{i}].at_seconds ({p['at_seconds']}s) must be "
                    f"< duration_seconds ({duration}s)"
                )

    return phases


def due_phases(elapsed: int, fired: set, phases: list[dict]) -> list[int]:
    """
    Return indices (into `phases`) of phases whose at_seconds has been
    reached but that have not yet fired, in ascending order.

    `fired` is the set of phase indices already switched to; index 0
    (the initial launch) must be pre-marked fired by the caller.
    """
    return sorted(
        i for i, p in enumerate(phases)
        if i not in fired and p["at_seconds"] <= elapsed
    )


# --------------------------------------------------------------------------- #
#  Logging helpers
# --------------------------------------------------------------------------- #

def banner(msg: str):
    print(f"\n{'-'*60}")
    print(f"  {msg}")
    print(f"{'-'*60}")


def step(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")


def wait_with_progress(seconds: int, label: str = ""):
    msg = f"  Waiting {seconds}s{f': {label}' if label else ''}"
    print(msg, end="", flush=True)
    for _ in range(seconds):
        time.sleep(1)
        print(".", end="", flush=True)
    print()


# --------------------------------------------------------------------------- #
#  Pre-flight
# --------------------------------------------------------------------------- #

def preflight(cfg: dict):
    banner("Pre-flight checks")
    master = cfg["infra"]["master_ssh_host"]

    step("Testing SSH to master...")
    r = ssh(master, "echo ok")
    if "ok" not in r.stdout:
        print("[ERROR] Master not reachable. Are VMs running?")
        sys.exit(1)

    step("Checking cluster nodes...")
    r = ssh(master, "kubectl get nodes --no-headers 2>/dev/null")
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    if not lines:
        print("[ERROR] No nodes returned - is kubectl configured?")
        sys.exit(1)
    not_ready = [l for l in lines if "NotReady" in l]
    if not_ready:
        print(f"[ERROR] Nodes not Ready:\n" + "\n".join(not_ready))
        sys.exit(1)
    step(f"Nodes: {len(lines)} Ready [OK]")

    step("Checking Online Boutique pods...")
    r = ssh(master, "kubectl get pods --no-headers 2>/dev/null | grep -v Running || true")
    non_running = [l for l in r.stdout.strip().splitlines() if l.strip() and "NAME" not in l]
    if non_running:
        print(f"  [WARN] Some pods not Running:")
        for l in non_running:
            print(f"    {l}")
    else:
        step("All pods Running [OK]")

    step("Testing SSH to loadgen...")
    loadgen = cfg["infra"]["loadgen_ssh_host"]
    r = ssh(loadgen, "echo ok")
    if "ok" not in r.stdout:
        print("[ERROR] Loadgen not reachable.")
        sys.exit(1)
    step("Loadgen reachable [OK]")


# --------------------------------------------------------------------------- #
#  Log management
# --------------------------------------------------------------------------- #

def clear_logs(cfg: dict):
    banner("Clearing previous logs")
    master = cfg["infra"]["master_ssh_host"]
    logs_path = cfg["infra"]["topfull_src_path"] + "/logs"
    ssh(master, f"mkdir -p {logs_path} && rm -f {logs_path}/*.csv {logs_path}/*.log 2>/dev/null; true",
        check=False)
    step(f"Cleared: {logs_path}")


# --------------------------------------------------------------------------- #
#  Topology constraints
# --------------------------------------------------------------------------- #

def parse_cpu_to_millicores(cpu_str):
    """Convert a Kubernetes CPU quantity ('100m', '1', '0.5') to millicores."""
    if not cpu_str:
        return None
    s = str(cpu_str).strip()
    if not s:
        return None
    if s.endswith("m"):
        return int(s[:-1])
    return int(float(s) * 1000)


def capture_service_capacity(cfg: dict, services: list) -> dict:
    """
    Snapshot each service's *original* CPU limit/request and declared
    replica count, before any scale_constraints are applied.

    Returns {service: {cpu_limit_millicores, cpu_request_millicores,
    replica_count}}. Missing/unparseable CPU values are None. Services
    with no matching Deployment (or on any kubectl/JSON failure) are
    simply omitted.
    """
    master = cfg["infra"]["master_ssh_host"]
    r = ssh(master, "kubectl get deploy -n default -o json", check=False)
    try:
        data = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        data = {}

    capacity = {}
    for item in data.get("items", []):
        name = (item.get("metadata") or {}).get("name")
        if name not in services:
            continue
        spec = item.get("spec") or {}
        containers = ((spec.get("template") or {}).get("spec") or {}).get("containers", [])
        resources = containers[0].get("resources", {}) if containers else {}
        limits = resources.get("limits", {}) or {}
        requests = resources.get("requests", {}) or {}
        capacity[name] = {
            "cpu_limit_millicores": parse_cpu_to_millicores(limits.get("cpu")),
            "cpu_request_millicores": parse_cpu_to_millicores(requests.get("cpu")),
            "replica_count": int(spec.get("replicas", 1)),
        }
    return capacity


def apply_constraints(cfg: dict) -> list:
    """
    Apply kubectl scale or CPU limit constraints.
    Returns a list of restore records so the caller can undo them later.
    """
    constraints = cfg.get("scale_constraints", [])
    if not constraints:
        return []

    banner("Applying topology constraints")
    master = cfg["infra"]["master_ssh_host"]
    restore_records = []

    for c in constraints:
        dep = c["deployment"]
        ns = c.get("namespace", "default")
        method = c.get("method", "replicas")

        if method == "replicas":
            # Detect current replica count so we can restore it
            r = ssh(master,
                    f"kubectl get deployment {dep} -n {ns} "
                    f"-o jsonpath='{{.spec.replicas}}' 2>/dev/null")
            original_replicas = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 1
            target = c["replicas"]
            step(f"Scaling {dep} ({ns}): {original_replicas} -> {target} replicas")
            ssh(master, f"kubectl scale deployment {dep} --replicas={target} -n {ns}")
            restore_records.append({
                "method": "replicas",
                "deployment": dep,
                "namespace": ns,
                "original_replicas": original_replicas,
            })

        elif method == "cpu_limit":
            frac = float(c["cpu_limit_fraction"])
            cpu_limit = topfull_cpu_quotas.kubectl_cpu_quantity(
                topfull_cpu_quotas.millicores_from_fraction(
                    topfull_cpu_quotas.paper_limit_for(dep), frac
                )
            )
            container = c.get("container", "server")
            # Capture full original resources so restore is exact (requests must
            # also drop: K8s requires request <= limit, and Boutique defaults
            # request 200m–500m which exceeds a 100m limit).
            r = ssh(master,
                    f"kubectl get deployment {dep} -n {ns} "
                    f"-o jsonpath='{{.spec.template.spec.containers[0].resources}}'")
            original_resources = r.stdout.strip() or "{}"
            step(
                f"Applying CPU limit {cpu_limit} "
                f"(fraction={frac}) to {dep}/{container} ({ns})"
            )
            patch = json.dumps({
                "spec": {"template": {"spec": {"containers": [
                    {"name": container, "resources": {
                        "limits": {"cpu": cpu_limit},
                        "requests": {"cpu": cpu_limit},
                    }}
                ]}}}
            })
            ssh(master, f"kubectl patch deployment {dep} -n {ns} -p '{patch}'")
            # CPU restore is paper-reconcile (not the pre-patch blob); keep
            # the record only for audit. restore_constraints skips cpu_limit.
            restore_records.append({
                "method": "cpu_limit",
                "deployment": dep,
                "namespace": ns,
                "container": container,
                "original_resources": original_resources,
            })

        else:
            print(f"[WARN] Unknown constraint method '{method}' - skipping {dep}")

    wait_with_progress(20, "pods stabilising after constraint")
    return restore_records


def reconcile_paper_cpu_limits(cfg: dict, wait: bool = True) -> None:
    """Patch Boutique Deployments to the paper CPU limit/request table."""
    banner("Reconciling CPU limits to paper quotas")
    master = cfg["infra"]["master_ssh_host"]
    for dep in topfull_cpu_quotas.RECONCILE_SERVICES:
        lim = topfull_cpu_quotas.kubectl_cpu_quantity(
            topfull_cpu_quotas.paper_limit_for(dep)
        )
        req = topfull_cpu_quotas.kubectl_cpu_quantity(
            topfull_cpu_quotas.paper_request_for(dep)
        )
        step(f"{dep}: limits.cpu={lim} requests.cpu={req}")
        patch = json.dumps({
            "spec": {"template": {"spec": {"containers": [
                {"name": "server", "resources": {
                    "limits": {"cpu": lim},
                    "requests": {"cpu": req},
                }}
            ]}}}
        })
        ssh(master, f"kubectl patch deployment {dep} -n default -p '{patch}'",
            check=False)
    if wait:
        wait_with_progress(20, "pods stabilising after paper CPU reconcile")


def write_run_quotas_json(cfg: dict) -> dict:
    """Upload effective per-service millicores for Detector.__init__ overlay."""
    master = cfg["infra"]["master_ssh_host"]
    effective = topfull_cpu_quotas.effective_cpu_quotas(
        cfg.get("scale_constraints") or []
    )
    write_remote_json(master, topfull_cpu_quotas.RUN_QUOTAS_JSON_PATH, effective)
    step(f"Wrote run quotas: {topfull_cpu_quotas.RUN_QUOTAS_JSON_PATH}")
    return effective


def delete_run_quotas_json(cfg: dict) -> None:
    master = cfg["infra"]["master_ssh_host"]
    ssh(master, f"rm -f {topfull_cpu_quotas.RUN_QUOTAS_JSON_PATH}", check=False)


def ensure_detector_quota_overlay(cfg: dict) -> None:
    """
    Idempotently patch overload_detection.py so Detector.__init__ loads
    topfull_run_quotas.json when present.
    """
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    path = f"{src}/overload_detection.py"
    marker = topfull_cpu_quotas.OVERLAY_MARKER
    r = ssh(
        master,
        f"grep -n '{marker}' {path} 2>/dev/null || true",
        check=False,
    )
    if marker in (r.stdout or ""):
        step(f"Detector quota overlay already present in {path}")
        return

    banner("Patching Detector for per-run CPU quota overlay")
    ssh(master, f"cp {path} {path}.bak.quota-overlay", check=False)

    # Remote patcher: insert snippet immediately before the __init__ return
    # that precedes the "Find overloaded services" docstring.
    patcher = (
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        f"path = Path({path!r})\n"
        "text = path.read_text(encoding='utf-8')\n"
        f"marker = {marker!r}\n"
        "if marker in text:\n"
        "    raise SystemExit(0)\n"
        f"snippet = {topfull_cpu_quotas.DETECTOR_OVERLAY_SNIPPET!r}\n"
        "needle = '    \"\"\"\\n    Find overloaded services'\n"
        "idx = text.find(needle)\n"
        "if idx < 0:\n"
        "    raise SystemExit('overlay insert point not found')\n"
        "before = text[:idx]\n"
        "ret = before.rfind('        return')\n"
        "if ret < 0:\n"
        "    raise SystemExit('__init__ return not found before detect docstring')\n"
        "text = before[:ret] + snippet + '\\n' + before[ret:] + text[idx:]\n"
        "path.write_text(text, encoding='utf-8')\n"
        "print('overlay_patched')\n"
    )
    write_remote_script(master, "/tmp/rg_patch_quota_overlay.py", patcher)
    ssh(master, "python3 /tmp/rg_patch_quota_overlay.py")
    step(f"Patched {path} with {marker}")


def restore_constraints(cfg: dict, restore_records: list):
    """Undo replica constraints. CPU limits are restored via paper reconcile."""
    replica_recs = [r for r in (restore_records or []) if r.get("method") == "replicas"]
    if not replica_recs:
        return

    banner("Restoring topology")
    master = cfg["infra"]["master_ssh_host"]

    for rec in replica_recs:
        dep = rec["deployment"]
        ns = rec["namespace"]
        orig = rec["original_replicas"]
        step(f"Restoring {dep} ({ns}) -> {orig} replicas")
        ssh(master, f"kubectl scale deployment {dep} --replicas={orig} -n {ns}",
            check=False)


# --------------------------------------------------------------------------- #
#  Master stack
# --------------------------------------------------------------------------- #

def start_master_stack(cfg: dict):
    banner("Starting master stack")
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    venv = cfg["infra"]["venv_activate"]

    # Kill any stale processes first.
    # Bracket trick in -f patterns avoids pkill matching this ssh/bash -c line itself.
    step("Killing stale processes...")
    ssh(master,
        "pkill -9 -f '[p]roxy_online_boutique' 2>/dev/null; "
        "pkill -9 -f '[d]eploy_rl.py' 2>/dev/null; "
        "pkill -9 -f '[m]etric_collector.py' 2>/dev/null; "
        "pkill -9 -f '[e]nvoy_retry_collector.py' 2>/dev/null; "
        "pkill -9 -f '[r]esource_usage_collector.py' 2>/dev/null; "
        "pkill -9 -f '[t]opfull_throttle_collector.py' 2>/dev/null; "
        "pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; "
        "tmux kill-server 2>/dev/null; "
        "sleep 2; true",
        check=False)

    # Write start scripts (LF guaranteed by write_remote_script)
    proxy_script = (
        f"#!/bin/bash\n"
        f"cd {src}/proxy\n"
        f"go run proxy_online_boutique.go\n"
    )
    rl_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"cd {src}\n"
        f"python3 deploy_rl.py\n"
    )
    mc_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"cd {src}\n"
        f"python3 metric_collector.py\n"
    )

    write_remote_script(master, "/tmp/rg_proxy.sh", proxy_script)
    write_remote_script(master, "/tmp/rg_rl.sh", rl_script)
    write_remote_script(master, "/tmp/rg_mc.sh", mc_script)

    # Start proxy
    ssh(master, "tmux new-session -d -s proxy /tmp/rg_proxy.sh")
    step("Started: Go proxy (tmux session: proxy)")
    wait_with_progress(5, "proxy init")

    # Start RL controller
    ssh(master, "tmux new-session -d -s toprl /tmp/rg_rl.sh")
    step("Started: deploy_rl.py (tmux session: toprl)")
    wait_with_progress(20, "Ray + RL checkpoint load")

    # Verify deploy_rl is running (-f matches full cmdline; process name is python3)
    r = ssh(master, "pgrep -fa deploy_rl.py 2>/dev/null || true")
    if "deploy_rl" not in r.stdout:
        print("[ERROR] deploy_rl.py did not start. Check tmux session 'toprl' on master.")
        sys.exit(1)
    step("deploy_rl.py running [OK]")

    # Start metric_collector
    ssh(master, "tmux new-session -d -s metrics /tmp/rg_mc.sh")
    step("Started: metric_collector.py (tmux session: metrics)")
    wait_with_progress(5, "metric_collector init")


# --------------------------------------------------------------------------- #
#  RetryGuard
# --------------------------------------------------------------------------- #

def start_retryguard(cfg: dict):
    rg_cfg = cfg["retryguard"]
    if not rg_cfg.get("enabled", False):
        return

    banner("Starting RetryGuard")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    rg_script = cfg["infra"].get(
        "retryguard_script",
        "/home/idozacharia/experiments/retryguard.py"
    )
    deploy_repo_script(master, "retryguard.py", rg_script)

    # Upload RetryGuard runtime parameters as JSON
    params = {
        "rejection_threshold":    rg_cfg["rejection_threshold"],
        "window_duration_seconds": rg_cfg["window_duration_seconds"],
        "disable_windows":        rg_cfg["disable_windows"],
        "re_enable_windows":      rg_cfg["re_enable_windows"],
        "retry_attempts_on":      rg_cfg["retry_attempts_on"],
        "retry_attempts_off":     rg_cfg["retry_attempts_off"],
    }
    write_remote_json(master, "/tmp/retryguard_params.json", params)
    step(f"Uploaded RetryGuard params: re_enable_windows={params['re_enable_windows']} "
         f"({params['re_enable_windows'] * params['window_duration_seconds']}s)")

    rg_start = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {rg_script} --params /tmp/retryguard_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_retryguard.sh", rg_start)
    ssh(master, "tmux new-session -d -s retryguard /tmp/rg_retryguard.sh")
    step(f"Started: RetryGuard (tmux session: retryguard, script: {rg_script})")
    wait_with_progress(3, "RetryGuard init")


# --------------------------------------------------------------------------- #
#  Envoy retry-stats collector (Gap 3 — retries per request)
# --------------------------------------------------------------------------- #

# Istio's default proxyStatsMatcher strips detailed per-cluster/listener stats
# (both outbound upstream_rq_* and inbound downstream_rq_*) from the Envoy
# admin /stats endpoint to save memory. Without this annotation, the mesh
# collector silently gets all-zero data forever — confirmed live on
# 2026-08-20 (PHASE7-DATA-GAPS.md Gap 3) for the outbound-only case.
# Applying it via kubectl patch is idempotent: a no-op (no pod restart)
# once already applied with the same value.
STATS_INCLUSION_REGEX = r"(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)"

# All 11 Boutique Deployments — the full mesh collector scrapes every one of
# these every poll (see PER-SERVICE-MESH-COLLECTOR-DESIGN.md). Keep this list
# in sync with envoy_retry_collector.ALL_SERVICES and
# resource_usage_collector.DEFAULT_SERVICES.
ALL_BOUTIQUE_SERVICES = [
    "frontend",
    "cartservice",
    "checkoutservice",
    "productcatalogservice",
    "paymentservice",
    "recommendationservice",
    "shippingservice",
    "currencyservice",
    "emailservice",
    "adservice",
    "redis-cart",
]


def ensure_envoy_stats_enabled(cfg: dict, caller_pods: list):
    """
    Patch each caller Deployment's pod template with
    sidecar.istio.io/statsInclusionRegexps so Envoy actually exposes
    upstream_rq_retry* counters. Idempotent — only causes a rollout the
    first time it's applied to a given deployment.
    """
    master = cfg["infra"]["master_ssh_host"]
    patch = json.dumps({
        "spec": {"template": {"metadata": {"annotations": {
            "sidecar.istio.io/statsInclusionRegexps": STATS_INCLUSION_REGEX,
        }}}}
    })
    write_remote_json(master, "/tmp/envoy_stats_patch.json",
                       json.loads(patch))
    for dep in caller_pods:
        r = ssh(master,
                f"kubectl patch deployment {dep} -n default --type merge "
                f"--patch-file /tmp/envoy_stats_patch.json",
                check=False)
        if r.returncode != 0:
            print(f"[WARN] Could not patch {dep} for Envoy stats inclusion: "
                  f"{r.stderr.strip()}")
            continue
        ssh(master,
            f"kubectl rollout status deployment/{dep} -n default --timeout=60s",
            check=False)
    step(f"Envoy stats inclusion ensured on: {', '.join(caller_pods)}")


def start_envoy_retry_collector(cfg: dict):
    """
    Start the full-mesh Envoy sidecar collector on master.

    Scrapes every Boutique pod (not just frontend/checkoutservice) for
    outbound (upstream_rq_*) and inbound (downstream_rq_*) stats, writing
    service_edges.csv / service_inbound.csv. Independent of RetryGuard:
    must run in both baseline and RetryGuard conditions so retry volume
    is comparable across arms.
    """
    erc_cfg = cfg.get("envoy_retry_collector", {})
    if not erc_cfg.get("enabled", False):
        return

    banner("Starting Envoy mesh collector")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "envoy_retry_collector_script",
        "/home/idozacharia/experiments/envoy_retry_collector.py",
    )
    deploy_repo_script(master, "envoy_retry_collector.py", script)

    services = list(erc_cfg.get("services", ALL_BOUTIQUE_SERVICES))
    ensure_envoy_stats_enabled(cfg, services)

    params = {
        "poll_interval_seconds": int(erc_cfg.get("poll_interval_seconds", 5)),
    }
    if "services" in erc_cfg:
        params["services"] = erc_cfg["services"]

    write_remote_json(master, "/tmp/envoy_retry_params.json", params)
    step(f"Uploaded Envoy mesh collector params: "
         f"poll_interval={params['poll_interval_seconds']}s "
         f"services={len(services)}")

    start_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {script} --params /tmp/envoy_retry_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_envoy_retry.sh", start_script)
    ssh(master, "tmux new-session -d -s envoyretry /tmp/rg_envoy_retry.sh")
    step(f"Started: Envoy mesh collector "
         f"(tmux session: envoyretry, script: {script})")
    wait_with_progress(3, "Envoy mesh collector init")


# --------------------------------------------------------------------------- #
#  Resource usage collector (Layer 2 — CPU/memory per service)
# --------------------------------------------------------------------------- #

def start_resource_usage_collector(cfg: dict):
    """
    Start the kubelet stats/summary scraper on master.

    Independent of RetryGuard: must run in both baseline and RetryGuard arms.
    """
    ruc_cfg = cfg.get("resource_usage_collector", {})
    if not ruc_cfg.get("enabled", False):
        return

    banner("Starting resource usage collector")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "resource_usage_collector_script",
        "/home/idozacharia/experiments/resource_usage_collector.py",
    )
    deploy_repo_script(master, "resource_usage_collector.py", script)

    params = {
        "poll_interval_seconds": int(ruc_cfg.get("poll_interval_seconds", 5)),
    }
    if "services" in ruc_cfg:
        params["services"] = ruc_cfg["services"]

    write_remote_json(master, "/tmp/resource_usage_params.json", params)
    step(f"Uploaded resource usage collector params: "
         f"poll_interval={params['poll_interval_seconds']}s")

    start_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {script} --params /tmp/resource_usage_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_resource_usage.sh", start_script)
    ssh(master, "tmux new-session -d -s resourceusage /tmp/rg_resource_usage.sh")
    step(f"Started: resource usage collector "
         f"(tmux session: resourceusage, script: {script})")
    wait_with_progress(3, "Resource usage collector init")


def start_topfull_throttle_collector(cfg: dict):
    """
    Start the TopFull throttle / detector collector on master.

    Independent of RetryGuard: must run in both baseline and RetryGuard arms.
    Read-only against rate_config/ and :8090/stats — no teardown.
    """
    ttc_cfg = cfg.get("topfull_throttle_collector", {})
    if not ttc_cfg.get("enabled", False):
        return

    banner("Starting TopFull throttle collector")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "topfull_throttle_collector_script",
        "/home/idozacharia/experiments/topfull_throttle_collector.py",
    )
    deploy_repo_script(master, "topfull_throttle_collector.py", script)
    params = {
        "poll_interval_seconds": int(ttc_cfg.get("poll_interval_seconds", 1)),
    }
    write_remote_json(master, "/tmp/topfull_throttle_params.json", params)
    step(
        "Uploaded TopFull throttle collector params: "
        f"poll_interval={params['poll_interval_seconds']}s"
    )
    start_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {script} --params /tmp/topfull_throttle_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_topfull_throttle.sh", start_script)
    ssh(master, "tmux new-session -d -s throttle /tmp/rg_topfull_throttle.sh")
    step("Started: TopFull throttle collector "
         f"(tmux session: throttle, script: {script})")
    wait_with_progress(3, "TopFull throttle collector init")


# --------------------------------------------------------------------------- #
#  Locust
# --------------------------------------------------------------------------- #

def _launch_locust(cfg: dict, user_counts: dict, spawn_rate) -> None:
    """Kill any running Locust and start it fresh at the given load level."""
    loadgen = cfg["infra"]["loadgen_ssh_host"]
    loadgen_path = cfg["infra"]["topfull_loadgen_path"]
    lc = cfg.get("locust", {})
    scripts = lc.get("scripts", ["online_boutique_create.sh", "online_boutique_create2.sh"])

    # Env var mapping: YAML key -> shell variable name in create scripts
    ENV_MAP = {
        "getproduct":   "GETPRODUCT",
        "postcheckout": "POSTCHECKOUT",
        "getcart":      "GETCART",
        "postcart":     "POSTCART",
        "emptycart":    "CART",      # create scripts use CART, not EMPTYCART
    }

    exports = []
    for yaml_key, shell_var in ENV_MAP.items():
        if yaml_key in user_counts:
            exports.append(f"export {shell_var}={user_counts[yaml_key]}")
    if spawn_rate is not None:
        exports.append(f"export RATE={spawn_rate}")
    env_prefix = "; ".join(exports) + "; " if exports else ""

    if exports:
        step("Applying user counts:")
        for e in exports:
            print(f"         {e}")

    # Kill any stale Locust processes (also used for a mid-run phase switch)
    ssh(loadgen, "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; sleep 1; true",
        check=False)

    launch_cmd = " && ".join(f"bash {s}" for s in scripts)
    launch_script = (
        f"#!/bin/bash\n"
        f"cd {loadgen_path}\n"
        f"{env_prefix}{launch_cmd}\n"
    )
    write_remote_script(loadgen, "/tmp/rg_locust_launch.sh", launch_script)
    ssh(loadgen, "tmux new-session -d -s loadgen /tmp/rg_locust_launch.sh")

    wait_with_progress(8, "Locust workers connecting")

    r = ssh(loadgen, "pgrep -c locust 2>/dev/null || echo 0")
    count = int(r.stdout.strip())
    if count == 0:
        print("[ERROR] No Locust processes found. Check the create scripts on the loadgen.")
        sys.exit(1)
    step(f"Locust running: {count} processes [OK]")


def start_locust(cfg: dict, phases: list[dict]) -> None:
    banner("Starting Locust load")
    first = phases[0]
    _launch_locust(cfg, first["user_counts"], first["spawn_rate"])


def switch_locust_phase(cfg: dict, phase: dict) -> None:
    banner(f"Switching Locust load phase at t={phase['at_seconds']}s")
    _launch_locust(cfg, phase["user_counts"], phase["spawn_rate"])


def stop_locust(cfg: dict):
    loadgen = cfg["infra"]["loadgen_ssh_host"]
    step("Stopping Locust...")
    ssh(loadgen,
        "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true",
        check=False)


# --------------------------------------------------------------------------- #
#  Stop all master processes
# --------------------------------------------------------------------------- #

def stop_master_stack(cfg: dict):
    master = cfg["infra"]["master_ssh_host"]
    step("Stopping master processes (metric_collector, deploy_rl, proxy, "
         "RetryGuard, Envoy retry collector, resource usage collector, "
         "TopFull throttle collector, Ray)...")
    # Bracket trick avoids pkill matching this ssh/bash -c line itself.
    ssh(master,
        "pkill -f '[m]etric_collector.py' 2>/dev/null; "
        "pkill -f '[d]eploy_rl.py' 2>/dev/null; "
        "pkill -f '[p]roxy_online_boutique' 2>/dev/null; "
        "pkill -f '[r]etryguard.py' 2>/dev/null; "
        "pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; "
        "pkill -f '[r]esource_usage_collector.py' 2>/dev/null; "
        "pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; "
        "sleep 2; "
        "pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; "
        "tmux kill-server 2>/dev/null; "
        "true",
        check=False)


def restore_virtualservice_retries(cfg: dict):
    """
    Re-apply default retries.attempts after a RetryGuard run.

    RetryGuard disables retries by *omitting* the retries block (Istio rejects
    attempts:0). If the controller is killed while retries are OFF, the mesh
    would otherwise stay without retries for subsequent experiments.
    """
    if not cfg.get("retryguard", {}).get("enabled", False):
        return

    banner("Restoring VirtualService retries")
    master = cfg["infra"]["master_ssh_host"]
    attempts = int(cfg["retryguard"].get("retry_attempts_on", 3))
    services = [
        "adservice", "cartservice", "checkoutservice", "currencyservice",
        "emailservice", "frontend", "paymentservice", "productcatalogservice",
        "recommendationservice", "shippingservice",
    ]
    for svc in services:
        patch = json.dumps({
            "spec": {
                "http": [{
                    "retries": {
                        "attempts": attempts,
                        "retryOn": "5xx,reset,connect-failure",
                    },
                    "route": [{"destination": {"host": svc}}],
                }]
            }
        })
        ssh(master,
            f"kubectl patch virtualservice {svc} -n default -p '{patch}'",
            check=False)
    step(f"Restored retries.attempts={attempts} on {len(services)} VirtualServices")


# --------------------------------------------------------------------------- #
#  Results collection
# --------------------------------------------------------------------------- #

def scenario_dir_name(cfg: dict) -> str:
    """Map a run's scenario_id/scenario_name to its campaign_48/ scenario subfolder
    (e.g. S1_normal_op). Keep in sync with experiments/results/campaign_48/README.md."""
    sid = cfg.get("scenario_id")
    name = cfg.get("scenario_name", "")
    if sid == 1:
        return "S1_normal_op"
    if sid == 2:
        return "S2_sustained_overload"
    if sid == 3:
        return "S3_targeted_bottleneck"
    if sid == 4:
        return "S4A_topology_position_A" if name.endswith("_A") else "S4B_topology_position_B"
    if sid == 5:
        return "S5_interval_tuning"
    if sid == 6:
        return "S6_forced_recovery"
    return ""  # unknown scenario_id — fall back to no subfolder


def collect_results(
    cfg: dict,
    capacity: dict | None = None,
    effective_quotas: dict | None = None,
) -> str:
    banner("Collecting results")
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    results_base = cfg["infra"]["results_base_path"]
    log_folder = cfg["log_folder"]
    dest = f"{results_base}/{log_folder}"

    # Copy logs on remote
    ssh(master, f"mkdir -p {dest}")
    ssh(master, f"cp -r {src}/logs/. {dest}/ 2>/dev/null; true", check=False)

    paper = {
        s: topfull_cpu_quotas.paper_limit_for(s)
        for s in topfull_cpu_quotas.RECONCILE_SERVICES
    }
    effective = effective_quotas or topfull_cpu_quotas.effective_cpu_quotas(
        cfg.get("scale_constraints") or []
    )

    # Write a run manifest alongside the logs (config snapshot + timestamps)
    manifest = {
        "scenario_id":   cfg["scenario_id"],
        "scenario_name": cfg["scenario_name"],
        "condition":     cfg["condition"],
        "run_number":    cfg["run_number"],
        "duration_seconds": cfg["duration_seconds"],
        "retryguard":    cfg["retryguard"],
        "envoy_retry_collector": cfg.get("envoy_retry_collector", {}),
        "resource_usage_collector": cfg.get("resource_usage_collector", {}),
        "topfull_throttle_collector": cfg.get("topfull_throttle_collector", {}),
        "scale_constraints": cfg.get("scale_constraints", []),
        "paper_cpu_quotas": paper,
        "effective_cpu_quotas": effective,
        "log_folder":    log_folder,
        "collected_at":  datetime.utcnow().isoformat() + "Z",
    }
    write_remote_json(master, f"{dest}/run_manifest.json", manifest)
    write_remote_json(master, f"{dest}/service_capacity.json", capacity or {})

    step(f"Results saved to (on master): {dest}")
    step("To pull results to your PC:")
    scen_dir = scenario_dir_name(cfg)
    local_dest = f"experiments/results/campaign_48/{scen_dir}/" if scen_dir else "experiments/results/campaign_48/"
    print(f"    scp -r topfull-master:{dest} {local_dest}")
    return dest


# --------------------------------------------------------------------------- #
#  Main experiment loop
# --------------------------------------------------------------------------- #

def run(config_path: str):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    topfull_cpu_quotas.validate_scale_constraints(cfg.get("scale_constraints") or [])

    scenario    = cfg["scenario_name"]
    condition   = cfg["condition"]
    run_n       = cfg["run_number"]
    duration    = cfg["duration_seconds"]
    log_folder  = cfg["log_folder"]
    rg_enabled  = cfg["retryguard"].get("enabled", False)
    phases = resolve_locust_phases(cfg)

    print(f"\n{'='*60}")
    print(f"  Scenario : {cfg['scenario_id']} - {scenario}")
    print(f"  Condition: {condition}")
    print(f"  Run #    : {run_n}")
    print(f"  Duration : {duration}s  ({duration//60}m {duration%60}s)")
    print(f"  RetryGuard: {'ON' if rg_enabled else 'OFF'}")
    if rg_enabled:
        rg = cfg["retryguard"]
        rew = rg["re_enable_windows"]
        wd  = rg["window_duration_seconds"]
        print(f"    threshold      : {rg['rejection_threshold']*100:.0f}%")
        print(f"    disable_windows: {rg['disable_windows']}  ({rg['disable_windows']*wd}s)")
        print(f"    re_enable_windows: {rew}  ({rew*wd}s)")
    erc_enabled = cfg.get("envoy_retry_collector", {}).get("enabled", False)
    print(f"  Envoy retry collector: {'ON' if erc_enabled else 'OFF'}")
    if erc_enabled:
        print(f"    poll_interval  : "
              f"{cfg['envoy_retry_collector'].get('poll_interval_seconds', 5)}s")
    ruc_enabled = cfg.get("resource_usage_collector", {}).get("enabled", False)
    print(f"  Resource usage collector: {'ON' if ruc_enabled else 'OFF'}")
    if ruc_enabled:
        print(f"    poll_interval  : "
              f"{cfg['resource_usage_collector'].get('poll_interval_seconds', 5)}s")
    ttc_enabled = cfg.get("topfull_throttle_collector", {}).get("enabled", False)
    print(f"  TopFull throttle collector: {'ON' if ttc_enabled else 'OFF'}")
    if ttc_enabled:
        print(f"    poll_interval  : "
              f"{cfg['topfull_throttle_collector'].get('poll_interval_seconds', 1)}s")
    if cfg.get("scale_constraints"):
        print(f"  Constraints:")
        for c in cfg["scale_constraints"]:
            method = c.get("method", "replicas")
            if method == "replicas":
                print(f"    {c['deployment']}: scale to {c['replicas']} replica(s)")
            elif method == "cpu_limit":
                frac = c.get("cpu_limit_fraction")
                qty = topfull_cpu_quotas.kubectl_cpu_quantity(
                    topfull_cpu_quotas.millicores_from_fraction(
                        topfull_cpu_quotas.paper_limit_for(c["deployment"]),
                        float(frac),
                    )
                )
                print(
                    f"    {c['deployment']}: cpu_limit_fraction={frac} "
                    f"({qty})"
                )
    if len(phases) > 1:
        print(f"  Load phases:")
        for p in phases:
            print(f"    t={p['at_seconds']:4d}s  user_counts={p['user_counts']}")
    print(f"  Output   : {log_folder}")
    print(f"{'='*60}")

    restore_records = []
    capacity = {}
    effective_quotas = {}
    start_ts = datetime.now()

    try:
        preflight(cfg)
        clear_logs(cfg)
        # Reconcile first (heals leftover S3 100m). Wait only when there are
        # no fraction constraints — apply_constraints already waits 20s.
        has_constraints = bool(cfg.get("scale_constraints"))
        reconcile_paper_cpu_limits(cfg, wait=not has_constraints)
        restore_records = apply_constraints(cfg)
        capacity = capture_service_capacity(cfg, ALL_BOUTIQUE_SERVICES)
        effective_quotas = write_run_quotas_json(cfg)
        ensure_detector_quota_overlay(cfg)

        start_master_stack(cfg)

        # Envoy retry collector is independent of RetryGuard — run in both arms.
        start_envoy_retry_collector(cfg)

        # CPU/memory collector — run in both arms (Layer 2).
        start_resource_usage_collector(cfg)

        start_topfull_throttle_collector(cfg)

        if rg_enabled:
            start_retryguard(cfg)

        start_locust(cfg, phases)
        fired_phases = {0}

        banner(f"Experiment running - {duration}s")
        elapsed = 0
        interval = 15
        while elapsed < duration:
            remaining = duration - elapsed
            pct = int(elapsed / duration * 40)
            bar = "#" * pct + "." * (40 - pct)
            print(f"\r  [{bar}] {elapsed:4d}s / {duration}s  ({remaining}s left) ",
                  end="", flush=True)
            step_seconds = min(interval, remaining)
            time.sleep(step_seconds)
            elapsed += step_seconds

            for idx in due_phases(elapsed, fired_phases, phases):
                print()
                switch_locust_phase(cfg, phases[idx])
                fired_phases.add(idx)
        print(f"\r  {'#'*40}  {duration}s / {duration}s  (done)              ")

    except KeyboardInterrupt:
        print("\n\n[ABORT] Interrupted - stopping and collecting partial results.")

    finally:
        end_ts = datetime.now()
        actual_duration = int((end_ts - start_ts).total_seconds())

        banner("Stopping all processes")
        stop_locust(cfg)
        stop_master_stack(cfg)

        collect_results(cfg, capacity, effective_quotas=effective_quotas)

        delete_run_quotas_json(cfg)
        if restore_records:
            restore_constraints(cfg, restore_records)
        # Always return to paper CPU limits (not pre-run dirty blobs).
        reconcile_paper_cpu_limits(cfg, wait=False)

        restore_virtualservice_retries(cfg)

        banner("Done")
        print(f"  Scenario : {scenario}  |  Condition: {condition}  |  Run: {run_n}")
        print(f"  Started  : {start_ts.strftime('%H:%M:%S')}")
        print(f"  Ended    : {end_ts.strftime('%H:%M:%S')}")
        print(f"  Actual   : {actual_duration}s")
        print(f"  Logs     : {log_folder}")
        print()


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a TopFull + RetryGuard experiment scenario."
    )
    parser.add_argument("config", help="Path to scenario YAML config file")
    args = parser.parse_args()

    try:
        import yaml  # noqa: F401
    except ImportError:
        print("[ERROR] PyYAML not installed. Run: pip install pyyaml")
        sys.exit(1)

    if not Path(args.config).exists():
        print(f"[ERROR] Config file not found: {args.config}")
        sys.exit(1)

    run(args.config)
