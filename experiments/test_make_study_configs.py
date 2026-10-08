"""
test_make_study_configs.py — Offline checks for the 2026-10-09 study
config generator. No cluster access.

Run:
    python -m pytest experiments/test_make_study_configs.py -v
"""
import sys
import types
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_study_configs as m

TEMPLATE_PATH = Path(__file__).resolve().parent / "configs" / "scenario_2_retryguard_no_topfull.yaml"


def test_counts_and_sizes():
    cfgs = m.build_configs()
    assert sum(c["set"] == "A" for c in cfgs) == 12
    assert sum(c["set"] == "B" for c in cfgs) == 18


def test_set_b_constraints_and_threshold():
    by = {c["cfg"]["log_folder"]: c["cfg"] for c in m.build_configs()}

    def limit(cfg, dep):
        return next(x["cpu_limit_millicores"] for x in cfg["scale_constraints"] if x["deployment"] == dep)

    assert limit(by["study2_s3_tf1rg1_rep1"], "checkoutservice") == 300
    assert limit(by["study2_s4a_tf1rg1_rep1"], "productcatalogservice") == 300
    assert limit(by["study2_s4b_tf1rg1_rep1"], "emailservice") == 40
    assert by["study2_s4b_tf0rg1_rep2"]["retryguard"]["reenable_rejection"] == 0.15
    assert by["study2_s4b_tf0rg1_rep2"]["topfull_rl"]["enabled"] is False
    assert by["study2_s3_tf1rg0_rep1"]["retryguard"]["enabled"] is False


def test_set_a_values():
    by = {c["cfg"]["log_folder"]: c["cfg"] for c in m.build_configs()}
    c = by["study2_s2_rr015_rgtf1_rep2"]
    assert c["retryguard"]["reenable_rejection"] == 0.15
    assert c["topfull_rl"]["enabled"] is True
    assert c["locust"]["user_counts"]["getproduct"] == 275


def test_unique_log_folders_and_blocked_order():
    cfgs = m.build_configs()
    assert len({c["cfg"]["log_folder"] for c in cfgs}) == 30
    a = sorted((c for c in cfgs if c["set"] == "A"), key=lambda c: c["order_index"])
    assert all(c["cfg"]["log_folder"].endswith("rep1") for c in a[:6])
    assert all(c["cfg"]["log_folder"].endswith("rep2") for c in a[6:])
    b = sorted((c for c in cfgs if c["set"] == "B"), key=lambda c: c["order_index"])
    assert all(c["cfg"]["log_folder"].endswith("rep1") for c in b[:9])
    assert all(c["cfg"]["log_folder"].endswith("rep2") for c in b[9:])
    assert a[5]["order_index"] < a[6]["order_index"]
    assert b[8]["order_index"] < b[9]["order_index"]


def test_scenario_identity_preserved_rows_and_paths():
    by = {c["cfg"]["log_folder"]: c for c in m.build_configs()}
    s3 = by["study2_s3_tf1rg1_rep1"]["cfg"]
    assert s3["scenario_id"] == 3
    assert s3["scenario_name"] == "targeted_bottleneck"
    assert s3["duration_seconds"] == 600
    assert s3["locust"]["user_counts"] == {
        "getproduct": 175,
        "postcheckout": 30,
        "getcart": 70,
        "postcart": 90,
        "emptycart": 5,
    }
    assert "175/30/70/90/5" in s3["description"]
    assert "checkoutservice cpu_limit_millicores=300" in s3["description"]
    assert "Unused slot" not in s3["description"]
    assert s3["paper_cpu_reconcile"] is False
    assert s3["restart_before_hold"]["deployments"] == [
        "checkoutservice",
        "recommendationservice",
    ]
    assert s3["restart_before_hold"]["settle_seconds"] == 60
    limits = {x["deployment"]: x["cpu_limit_millicores"] for x in s3["scale_constraints"]}
    assert limits["checkoutservice"] == 300
    assert limits["recommendationservice"] == 1150
    assert limits["productcatalogservice"] == 800
    assert limits["emailservice"] == 120
    assert len(s3["scale_constraints"]) == 10

    s4a = by["study2_s4a_tf0rg1_rep1"]["cfg"]
    assert s4a["scenario_id"] == 4
    assert s4a["scenario_name"] == "topology_position_A"
    assert next(
        x["cpu_limit_millicores"]
        for x in s4a["scale_constraints"]
        if x["deployment"] == "checkoutservice"
    ) == 800

    s4b = by["study2_s4b_tf1rg0_rep2"]["cfg"]
    assert s4b["scenario_name"] == "topology_position_B"
    assert s4b["condition"] == "baseline"
    assert s4b["retryguard"]["enabled"] is False
    assert s4b["retryguard"]["reenable_rejection"] == 0.15
    assert s4b["retryguard"]["retry_metric"] == "edge_rpr"
    assert s4b["topfull_rl"]["enabled"] is True

    a0 = by["study2_s2_rr010_rgtf0_rep1"]["cfg"]
    assert a0["scenario_id"] == 2
    assert a0["scenario_name"] == "sustained_overload"
    assert a0["condition"] == "retryguard"
    assert a0["topfull_rl"]["enabled"] is False
    assert a0["retryguard"]["enabled"] is True
    assert a0["retryguard"]["reenable_rejection"] == 0.10
    assert a0["duration_seconds"] == 600
    assert a0["locust"]["user_counts"]["postcheckout"] == 90
    assert "275/90/100/90/5" in a0["description"]

    a20 = by["study2_s2_rr020_rgtf1_rep1"]["cfg"]
    assert a20["retryguard"]["reenable_rejection"] == 0.20
    assert a20["topfull_rl"]["enabled"] is True
    assert a20["condition"] == "retryguard"

    for set_name, n in (("A", 6), ("B", 9)):
        block = sorted(
            (c for c in m.build_configs() if c["set"] == set_name),
            key=lambda c: c["order_index"],
        )
        assert [c["order_index"] for c in block] == list(range(1, 2 * n + 1))
        for c in block:
            name = Path(c["path"]).name
            assert name == f"{c['order_index']:02d}_{set_name}_{c['cfg']['log_folder']}.yaml"
            assert "study_2026_10_09" in str(c["path"]).replace("\\", "/")


def _import_retryguard():
    """Import retryguard the way test_retryguard.py does when kubernetes is absent."""
    if "kubernetes" not in sys.modules:
        kubernetes_stub = types.ModuleType("kubernetes")
        client_stub = types.ModuleType("kubernetes.client")
        client_rest_stub = types.ModuleType("kubernetes.client.rest")

        class _CustomObjectsApi:
            pass

        class _ConfigException(Exception):
            pass

        class _ApiException(Exception):
            def __init__(self, status=0, reason=""):
                super().__init__(reason)
                self.status = status
                self.reason = reason

        client_stub.CustomObjectsApi = _CustomObjectsApi
        client_rest_stub.ApiException = _ApiException
        config_stub = types.ModuleType("kubernetes.config")
        config_stub.ConfigException = _ConfigException
        config_stub.load_kube_config = lambda: None
        config_stub.load_incluster_config = lambda: None
        kubernetes_stub.client = client_stub
        kubernetes_stub.config = config_stub
        sys.modules["kubernetes"] = kubernetes_stub
        sys.modules["kubernetes.client"] = client_stub
        sys.modules["kubernetes.client.rest"] = client_rest_stub
        sys.modules["kubernetes.config"] = config_stub
    import retryguard
    return retryguard


def _assert_same_keys(got, expected, path):
    if isinstance(expected, dict):
        assert isinstance(got, dict), path
        missing = set(expected) - set(got)
        extra = set(got) - set(expected)
        assert not missing, (path, sorted(missing))
        allowed = {"reenable_rejection"} if path == "retryguard" else set()
        assert extra <= allowed, (path, sorted(extra))
        for key in expected:
            child = f"{path}.{key}" if path else key
            _assert_same_keys(got[key], expected[key], child)
    elif isinstance(expected, list) and expected and isinstance(expected[0], dict):
        assert isinstance(got, list) and len(got) == len(expected), path
        for i, (g, e) in enumerate(zip(got, expected)):
            _assert_same_keys(g, e, f"{path}[{i}]")


def test_configs_have_runner_keys_and_reenable_threshold():
    retryguard = _import_retryguard()
    template = yaml.safe_load(TEMPLATE_PATH.read_text(encoding="utf-8"))
    for item in m.build_configs():
        cfg = item["cfg"]
        assert set(cfg) == set(template)
        _assert_same_keys(cfg, template, "")
        assert cfg["scenario_id"]
        assert cfg["condition"] in ("baseline", "retryguard")
        assert isinstance(cfg["duration_seconds"], int)
        assert cfg["locust"]["user_counts"]
        assert cfg["locust"]["spawn_rate"] == 50
        assert cfg["locust"]["scripts"]
        assert cfg["scale_constraints"]
        assert {"attempts_on", "attempts_off", "per_try_timeout_ms"} <= set(cfg["retries"])
        rg = cfg["retryguard"]
        assert {"rejection_threshold", "sample_interval_seconds", "interval_samples"} <= set(rg)
        assert cfg["log_folder"]
        assert set(cfg["infra"]) == set(template["infra"])
        for key, value in cfg["infra"].items():
            assert value, key
        assert cfg["paper_cpu_reconcile"] is False
        assert retryguard.reenable_threshold_from_params(rg) == rg["reenable_rejection"]
