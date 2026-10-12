"""
topfull_cpu_quotas.py — Paper CPU quotas (TopFull Detector table) and
fraction helpers for S3/S4 bottlenecks.

Units are millicores, matching cAdvisor latest_usage.cpu and kubectl 'Nm'.
"""
from __future__ import annotations

from typing import Dict, List

DEFAULT_PAPER_LIMIT_MILLICORES = 1000

# Paper-C1 CPU table (locked 2026-10-13, both-off run 89). The single source
# of truth is docs/adr/0009-paper-c1-default-cpu-table.md; this dict must
# match it (test_topfull_cpu_quotas.py parses the ADR and fails on any
# difference). Edit the ADR first, then this table. All 11 services,
# request == limit.
PAPER_CPU_LIMIT_MILLICORES: Dict[str, int] = {
    "frontend": 1150,               # x4 replicas pinned (HPA), see ADR 0009
    "checkoutservice": 800,
    "recommendationservice": 1150,
    "productcatalogservice": 800,
    "cartservice": 800,
    "currencyservice": 770,
    "shippingservice": 770,
    "redis-cart": 540,
    "emailservice": 120,
    "paymentservice": 155,
    "adservice": 1150,
}

# Ron-config regime: request == limit for every service (unlike the old
# KAIST-paper-quota table, which halved request relative to limit for
# some services). paper_request_for() falls back to paper_limit_for()
# below when a service has no explicit override here — leave this dict
# empty rather than duplicating PAPER_CPU_LIMIT_MILLICORES.
PAPER_CPU_REQUEST_MILLICORES: Dict[str, int] = {}

RECONCILE_SERVICES = (
    "frontend",
    "checkoutservice",
    "recommendationservice",
    "productcatalogservice",
    "cartservice",
    "currencyservice",
    "shippingservice",
    "redis-cart",
    "emailservice",
    "paymentservice",
    "adservice",
)

# redis-cart's pod template container is named "redis", not "server"
# (confirmed live 2026-09-20: `kubectl get deploy redis-cart -o
# jsonpath={.spec.template.spec.containers[0].name}` -> "redis"). Every
# other of the 11 Boutique Deployments uses "server".
CONTAINER_NAME_OVERRIDES: Dict[str, str] = {
    "redis-cart": "redis",
}

# Ron-config regime: both of these services' replica counts are HPA-managed
# (frontend since the 2026-09-20 base migration; productcatalogservice since
# the 2026-09-21 methodology rework, ADR-0005) — a fixed `replicas`
# scale_constraint on either would fight the autoscaler.
HPA_MANAGED_DEPLOYMENTS = frozenset({"frontend", "productcatalogservice"})


def container_name_for(service: str) -> str:
    return CONTAINER_NAME_OVERRIDES.get(service, "server")


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


def validate_request_fraction(request_fraction: float) -> float:
    """cpu_request_fraction must be in (0, 1]. Default 1.0 keeps request == limit."""
    try:
        fraction = float(request_fraction)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"cpu_request_fraction must be a number in (0, 1], got {request_fraction!r}"
        ) from exc
    if fraction <= 0 or fraction > 1:
        raise ValueError(
            f"cpu_request_fraction must be in (0, 1], got {request_fraction}"
        )
    return fraction


def paper_request_for(service: str, request_fraction: float = 1.0) -> int:
    fraction = validate_request_fraction(request_fraction)
    if service in PAPER_CPU_REQUEST_MILLICORES:
        base = int(PAPER_CPU_REQUEST_MILLICORES[service])
    else:
        base = paper_limit_for(service)
    return int(base * fraction)


def millicores_from_fraction(paper_limit: int, fraction: float) -> int:
    if fraction <= 0 or fraction > 1:
        raise ValueError(f"cpu_limit_fraction must be in (0, 1], got {fraction}")
    return int(paper_limit * fraction)


def cpu_limit_millicores_for(constraint: dict) -> int:
    """
    Resolve a `method: "cpu_limit"` constraint's absolute millicore value.

    Exactly one of `cpu_limit_millicores` (new, absolute — ADR-0006) or
    `cpu_limit_fraction` (legacy, relative to paper_limit_for(deployment))
    must be present.
    """
    has_millicores = "cpu_limit_millicores" in constraint
    has_fraction = "cpu_limit_fraction" in constraint
    if has_millicores and has_fraction:
        raise ValueError(
            "cpu_limit constraint cannot set both cpu_limit_millicores and "
            "cpu_limit_fraction - pick one"
        )
    if has_millicores:
        return int(constraint["cpu_limit_millicores"])
    if has_fraction:
        dep = constraint["deployment"]
        return millicores_from_fraction(
            paper_limit_for(dep), float(constraint["cpu_limit_fraction"])
        )
    raise ValueError(
        "cpu_limit constraint requires either cpu_limit_millicores or "
        "cpu_limit_fraction"
    )


def kubectl_cpu_quantity(millicores: int) -> str:
    return f"{int(millicores)}m"


def validate_scale_constraints(constraints: List[dict]) -> None:
    known = set(PAPER_CPU_LIMIT_MILLICORES) | set(RECONCILE_SERVICES)
    for c in constraints or []:
        method = c.get("method")
        if method == "replicas" and c.get("deployment") in HPA_MANAGED_DEPLOYMENTS:
            raise ValueError(
                f"scale_constraints cannot set replicas on {c['deployment']} - "
                "its replica count is HPA-managed; a fixed replicas constraint "
                "would fight the autoscaler"
            )
        if method != "cpu_limit":
            continue
        if "cpu_limit" in c:
            raise ValueError(
                "scale_constraints cpu_limit is removed; use cpu_limit_fraction "
                "or cpu_limit_millicores"
            )
        dep = c.get("deployment")
        if dep not in known:
            raise ValueError(f"no paper quota for deployment {dep}")
        cpu_limit_millicores_for(c)


def cpu_limit_mismatches(
    live: Dict[str, dict], expected: Dict[str, int]
) -> List[str]:
    """
    Compare live Deployment CPU (capture_service_capacity shape) with the
    expected per-service millicores. Request must equal limit as well.
    Returns one message per problem; an empty list means the VMs match.
    """
    problems: List[str] = []
    for svc, want in sorted(expected.items()):
        got = live.get(svc)
        if got is None:
            problems.append(f"{svc}: no live Deployment found")
            continue
        lim = got.get("cpu_limit_millicores")
        req = got.get("cpu_request_millicores")
        if lim != want:
            problems.append(f"{svc}: live limit {lim}m, expected {want}m")
        if req != want:
            problems.append(f"{svc}: live request {req}m, expected {want}m")
    return problems


def effective_cpu_quotas(constraints: List[dict]) -> Dict[str, int]:
    out = {s: paper_limit_for(s) for s in RECONCILE_SERVICES}
    for name, lim in PAPER_CPU_LIMIT_MILLICORES.items():
        out[name] = lim
    for c in constraints or []:
        if c.get("method") != "cpu_limit":
            continue
        out[c["deployment"]] = cpu_limit_millicores_for(c)
    return out
