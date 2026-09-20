#!/usr/bin/env python3
"""
envoy_retry_collector.py — Scrapes Envoy sidecar stats for all Boutique services.

Usage (on master, with venv active):
    python3 envoy_retry_collector.py --params /tmp/envoy_retry_params.json

Every poll GETs http://<pod_ip>:15020/stats/prometheus and appends rows to
two shared CSVs under {record_path}/:
    service_edges.csv   — outbound upstream_rq_* per (caller, target)
    service_inbound.csv — inbound downstream_rq_* per service

Retries-per-request and offered-load deltas are derived at analysis time.

Latency columns (added 2026-09-16, additive — see
docs/superpowers/specs/2026-09-16-rho-estimator-correction.md):
Envoy's histogram stats are exposed on /stats/prometheus as three separate
series per histogram (`_bucket`, `_sum`, `_count`). Both CSVs gained two
trailing columns, `rq_time_sum_ms` / `rq_time_count`, cumulative counters
just like the existing `total`/`2xx`/etc columns — diff them the same way
(Δrq_time_sum_ms / Δrq_time_count = mean sojourn time for that tick).
`service_inbound.csv` also gained `rq_time_buckets`: a JSON object of the
cumulative histogram bucket counts keyed by `le` (ms), so
`estimate_service_mu.py` can derive a per-tick P50 by differencing buckets
between consecutive polls (more robust than the mean under long-tail
latency). Rows from before this change simply don't have these columns;
`csv.DictReader` consumers see them as a missing key, not a schema break.
Outbound: `envoy_cluster_upstream_rq_time_sum`/`_count`, keyed by the same
`cluster_name` label already used for `envoy_cluster_upstream_rq_total`.
Inbound: `envoy_http_inbound_<listener>_downstream_rq_time_sum`/`_count`,
matching the existing `envoy_http_inbound_<listener>_downstream_rq_total`
naming already parsed below.

**Verified live against this cluster on 2026-09-16** (see
docs/superpowers/specs/2026-09-16-rho-estimator-correction.md §"Live
verification follow-up"):

- INBOUND is confirmed correct as written. A live `curl .../stats/prometheus`
  against a freshly-started `frontend` pod showed
  `envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_{bucket,sum,count}`
  present (as a `# TYPE ... histogram`) even before any traffic — Istio's
  default minimal proxy-stats set includes per-listener HTTP connection-
  manager stats (low cardinality: ~1 listener/pod), so `_sum`/`_count`
  populate under real traffic exactly as this collector assumes.
- OUTBOUND (`envoy_cluster_upstream_rq_time_{sum,count}`) does **not**
  appear at all in this cluster's `/stats/prometheus` output — confirmed by
  diffing the full scrape's `# TYPE ... histogram` lines: only
  `envoy_cluster_upstream_cx_connect_ms`/`_length_ms` and the inbound HTTP
  histogram exist; there is no `envoy_cluster_upstream_rq_time` histogram
  for any outbound cluster. This is expected, documented Istio behavior,
  not a bug in this collector's regex/string match: per-cluster
  `upstream_rq_time` is a *detailed* stat Istio excludes from its default
  minimal proxy-stats set (to bound cardinality — N clusters per pod vs. 1
  listener per pod), and only appears if `proxyStatsMatcher.inclusionSuffixes`
  (or `inclusionRegexps`) includes `upstream_rq_time`, set either mesh-wide
  (`meshConfig.defaultConfig`) or per-workload (`proxy.istio.io/config`
  annotation) — either way requiring **every Boutique pod to restart** to
  pick up the new sidecar bootstrap config. That is a deliberate,
  cluster-wide infra change out of scope for this collector fix (and not
  needed today: `estimate_service_mu.py` only reads `service_inbound.csv`,
  never `service_edges.csv`'s latency columns). Net effect: on this cluster,
  `service_edges.csv`'s `rq_time_sum_ms`/`rq_time_count` will read
  structurally zero on every row, forever, until that mesh-config change is
  made — this is a **known, disclosed limitation** (the stat does not
  exist to scrape), not a transient "no traffic yet" zero. The
  outbound-parsing code below is left as-is (it is the correct Envoy naming
  convention, ready to work the moment the stat is enabled) rather than
  removed, since removing it would just delete otherwise-correct,
  forward-compatible logic for zero benefit.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #

GLOBAL_CONFIG_PATH = (
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/global_config.json"
)

# All 11 Boutique Deployments (app label == Kubernetes Service name). Every
# pod is scraped every poll — no more hardcoded caller/target shortlist.
ALL_SERVICES: List[str] = [
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

OUTBOUND_METRICS = ("total", "2xx", "4xx", "5xx", "retry", "rq_time_sum_ms", "rq_time_count")
INBOUND_METRICS = ("total", "2xx", "4xx", "5xx", "resets", "rq_time_sum_ms", "rq_time_count")

PROM_LINE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?P<labels>\{[^}]*\})?"
    r"\s+(?P<value>[0-9]+(?:\.[0-9]+)?)$"
)
CLUSTER_TARGET_RE = re.compile(
    r"^outbound\|[^|]*\|[^|]*\|"
    r"(?P<target>[\w-]+)\.default\.svc\.cluster\.local$"
)
LABEL_PAIR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"')
INBOUND_TOTAL_NAME_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq_total$"
)
INBOUND_CLASS_NAME_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq$"
)
INBOUND_RESET_NAME_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq_rx_reset$"
)
# Latency histogram mean, via _sum/_count (skip _bucket — see module docstring).
INBOUND_RQ_TIME_SUM_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq_time_sum$"
)
INBOUND_RQ_TIME_COUNT_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq_time_count$"
)
INBOUND_RQ_TIME_BUCKET_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq_time_bucket$"
)

# New trailing columns are additive — appended at the end so any consumer
# reading by column name (csv.DictReader, retryguard.py's InboundCsvTailer)
# is unaffected; a positional reader would break, but none exists today.
EDGES_CSV_COLUMNS = [
    "timestamp", "caller", "target", "total", "2xx", "4xx", "5xx", "retry",
    "rq_time_sum_ms", "rq_time_count",
]
INBOUND_CSV_COLUMNS = [
    "timestamp", "service", "total", "2xx", "4xx", "5xx", "resets",
    "rq_time_sum_ms", "rq_time_count", "rq_time_buckets",
]

DEFAULT_POLL_INTERVAL_SECONDS = 5
KUBECTL_TIMEOUT_SECONDS = 15
HTTP_TIMEOUT_SECONDS = 15
PROMETHEUS_STATS_PORT = 15020
TRANSPORT_NETWORK_PROMETHEUS = "network_prometheus"
DEFAULT_MAX_WORKERS = 4
TIER2_WARN_EVERY_POLLS = 30
NAMESPACE = "default"

CommandRunner = Callable[[List[str]], object]
HttpFetcher = Callable[[str], object]

# --------------------------------------------------------------------------- #
#  Logging / shutdown
# --------------------------------------------------------------------------- #

log = logging.getLogger("envoy_retry_collector")
_shutdown = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    _shutdown = True
    log.info("%s  SHUTDOWN  signal=%s", utc_now(), signum)


def setup_logging(record_path: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    log_file = record_path / "envoy_retry_collector.log"
    try:
        fh = logging.FileHandler(str(log_file), mode="a")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as exc:
        print(
            f"[envoy_retry_collector] WARN: cannot open {log_file}: {exc}",
            file=sys.stderr,
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tick_timestamp(interval_seconds: int, now: Optional[float] = None) -> str:
    t = time.time() if now is None else now
    aligned = int(t // interval_seconds) * interval_seconds
    return datetime.fromtimestamp(aligned, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def sleep_until_next_tick(
    interval_seconds: int,
    now: Optional[float] = None,
    sleeper: Optional[Callable[[float], None]] = None,
) -> None:
    t = time.time() if now is None else now
    next_tick = (int(t // interval_seconds) + 1) * interval_seconds
    delay = max(0.0, next_tick - t)
    (sleeper or time.sleep)(delay)


# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #

def load_params(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_record_path(global_config_path: str = GLOBAL_CONFIG_PATH) -> Path:
    with open(global_config_path, "r", encoding="utf-8") as f:
        gcfg = json.load(f)
    return Path(gcfg["record_path"])


def resolve_record_path(
    params: dict, global_config_path: str = GLOBAL_CONFIG_PATH
) -> Path:
    override = params.get("record_path")
    if override:
        return Path(override)
    return load_record_path(global_config_path)


# --------------------------------------------------------------------------- #
#  Default command runner (subprocess)
# --------------------------------------------------------------------------- #

def default_run_cmd(cmd: List[str]) -> SimpleResult:
    """Run a kubectl command; raises TimeoutError on timeout."""
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(str(exc)) from exc
    return SimpleResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


class SimpleResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# --------------------------------------------------------------------------- #
#  Pure parsing / CSV
# --------------------------------------------------------------------------- #

def parse_prom_labels(label_block: str) -> Dict[str, str]:
    text = (label_block or "").strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    return {m.group(1): m.group(2) for m in LABEL_PAIR_RE.finditer(text)}


def target_from_cluster_name(cluster_name: str) -> Optional[str]:
    m = CLUSTER_TARGET_RE.match(cluster_name or "")
    return m.group("target") if m else None


def parse_edges(stats_text: str) -> Dict[str, Dict[str, int]]:
    """
    Parse outbound cluster stats into per-target metric dicts.

    Only targets that actually appear in stats_text are included — no
    fixed target list. Every distinct <target> seen in an
    envoy_cluster_upstream_rq* line whose cluster_name is
    outbound|...||<target>.default.svc.cluster.local gets a row, with
    any metric not present for that target defaulting to 0.
    """
    edges: Dict[str, Dict[str, int]] = {}

    def bucket(target: str) -> Dict[str, int]:
        if target not in edges:
            edges[target] = {k: 0 for k in OUTBOUND_METRICS}
        return edges[target]

    for line in stats_text.splitlines():
        m = PROM_LINE_RE.match(line.strip())
        if not m:
            continue
        labels = parse_prom_labels(m.group("labels") or "")
        target = target_from_cluster_name(labels.get("cluster_name", ""))
        if not target:
            continue
        name = m.group("name")
        value = int(float(m.group("value")))
        if name == "envoy_cluster_upstream_rq_total":
            bucket(target)["total"] = value
        elif name == "envoy_cluster_upstream_rq_retry":
            bucket(target)["retry"] = value
        elif name == "envoy_cluster_upstream_rq":
            klass = labels.get("response_code_class")
            if klass in ("2xx", "4xx", "5xx"):
                bucket(target)[klass] = value
        elif name == "envoy_cluster_upstream_rq_time_sum":
            # Verified 2026-09-16: this stat does not appear on this cluster's
            # /stats/prometheus by default (Istio excludes per-cluster
            # upstream_rq_time from its minimal stat set) — see module
            # docstring. Kept for forward compatibility; will stay 0 today.
            bucket(target)["rq_time_sum_ms"] = value
        elif name == "envoy_cluster_upstream_rq_time_count":
            bucket(target)["rq_time_count"] = value
    return edges


def parse_inbound(stats_text: str) -> Dict[str, Any]:
    """
    Parse this pod's own inbound listener stats (downstream_rq_*).

    A pod can have more than one HTTP listener (e.g. separate ports);
    if multiple inbound listeners appear, keep the listener with the
    largest total (do not sum). Always returns all INBOUND_METRICS
    (missing -> 0) plus `rq_time_buckets`: a JSON object mapping histogram
    `le` labels (ms, or "+Inf") to cumulative bucket counts. Empty string
    when no bucket series were present. Used offline to derive P50/P95
    sojourn-time deltas (see estimate_service_mu.histogram_percentile).
    """
    per_listener: Dict[str, Dict[str, Any]] = {}

    def bucket(listener: str) -> Dict[str, Any]:
        if listener not in per_listener:
            row: Dict[str, Any] = {k: 0 for k in INBOUND_METRICS}
            row["rq_time_buckets"] = {}  # le -> cumulative count
            per_listener[listener] = row
        return per_listener[listener]

    for line in stats_text.splitlines():
        m = PROM_LINE_RE.match(line.strip())
        if not m:
            continue
        name = m.group("name")
        value = int(float(m.group("value")))
        labels = parse_prom_labels(m.group("labels") or "")
        total_m = INBOUND_TOTAL_NAME_RE.match(name)
        class_m = INBOUND_CLASS_NAME_RE.match(name)
        if total_m:
            bucket(total_m.group("listener"))["total"] = value
        elif class_m:
            klass = labels.get("response_code_class")
            if klass in ("2xx", "4xx", "5xx"):
                bucket(class_m.group("listener"))[klass] = value
        elif INBOUND_RESET_NAME_RE.match(name):
            reset_m = INBOUND_RESET_NAME_RE.match(name)
            bucket(reset_m.group("listener"))["resets"] = value
        elif INBOUND_RQ_TIME_SUM_RE.match(name):
            sum_m = INBOUND_RQ_TIME_SUM_RE.match(name)
            bucket(sum_m.group("listener"))["rq_time_sum_ms"] = value
        elif INBOUND_RQ_TIME_COUNT_RE.match(name):
            count_m = INBOUND_RQ_TIME_COUNT_RE.match(name)
            bucket(count_m.group("listener"))["rq_time_count"] = value
        elif INBOUND_RQ_TIME_BUCKET_RE.match(name):
            bucket_m = INBOUND_RQ_TIME_BUCKET_RE.match(name)
            le = labels.get("le")
            if le is not None:
                bucket(bucket_m.group("listener"))["rq_time_buckets"][le] = value
    if not per_listener:
        empty = {k: 0 for k in INBOUND_METRICS}
        empty["rq_time_buckets"] = ""
        return empty
    chosen = max(per_listener.values(), key=lambda d: d["total"])
    out: Dict[str, Any] = {k: chosen[k] for k in INBOUND_METRICS}
    buckets = chosen.get("rq_time_buckets") or {}
    out["rq_time_buckets"] = json.dumps(buckets, separators=(",", ":")) if buckets else ""
    return out


def sum_edge_maps(
    edge_maps: List[Dict[str, Dict[str, int]]],
) -> Dict[str, Dict[str, int]]:
    """
    Sum per-target outbound metrics across multiple pods of the same
    calling service (e.g. frontend at replicas=1..4 under its HPA, see
    the 2026-09-20 Ron-Nezer migration). Each element of `edge_maps` is
    one pod's parse_edges() output. A target missing from one pod's map
    contributes 0 for that pod, not a dropped row.
    """
    summed: Dict[str, Dict[str, int]] = {}
    for edges in edge_maps:
        for target, metrics in edges.items():
            bucket = summed.setdefault(target, {k: 0 for k in OUTBOUND_METRICS})
            for key in OUTBOUND_METRICS:
                bucket[key] += metrics.get(key, 0)
    return summed


def sum_inbound_maps(inbound_maps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sum inbound listener metrics across multiple pods of the same callee
    service. Scalar counters (total/2xx/4xx/5xx/resets/rq_time_sum_ms/
    rq_time_count) sum linearly across independent pods. rq_time_buckets
    (cumulative histogram counts keyed by `le`, JSON-encoded by
    parse_inbound()) also sum per-bucket across pods — each pod's
    buckets are independent cumulative counters over that pod's own
    requests, so bucket-for-bucket addition is the correct merge.
    """
    if not inbound_maps:
        empty: Dict[str, Any] = {k: 0 for k in INBOUND_METRICS}
        empty["rq_time_buckets"] = ""
        return empty

    totals: Dict[str, Any] = {k: 0 for k in INBOUND_METRICS}
    bucket_totals: Dict[str, int] = {}
    for inbound in inbound_maps:
        for key in INBOUND_METRICS:
            totals[key] += inbound.get(key, 0)
        buckets_raw = inbound.get("rq_time_buckets") or ""
        if buckets_raw:
            try:
                buckets = json.loads(buckets_raw) if isinstance(buckets_raw, str) else buckets_raw
            except (TypeError, ValueError, json.JSONDecodeError):
                buckets = {}
            for le, count in buckets.items():
                bucket_totals[le] = bucket_totals.get(le, 0) + int(count)

    out: Dict[str, Any] = dict(totals)
    out["rq_time_buckets"] = (
        json.dumps(bucket_totals, separators=(",", ":")) if bucket_totals else ""
    )
    return out


def write_edges_csv(
    csv_path: Path,
    timestamp: str,
    caller: str,
    edges: Dict[str, Dict[str, int]],
) -> None:
    """Append one row per (caller, target) pair; write header if new file."""
    if not edges:
        return
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EDGES_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for target in sorted(edges):
            m = edges[target]
            writer.writerow({
                "timestamp": timestamp,
                "caller": caller,
                "target": target,
                "total": m["total"],
                "2xx": m["2xx"],
                "4xx": m["4xx"],
                "5xx": m["5xx"],
                "retry": m["retry"],
                "rq_time_sum_ms": m["rq_time_sum_ms"],
                "rq_time_count": m["rq_time_count"],
            })


def write_inbound_csv(
    csv_path: Path,
    timestamp: str,
    service: str,
    inbound: Dict[str, Any],
) -> None:
    """Append one row for this service's inbound totals this poll."""
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INBOUND_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "service": service,
            "total": inbound["total"],
            "2xx": inbound["2xx"],
            "4xx": inbound["4xx"],
            "5xx": inbound["5xx"],
            "resets": inbound["resets"],
            "rq_time_sum_ms": inbound["rq_time_sum_ms"],
            "rq_time_count": inbound["rq_time_count"],
            "rq_time_buckets": inbound.get("rq_time_buckets", ""),
        })


# --------------------------------------------------------------------------- #
#  HTTP fetch + kubectl pod IP discover
# --------------------------------------------------------------------------- #

def prometheus_stats_url(pod_ip: str, port: int = PROMETHEUS_STATS_PORT) -> str:
    return f"http://{pod_ip}:{port}/stats/prometheus"


def default_fetch_url(url: str) -> SimpleResult:
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return SimpleResult(returncode=0, stdout=body, stderr="")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return SimpleResult(returncode=1, stdout="", stderr=str(exc))


def fetch_stats_text(
    pod_ip: str,
    fetch_url: Optional[HttpFetcher] = None,
) -> Optional[str]:
    fetcher = fetch_url or default_fetch_url
    url = prometheus_stats_url(pod_ip)
    try:
        result = fetcher(url)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  fetch stats %s failed: %s", utc_now(), pod_ip, exc)
        return None
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  fetch stats %s exit=%s stderr=%s",
            utc_now(),
            pod_ip,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None
    return getattr(result, "stdout", None)


def parse_ip_list(raw: Optional[str]) -> List[str]:
    """
    Split a cached pod-IP field into individual IPs. A field with no
    comma is a single IP (the shape every service had before any
    service could have more than one replica) and returns a one-element
    list; a multi-replica service (e.g. frontend under its HPA, see the
    2026-09-20 Ron-Nezer migration) is comma-joined, e.g.
    "10.0.0.1,10.0.0.2".
    """
    if not raw:
        return []
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def join_ip_list(ips: List[str]) -> str:
    return ",".join(ips)


def discover_pod_ip(
    service: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[str]:
    runner = run_cmd or default_run_cmd
    cmd = [
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"app={service}",
        "-o", "jsonpath={.items[0].status.podIP}",
    ]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  discover ip %s failed: %s", utc_now(), service, exc)
        return None
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  discover ip %s exit=%s stderr=%s",
            utc_now(),
            service,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None
    ip = (getattr(result, "stdout", "") or "").strip()
    return ip or None


def discover_pod_ips(
    service: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> List[str]:
    """
    Return every Running pod IP for `service` — not just the first.
    Needed once a service (frontend, under its 2026-09-20 HPA) can have
    more than one replica; the older discover_pod_ip() (jsonpath
    `.items[0]`) would silently scrape only 1 of up to 4 frontend
    replicas. Returns [] on any kubectl failure or no pods yet.
    """
    runner = run_cmd or default_run_cmd
    cmd = [
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"app={service}",
        "-o", 'jsonpath={range .items[*]}{.status.podIP}{"\\n"}{end}',
    ]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  discover ips %s failed: %s", utc_now(), service, exc)
        return []
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  discover ips %s exit=%s stderr=%s",
            utc_now(),
            service,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return []
    stdout = getattr(result, "stdout", "") or ""
    return [ip.strip() for ip in stdout.splitlines() if ip.strip()]


@dataclass
class ServiceScrapeResult:
    service: str
    edges: Optional[Dict[str, Dict[str, int]]] = None
    inbound: Optional[Dict[str, Any]] = None
    evict_ip: bool = False
    warning: Optional[str] = None


def should_log_tier2(service: str, poll_index: int, state: Dict[str, int]) -> bool:
    last = state.get(service)
    if last is None or poll_index - last >= TIER2_WARN_EVERY_POLLS:
        state[service] = poll_index
        return True
    return False


def scrape_one_service(
    service: str,
    pod_ip: Optional[str],
    fetch_url: HttpFetcher,
) -> ServiceScrapeResult:
    if not pod_ip:
        return ServiceScrapeResult(
            service=service, warning=f"no seeded ip for service={service}"
        )
    stats_text = fetch_stats_text(pod_ip, fetch_url=fetch_url)
    if stats_text is None:
        return ServiceScrapeResult(
            service=service,
            evict_ip=True,
            warning=f"tier2 fetch failed service={service} ip={pod_ip}",
        )
    return ServiceScrapeResult(
        service=service,
        edges=parse_edges(stats_text),
        inbound=parse_inbound(stats_text),
    )


# --------------------------------------------------------------------------- #
#  Service list / poll loop
# --------------------------------------------------------------------------- #

def resolve_services(params: dict) -> List[str]:
    override = params.get("services")
    if override:
        return list(override)
    return list(ALL_SERVICES)


def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[HttpFetcher] = None,
    ip_cache: Optional[Dict[str, str]] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    poll_index: int = 0,
    tier2_warn_state: Optional[Dict[str, int]] = None,
) -> None:
    if ip_cache is None:
        ip_cache = {}
    if tier2_warn_state is None:
        tier2_warn_state = {}
    fetcher = fetch_url or default_fetch_url
    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"
    workers = max(1, int(max_workers or DEFAULT_MAX_WORKERS))

    def _submit(service: str) -> ServiceScrapeResult:
        return scrape_one_service(service, ip_cache.get(service), fetcher)

    results: List[ServiceScrapeResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_submit, service): service for service in services}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                svc = futs[fut]
                log.warning("%s  WARNING  scrape %s raised: %s", utc_now(), svc, exc)
    _apply_scrape_results(
        results,
        ip_cache,
        edges_path,
        inbound_path,
        timestamp,
        poll_index,
        tier2_warn_state,
        run_cmd,
    )


def _apply_scrape_results(
    results: List[ServiceScrapeResult],
    ip_cache: Dict[str, str],
    edges_path: Path,
    inbound_path: Path,
    timestamp: str,
    poll_index: int,
    tier2_warn_state: Dict[str, int],
    run_cmd: Optional[CommandRunner] = None,
) -> None:
    for result in sorted(results, key=lambda r: r.service):
        if result.evict_ip:
            ip_cache.pop(result.service, None)
        if result.warning:
            if "tier2" in result.warning:
                if should_log_tier2(result.service, poll_index, tier2_warn_state):
                    log.warning("%s  WARNING  %s", utc_now(), result.warning)
                    new_ip = discover_pod_ip(result.service, run_cmd=run_cmd)
                    if new_ip:
                        ip_cache[result.service] = new_ip
            else:
                log.warning("%s  WARNING  %s", utc_now(), result.warning)
        if result.edges is not None and result.inbound is not None:
            write_edges_csv(edges_path, timestamp, result.service, result.edges)
            write_inbound_csv(inbound_path, timestamp, result.service, result.inbound)


def run_collector(
    params: dict,
    record_path: Path,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[HttpFetcher] = None,
    max_polls: Optional[int] = None,
) -> None:
    services = resolve_services(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    max_workers = int(params.get("max_workers", DEFAULT_MAX_WORKERS))
    ip_cache: Dict[str, str] = dict(params.get("pod_ips") or {})
    tier2_warn_state: Dict[str, int] = {}
    log.info(
        "%s  START  poll_interval=%ss services=%d transport=%s max_workers=%s",
        utc_now(), interval, len(services),
        TRANSPORT_NETWORK_PROMETHEUS, max_workers,
    )
    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        if max_polls is None:
            sleep_until_next_tick(interval)
            if _shutdown:
                break
        ts = tick_timestamp(interval)
        poll_once(
            record_path,
            services,
            timestamp=ts,
            run_cmd=run_cmd,
            fetch_url=fetch_url,
            ip_cache=ip_cache,
            max_workers=max_workers,
            poll_index=polls,
            tier2_warn_state=tier2_warn_state,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
    log.info("%s  EXIT", utc_now())


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envoy sidecar mesh-stats collector (Prometheus :15020)."
    )
    parser.add_argument(
        "--params",
        required=True,
        help="Path to collector params JSON "
        "(poll_interval_seconds, optional services, pod_ips, max_workers)",
    )
    args = parser.parse_args()
    params = load_params(args.params)
    record_path = resolve_record_path(params)
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    run_collector(params, record_path)


if __name__ == "__main__":
    main()
