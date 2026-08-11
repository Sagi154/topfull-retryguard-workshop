#!/usr/bin/env python3
"""
run_scenario.py - Experiment runner for TopFull + RetryGuard scenarios.

Reads a scenario YAML config and orchestrates the full experiment:
  1. Pre-flight cluster health check
  2. Apply topology constraints (kubectl scale / cpu_limit)
  3. Start master stack (proxy -> deploy_rl -> metric_collector)
  4. Optionally start RetryGuard
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
            cpu_limit = c["cpu_limit"]
            container = c.get("container", "server")
            # Capture full original resources so restore is exact (requests must
            # also drop: K8s requires request <= limit, and Boutique defaults
            # request 200m–500m which exceeds a 100m limit).
            r = ssh(master,
                    f"kubectl get deployment {dep} -n {ns} "
                    f"-o jsonpath='{{.spec.template.spec.containers[0].resources}}'")
            original_resources = r.stdout.strip() or "{}"
            step(f"Applying CPU limit {cpu_limit} to {dep}/{container} ({ns})")
            patch = json.dumps({
                "spec": {"template": {"spec": {"containers": [
                    {"name": container, "resources": {
                        "limits": {"cpu": cpu_limit},
                        "requests": {"cpu": cpu_limit},
                    }}
                ]}}}
            })
            ssh(master, f"kubectl patch deployment {dep} -n {ns} -p '{patch}'")
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


def restore_constraints(cfg: dict, restore_records: list):
    """Undo all topology constraints applied by apply_constraints()."""
    if not restore_records:
        return

    banner("Restoring topology")
    master = cfg["infra"]["master_ssh_host"]

    for rec in restore_records:
        dep = rec["deployment"]
        ns = rec["namespace"]

        if rec["method"] == "replicas":
            orig = rec["original_replicas"]
            step(f"Restoring {dep} ({ns}) -> {orig} replicas")
            ssh(master, f"kubectl scale deployment {dep} --replicas={orig} -n {ns}",
                check=False)

        elif rec["method"] == "cpu_limit":
            container = rec["container"]
            step(f"Restoring CPU resources on {dep}/{container} ({ns})")
            # Restore the full original resources blob (limits + requests).
            try:
                orig = json.loads(rec.get("original_resources") or "{}")
            except json.JSONDecodeError:
                orig = {}
            if orig:
                patch = json.dumps({
                    "spec": {"template": {"spec": {"containers": [
                        {"name": container, "resources": orig}
                    ]}}}
                })
                ssh(master, f"kubectl patch deployment {dep} -n {ns} -p '{patch}'",
                    check=False)
            else:
                # Fallback: remove cpu limit only (legacy restore records)
                patch = json.dumps([
                    {"op": "remove",
                     "path": "/spec/template/spec/containers/0/resources/limits/cpu"}
                ])
                ssh(master,
                    f"kubectl patch deployment {dep} -n {ns} --type=json -p '{patch}'",
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
#  Locust
# --------------------------------------------------------------------------- #

def start_locust(cfg: dict):
    banner("Starting Locust load")
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

    user_counts = lc.get("user_counts", {})
    exports = []
    for yaml_key, shell_var in ENV_MAP.items():
        if yaml_key in user_counts:
            exports.append(f"export {shell_var}={user_counts[yaml_key]}")
    if "spawn_rate" in lc:
        exports.append(f"export RATE={lc['spawn_rate']}")
    env_prefix = "; ".join(exports) + "; " if exports else ""

    if exports:
        step("Applying user counts from config:")
        for e in exports:
            print(f"         {e}")

    # Kill any stale Locust processes
    ssh(loadgen, "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; sleep 1; true",
        check=False)

    # Write and execute a launch script on the loadgen
    launch_cmd = " && ".join(f"bash {s}" for s in scripts)
    launch_script = (
        f"#!/bin/bash\n"
        f"cd {loadgen_path}\n"
        f"{env_prefix}{launch_cmd}\n"
    )
    write_remote_script(loadgen, "/tmp/rg_locust_launch.sh", launch_script)
    ssh(loadgen, "tmux new-session -d -s loadgen /tmp/rg_locust_launch.sh")

    wait_with_progress(8, "Locust workers connecting")

    # Verify Locust is running
    r = ssh(loadgen, "pgrep -c locust 2>/dev/null || echo 0")
    count = int(r.stdout.strip())
    if count == 0:
        print("[ERROR] No Locust processes found. Check the create scripts on the loadgen.")
        sys.exit(1)
    step(f"Locust running: {count} processes [OK]")


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
    step("Stopping master processes (metric_collector, deploy_rl, proxy, RetryGuard, Ray)...")
    # Bracket trick avoids pkill matching this ssh/bash -c line itself.
    ssh(master,
        "pkill -f '[m]etric_collector.py' 2>/dev/null; "
        "pkill -f '[d]eploy_rl.py' 2>/dev/null; "
        "pkill -f '[p]roxy_online_boutique' 2>/dev/null; "
        "pkill -f '[r]etryguard.py' 2>/dev/null; "
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

def collect_results(cfg: dict) -> str:
    banner("Collecting results")
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    results_base = cfg["infra"]["results_base_path"]
    log_folder = cfg["log_folder"]
    dest = f"{results_base}/{log_folder}"

    # Copy logs on remote
    ssh(master, f"mkdir -p {dest}")
    ssh(master, f"cp -r {src}/logs/. {dest}/ 2>/dev/null; true", check=False)

    # Write a run manifest alongside the logs (config snapshot + timestamps)
    manifest = {
        "scenario_id":   cfg["scenario_id"],
        "scenario_name": cfg["scenario_name"],
        "condition":     cfg["condition"],
        "run_number":    cfg["run_number"],
        "duration_seconds": cfg["duration_seconds"],
        "retryguard":    cfg["retryguard"],
        "scale_constraints": cfg.get("scale_constraints", []),
        "log_folder":    log_folder,
        "collected_at":  datetime.utcnow().isoformat() + "Z",
    }
    write_remote_json(master, f"{dest}/run_manifest.json", manifest)

    step(f"Results saved to (on master): {dest}")
    step("To pull results to your PC:")
    print(f"    scp -r topfull-master:{dest} experiments/results/")
    return dest


# --------------------------------------------------------------------------- #
#  Main experiment loop
# --------------------------------------------------------------------------- #

def run(config_path: str):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    scenario    = cfg["scenario_name"]
    condition   = cfg["condition"]
    run_n       = cfg["run_number"]
    duration    = cfg["duration_seconds"]
    log_folder  = cfg["log_folder"]
    rg_enabled  = cfg["retryguard"].get("enabled", False)

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
    if cfg.get("scale_constraints"):
        print(f"  Constraints:")
        for c in cfg["scale_constraints"]:
            method = c.get("method", "replicas")
            if method == "replicas":
                print(f"    {c['deployment']}: scale to {c['replicas']} replica(s)")
            elif method == "cpu_limit":
                print(f"    {c['deployment']}: cpu_limit={c['cpu_limit']}")
    print(f"  Output   : {log_folder}")
    print(f"{'='*60}")

    restore_records = []
    start_ts = datetime.now()

    try:
        preflight(cfg)
        clear_logs(cfg)
        restore_records = apply_constraints(cfg)

        start_master_stack(cfg)

        if rg_enabled:
            start_retryguard(cfg)

        start_locust(cfg)

        banner(f"Experiment running - {duration}s")
        elapsed = 0
        interval = 15
        while elapsed < duration:
            remaining = duration - elapsed
            pct = int(elapsed / duration * 40)
            bar = "#" * pct + "." * (40 - pct)
            print(f"\r  [{bar}] {elapsed:4d}s / {duration}s  ({remaining}s left) ",
                  end="", flush=True)
            time.sleep(min(interval, remaining))
            elapsed += min(interval, remaining)
        print(f"\r  {'#'*40}  {duration}s / {duration}s  (done)              ")

    except KeyboardInterrupt:
        print("\n\n[ABORT] Interrupted - stopping and collecting partial results.")

    finally:
        end_ts = datetime.now()
        actual_duration = int((end_ts - start_ts).total_seconds())

        banner("Stopping all processes")
        stop_locust(cfg)
        stop_master_stack(cfg)

        collect_results(cfg)

        if restore_records:
            restore_constraints(cfg, restore_records)

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
