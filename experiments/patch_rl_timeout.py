#!/usr/bin/env python3
"""
Patch master's TopFull RL loop so a stalled proxy cannot block it, and so its log
carries the facts needed to see a stall. Safe to run more than once.

Run ON MASTER (the live copy is not in this repo's TopFull/ submodule):

    python3 patch_rl_timeout.py [--src DIR] [--dry-run]

Changes (see Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md):
  overload_detection.py  current_rps(): requests.get(..., timeout=2.0); on failure raise
                         ProxyStatsUnavailable; RL_RPS_START / RL_RPS_END / RL_RPS_TIMEOUT
                         lines; RL_CAP_APPLY line per applied cap. Detector construction
                         also catches that timeout, prints RL_SKIP where=init, and uses an
                         empty rps dict so each API threshold stays 10000 for that startup.
  deploy_rl.py           Agent.run(), Agent.add_apis() and the main loop skip the tick on
                         ProxyStatsUnavailable and retry on the next tick; RL_LOOP_START
                         heartbeat; RL_SKIP lines.
The paths rewritten for this VM (global_config_path) are not touched.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_SRC = Path(
    "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src"
)
MARKER = "RL_TIMEOUT_PATCH v1"


class PatchError(RuntimeError):
    pass


# --- overload_detection.py --------------------------------------------------

OD_IMPORT_OLD = "import random\nimport threading\n"
OD_IMPORT_NEW = f'''import random
import threading
import time as _rl_time
import requests as _rl_requests

# {MARKER}: deviation from upstream TopFull, see Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md
RL_PROXY_TIMEOUT_S = 2.0


class ProxyStatsUnavailable(Exception):
    """The proxy's /stats did not answer within RL_PROXY_TIMEOUT_S."""
'''

OD_CAP_OLD = "        print(f\"{api['name']}: {api['threshold']}\")\n        total += api['threshold']\n"
OD_CAP_NEW = (
    "        print(f\"{api['name']}: {api['threshold']}\")\n"
    "        print(f\"RL_CAP_APPLY api={api['name']} threshold={api['threshold']}\", flush=True)\n"
    "        total += api['threshold']\n"
)

OD_DEF_OLD = "    def current_rps(self):\n"
OD_DEF_NEW = "    def current_rps(self, caller=\"unknown\"):\n"

OD_GET_OLD = (
    "        response = requests.get(url, proxies=proxies)\n"
    "        if not response.ok:\n"
    "            return None\n"
)
OD_GET_NEW = (
    "        print(f\"RL_RPS_START caller={caller}\", flush=True)\n"
    "        _t0 = _rl_time.time()\n"
    "        try:\n"
    "            response = requests.get(url, proxies=proxies, timeout=RL_PROXY_TIMEOUT_S)\n"
    "        except _rl_requests.exceptions.RequestException as exc:\n"
    "            print(f\"RL_RPS_TIMEOUT caller={caller} elapsed_s={_rl_time.time() - _t0:.2f} \"\n"
    "                  f\"timeout_s={RL_PROXY_TIMEOUT_S} error={type(exc).__name__}\", flush=True)\n"
    "            raise ProxyStatsUnavailable(str(exc))\n"
    "        print(f\"RL_RPS_END caller={caller} elapsed_s={_rl_time.time() - _t0:.2f} \"\n"
    "              f\"ok={int(response.ok)}\", flush=True)\n"
    "        if not response.ok:\n"
    "            return None\n"
)

OD_CLUSTER_OLD = "        rps = self.current_rps()\n        # print(rps)\n"
OD_CLUSTER_NEW = "        rps = self.current_rps(caller=\"clustering\")\n        # print(rps)\n"

OD_INIT_OLD = (
    "        self.kube = kubeAPI()\n"
    "        \n"
    "        rps = self.current_rps()\n"
    "\n"
    "        self.event = threading.Event()\n"
)
OD_INIT_NEW = (
    "        self.kube = kubeAPI()\n"
    "        \n"
    "        try:\n"
    "            rps = self.current_rps(caller=\"init\")\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=init reason=proxy_stats_unavailable\", flush=True)\n"
    "            rps = {}\n"
    "\n"
    "        self.event = threading.Event()\n"
)

# --- deploy_rl.py -----------------------------------------------------------

DR_RUN_OLD = (
    "        goodput = 0\n"
    "        clean_apis = []\n"
    "        rps = self.detector.current_rps()\n"
)
DR_RUN_NEW = (
    "        goodput = 0\n"
    "        clean_apis = []\n"
    f"        # {MARKER}\n"
    "        try:\n"
    "            rps = self.detector.current_rps(caller=\"agent\")\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=agent reason=proxy_stats_unavailable\", flush=True)\n"
    "            return\n"
)

DR_APPLY_OLD = "        self.detector.apply_v2(float(action), self.target_apis, [])\n"
DR_APPLY_NEW = (
    "        try:\n"
    "            self.detector.apply_v2(float(action), self.target_apis, [])\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=agent reason=proxy_stats_unavailable\", flush=True)\n"
    "            return\n"
)

DR_ADD_OLD = (
    "    def add_apis(self, new_apis):\n"
    "        rps = self.detector.current_rps()\n"
)
DR_ADD_NEW = (
    "    def add_apis(self, new_apis):\n"
    "        try:\n"
    "            rps = self.detector.current_rps(caller=\"add_apis\")\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=add_apis reason=proxy_stats_unavailable\", flush=True)\n"
    "            return\n"
)

DR_LOOP_OLD = "# Start Loop\nwhile True:\n    time.sleep(2)\n    # Clean stopped agents\n"
DR_LOOP_NEW = (
    "# Start Loop\n"
    "_rl_iter = 0\n"
    "while True:\n"
    "    time.sleep(2)\n"
    "    _rl_iter += 1\n"
    "    print(f\"RL_LOOP_START iter={_rl_iter}\", flush=True)\n"
    "    # Clean stopped agents\n"
)

DR_CLUSTER_OLD = "        cluster_apis = detector.clustering([svc])\n        print(cluster_apis)\n"
DR_CLUSTER_NEW = (
    "        try:\n"
    "            cluster_apis = detector.clustering([svc])\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(f\"RL_SKIP where=clustering svc={svc} reason=proxy_stats_unavailable\", flush=True)\n"
    "            continue\n"
    "        print(cluster_apis)\n"
)

OVERLOAD_EDITS = [
    (OD_IMPORT_OLD, OD_IMPORT_NEW),
    (OD_CAP_OLD, OD_CAP_NEW),
    (OD_DEF_OLD, OD_DEF_NEW),
    (OD_GET_OLD, OD_GET_NEW),
    (OD_CLUSTER_OLD, OD_CLUSTER_NEW),
    (OD_INIT_OLD, OD_INIT_NEW),
]
DEPLOY_EDITS = [
    (DR_RUN_OLD, DR_RUN_NEW),
    (DR_APPLY_OLD, DR_APPLY_NEW),
    (DR_ADD_OLD, DR_ADD_NEW),
    (DR_LOOP_OLD, DR_LOOP_NEW),
    (DR_CLUSTER_OLD, DR_CLUSTER_NEW),
]


def _apply_one(text: str, edits: list, name: str) -> str:
    crlf = "\r\n" in text
    body = text.replace("\r\n", "\n")
    if MARKER in body:
        return text
    for old, new in edits:
        if body.count(old) != 1:
            raise PatchError(
                f"{name}: anchor not found exactly once ({body.count(old)} matches): "
                f"{old.strip().splitlines()[0]!r}. The live file differs from upstream; "
                "patch by hand and keep the marker."
            )
        body = body.replace(old, new)
    return body.replace("\n", "\r\n") if crlf else body


def apply(text_overload: str, text_deploy: str) -> tuple[str, str]:
    """Return both files patched. Idempotent per file. Raises PatchError on a missing anchor."""
    return (
        _apply_one(text_overload, OVERLOAD_EDITS, "overload_detection.py"),
        _apply_one(text_deploy, DEPLOY_EDITS, "deploy_rl.py"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    over_path = args.src / "overload_detection.py"
    dep_path = args.src / "deploy_rl.py"
    try:
        over, dep = apply(over_path.read_text(encoding="utf-8"), dep_path.read_text(encoding="utf-8"))
    except PatchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for path, new in ((over_path, over), (dep_path, dep)):
        old = path.read_text(encoding="utf-8")
        if new == old:
            print(f"{path.name}: already patched")
            continue
        if args.dry_run:
            print(f"{path.name}: would patch")
            continue
        shutil.copy2(path, path.with_name(f"{path.name}.orig-{stamp}"))
        path.write_text(new, encoding="utf-8")
        print(f"{path.name}: patched (backup {path.name}.orig-{stamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
