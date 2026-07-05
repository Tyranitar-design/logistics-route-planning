import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_optional_capability_service_returns_safe_runtime_contract():
    from app.services.optional_capability_service import OptionalCapabilityService

    payload = OptionalCapabilityService().check(run_smoke=False)

    assert payload["success"] is True
    assert payload["security"]["secret_values_returned"] is False
    assert payload["security"]["license_contents_returned"] is False
    assert payload["security"]["api_keys_returned"] is False
    assert payload["boundary"]["dispatch_hard_constraints_owner"] == "dispatch solver layer"
    assert payload["boundary"]["rl_policy_mode"] == "shadow_rerank_only"

    capabilities = {row["id"]: row for row in payload["capabilities"]}
    for capability_id in [
        "gurobi",
        "cplex_docplex",
        "ortools",
        "pymoo",
        "torch",
        "stable_baselines3",
        "optuna",
        "lightgbm",
        "transformers",
        "geospatial_stack",
    ]:
        assert capability_id in capabilities
        assert "available" in capabilities[capability_id]
        assert "provider_status" in capabilities[capability_id]

    assert capabilities["stable_baselines3"]["execution_mode"] == "shadow_only"
    assert "RL is advisory" in capabilities["stable_baselines3"]["boundary"]
    assert "VERY-SECRET-LICENSE" not in str(payload)


def test_optimization_capabilities_endpoint_can_be_mocked(monkeypatch):
    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeOptionalCapabilityService:
        def check(self, run_smoke=False):
            return {
                "success": True,
                "provider": "optional_runtime_capabilities",
                "provider_status": "ok",
                "authenticity_level": "B-runtime-probe",
                "summary": {
                    "total": 2,
                    "available": 2,
                    "degraded": 0,
                    "provider_status": "ok",
                    "exact_solver_available": True,
                    "multi_objective_available": True,
                    "rl_shadow_available": True,
                    "deep_learning_available": True,
                    "geospatial_available": True,
                    "by_category": {},
                },
                "capabilities": [
                    {
                        "id": "cplex_docplex",
                        "label": "CPLEX / docplex",
                        "category": "exact_solver",
                        "available": True,
                        "provider_status": "ok",
                        "fallback_reason": None,
                        "version": "cplex test",
                        "execution_mode": "bounded_exact_solver",
                    },
                    {
                        "id": "stable_baselines3",
                        "label": "Stable-Baselines3 / Gymnasium",
                        "category": "reinforcement_learning",
                        "available": True,
                        "provider_status": "ok",
                        "fallback_reason": None,
                        "version": "stable-baselines3 test",
                        "execution_mode": "shadow_only",
                        "boundary": "RL is advisory rerank/shadow only; dispatch solver owns hard constraints",
                    },
                ],
                "recommendations": ["all optional test capabilities are ready"],
                "security": {
                    "secret_values_returned": False,
                    "license_contents_returned": False,
                    "api_keys_returned": False,
                },
                "boundary": {
                    "dispatch_hard_constraints_owner": "dispatch solver layer",
                    "rl_policy_mode": "shadow_rerank_only",
                    "full_training_mode": "manual_or_background_job",
                },
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_optional_capability_service",
        lambda: FakeOptionalCapabilityService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    response = client.get("/api/optimization/capabilities?smoke=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["summary"]["available"] == 2
    assert payload["capabilities"][1]["execution_mode"] == "shadow_only"
    assert payload["security"]["license_contents_returned"] is False
