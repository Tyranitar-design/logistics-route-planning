import importlib
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _build_app(monkeypatch, clear_minimax_key=True):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")
    if clear_minimax_key:
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app
    from app.models import db

    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def test_runtime_capabilities_reports_registered_routes(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.get("/api/runtime/capabilities?solver_probe=0")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["registered_capabilities"]["registered"]["advanced_ml"]["registered"] is True
    assert payload["registered_capabilities"]["registered"]["enterprise_summary"]["registered"] is True
    assert payload["registered_capabilities"]["registered"]["agent_gateway"]["registered"] is True
    assert payload["registered_capabilities"]["registered"]["gis_provider_health"]["registered"] is True
    assert payload["demo_readiness"]["status"] in {"ready", "watch", "blocked"}
    assert isinstance(payload["demo_readiness"]["score"], int)
    assert "recommended_dev_url" in payload["demo_readiness"]["frontend"]
    assert payload["agent_gateway"]["api_key_configured"] is False
    assert payload["security"]["api_keys_returned"] is False
    assert "test-secret-key" not in str(payload)


def test_ready_includes_registered_capability_summary(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.get("/api/ready")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert "registered_capabilities" in payload
    assert payload["registered_capabilities"]["registered"]["advanced_ml"]["registered"] is True
    assert payload["registered_capabilities"]["registered"]["runtime_capabilities"]["registered"] is True


def test_agent_chat_without_key_returns_degraded_200(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/agent/chat",
        json={
            "agent_role": "智能调度专家",
            "question": "请解释今天的调度健康状态",
            "task_context": {"data_source": "shipment_fact", "api_key": "must-not-leak"},
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is False
    assert payload["provider_status"] == "degraded"
    assert payload["fallback_reason"] == "MINIMAX_API_KEY_MISSING"
    assert "must-not-leak" not in str(payload)
    assert payload["security"]["api_key_value_returned"] is False


def test_agent_chat_with_fake_openai_client_does_not_expose_key(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "test-secret-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://example.invalid/v1")
    app = _build_app(monkeypatch, clear_minimax_key=False)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "<think>internal reasoning</think>\n建议先查看 /api/runtime/capabilities。"}}],
                "usage": {"total_tokens": 12},
            }

    class FakeClient:
        calls = []

        @classmethod
        def post(cls, *args, **kwargs):
            cls.calls.append({"args": args, "kwargs": kwargs})
            return FakeResponse()

    from app.services import agent_gateway_service

    agent_gateway_service._service = agent_gateway_service.AgentGatewayService(http_client=FakeClient)
    client = app.test_client()
    response = client.post(
        "/api/agent/chat",
        json={"agent_role": "data_quality_expert", "question": "如何审计 shipment_facts 时间轴？"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["provider_status"] == "ok"
    assert payload["answer"].startswith("建议先查看")
    assert "<think>" not in payload["answer"]
    assert "internal reasoning" not in payload["answer"]
    assert "test-secret-key" not in str(payload)
    assert FakeClient.calls[0]["kwargs"]["headers"]["Authorization"] == "Bearer test-secret-key"


def test_agent_tool_preview_is_read_only(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/agent/tools/preview",
        json={"tool_name": "dispatch_preview", "parameters": {"persist": True}},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["preview"]["read_only"] is True
    assert payload["preview"]["parameters"]["persist"] is False
    assert payload["truth_contract"]["business_mutation"] == "none"


def test_gis_provider_health_returns_safe_component_status(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.get("/api/gis/provider-health")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert set(["amap", "tianditu", "postgis", "local_graph"]).issubset(payload["components"])
    assert payload["components"]["amap"]["keys"]["effective_key_configured"] is False
    assert payload["components"]["tianditu"]["keys"]["effective_key_configured"] is False
    assert payload["security"]["api_keys_returned"] is False
    assert "test-secret-key" not in str(payload)


def test_decision_scenario_dry_run_does_not_persist(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    with app.app_context():
        from app.models.dispatch import DispatchScenario

        before = DispatchScenario.query.count()

    response = client.post(
        "/api/decision/scenarios",
        json={
            "scenario_type": "network_design",
            "name": "仓网设计 dry run",
            "persist": False,
            "payload": {"candidate_limit": 4},
        },
    )
    payload = response.get_json()

    with app.app_context():
        from app.models.dispatch import DispatchScenario

        after = DispatchScenario.query.count()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["persisted"] is False
    assert payload["business_mutation"] == "none"
    assert payload["truth_contract"]["raw_fact_mutation"] is False
    assert after == before


def test_decision_scenario_can_persist_scenario_record_only(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/decision/scenarios",
        json={
            "scenario_type": "dispatch",
            "name": "调度方案记录",
            "persist": True,
            "summary": {"orders": 10},
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["persisted"] is True
    assert payload["business_mutation"] == "scenario_record_only"
    assert payload["truth_contract"]["source_tables_mutated"] == ["dispatch_scenarios"]


def test_enterprise_smoke_harness_classifies_auth_and_missing_routes():
    from scripts.enterprise_smoke_harness import _compact_response

    auth = _compact_response("/api/dispatch/health", 401, {"msg": "Missing Authorization Header"}, 0.01)
    missing = _compact_response("/api/not-registered", 404, {"error": "not found"}, 0.01)
    ok = _compact_response(
        "/api/runtime/capabilities?solver_probe=0",
        200,
        {
            "success": True,
            "database_runtime": {"backend": "postgresql", "shipment_facts": 50000},
            "demo_readiness": {"status": "ready", "score": 94},
        },
        0.01,
    )

    assert auth["classification"] == "auth_required"
    assert auth["route_present"] is True
    assert missing["classification"] == "route_missing"
    assert missing["route_present"] is False
    assert ok["classification"] == "ok"
    assert ok["demo_readiness_status"] == "ready"
    assert ok["shipment_facts"] == 50000
