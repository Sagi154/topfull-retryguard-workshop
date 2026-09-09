"""
topfull_cpu_quotas.py — Paper CPU quotas (TopFull Detector table) and
fraction helpers for S3/S4 bottlenecks.

Units are millicores, matching cAdvisor latest_usage.cpu and kubectl 'Nm'.
"""
from __future__ import annotations

from typing import Dict, List

DEFAULT_PAPER_LIMIT_MILLICORES = 1000

PAPER_CPU_LIMIT_MILLICORES: Dict[str, int] = {
    "cartservice": 1000,
    "currencyservice": 1000,
    "frontend": 1000,
    "adservice": 1000,
    "productcatalogservice": 500,
    "checkoutservice": 1000,
    "recommendationservice": 2000,
}

PAPER_CPU_REQUEST_MILLICORES: Dict[str, int] = {
    "cartservice": 500,
    "currencyservice": 500,
    "frontend": 500,
    "adservice": 500,
    "productcatalogservice": 250,
    "checkoutservice": 500,
    "recommendationservice": 1000,
    "paymentservice": 200,
}

RECONCILE_SERVICES = (
    "cartservice",
    "currencyservice",
    "frontend",
    "adservice",
    "productcatalogservice",
    "checkoutservice",
    "recommendationservice",
    "paymentservice",
)

RUN_QUOTAS_JSON_PATH = "/home/idozacharia/experiments/topfull_run_quotas.json"
OVERLAY_MARKER = "TOPFULL_RUN_QUOTAS_OVERLAY"

# Indentation matches Detector.__init__ body (8 spaces).
DETECTOR_OVERLAY_SNIPPET = '''
        # TOPFULL_RUN_QUOTAS_OVERLAY
        _quota_path = "/home/idozacharia/experiments/topfull_run_quotas.json"
        try:
            with open(_quota_path, "r") as _qf:
                _overlay = json.load(_qf)
            for _svc, _cpu in _overlay.items():
                if _svc in self.services:
                    self.services[_svc]["cpu"] = int(_cpu)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
'''


def paper_limit_for(service: str) -> int:
    return int(PAPER_CPU_LIMIT_MILLICORES.get(service, DEFAULT_PAPER_LIMIT_MILLICORES))


def paper_request_for(service: str) -> int:
    if service in PAPER_CPU_REQUEST_MILLICORES:
        return int(PAPER_CPU_REQUEST_MILLICORES[service])
    return paper_limit_for(service)


def millicores_from_fraction(paper_limit: int, fraction: float) -> int:
    if fraction <= 0 or fraction > 1:
        raise ValueError(f"cpu_limit_fraction must be in (0, 1], got {fraction}")
    return int(paper_limit * fraction)


def kubectl_cpu_quantity(millicores: int) -> str:
    return f"{int(millicores)}m"


def validate_scale_constraints(constraints: List[dict]) -> None:
    known = set(PAPER_CPU_LIMIT_MILLICORES) | set(RECONCILE_SERVICES)
    for c in constraints or []:
        if c.get("method") != "cpu_limit":
            continue
        if "cpu_limit" in c:
            raise ValueError(
                "scale_constraints cpu_limit is removed; use cpu_limit_fraction"
            )
        if "cpu_limit_fraction" not in c:
            raise ValueError("cpu_limit constraint requires cpu_limit_fraction")
        dep = c.get("deployment")
        if dep not in known:
            raise ValueError(f"no paper quota for deployment {dep}")
        millicores_from_fraction(paper_limit_for(dep), float(c["cpu_limit_fraction"]))


def effective_cpu_quotas(constraints: List[dict]) -> Dict[str, int]:
    out = {s: paper_limit_for(s) for s in RECONCILE_SERVICES}
    for name, lim in PAPER_CPU_LIMIT_MILLICORES.items():
        out[name] = lim
    for c in constraints or []:
        if c.get("method") != "cpu_limit":
            continue
        dep = c["deployment"]
        out[dep] = millicores_from_fraction(
            paper_limit_for(dep), float(c["cpu_limit_fraction"])
        )
    return out
