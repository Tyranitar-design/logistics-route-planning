import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def _make_fake_gurobi_home(tmp_path: Path, license_content: str = "SECRET-LICENSE-CONTENT") -> Path:
    home = tmp_path / "Gurobi1300"
    bin_dir = home / "win64" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "gurobi_cl.exe").write_text("", encoding="utf-8")
    (bin_dir / "gurobi.lic").write_text(license_content, encoding="utf-8")
    return home


def test_gurobi_capability_never_exposes_license_contents(tmp_path, monkeypatch):
    secret = "VERY-SECRET-GUROBI-LICENSE"
    home = _make_fake_gurobi_home(tmp_path, secret)
    monkeypatch.setenv("GUROBI_HOME", str(home))
    monkeypatch.delenv("GRB_LICENSE_FILE", raising=False)
    monkeypatch.delenv("GUROBI_LICENSE_FILE", raising=False)

    import app.services.gurobi_capability_service as module

    def fake_import_module(name):
        if name == "gurobipy":
            raise ImportError("not installed")
        return importlib.import_module(name)

    monkeypatch.setattr(module.importlib, "import_module", fake_import_module)

    payload = module.GurobiCapabilityService().check(run_smoke=False)

    assert payload["checks"]["license_file_present"] is True
    assert payload["checks"]["cli_available"] is True
    assert payload["security"]["license_contents_returned"] is False
    assert payload["security"]["secret_values_returned"] is False
    assert secret not in str(payload)


def test_gurobi_capability_static_check_with_python_api(tmp_path, monkeypatch):
    home = _make_fake_gurobi_home(tmp_path)
    monkeypatch.setenv("GUROBI_HOME", str(home))
    monkeypatch.delenv("GRB_LICENSE_FILE", raising=False)
    monkeypatch.delenv("GUROBI_LICENSE_FILE", raising=False)

    import app.services.gurobi_capability_service as module

    fake_gp = SimpleNamespace(
        gurobi=SimpleNamespace(version=lambda: (13, 0, 0)),
        GRB=SimpleNamespace(MAXIMIZE=1, OPTIMAL=2),
    )
    monkeypatch.setattr(module.importlib, "import_module", lambda name: fake_gp)

    payload = module.GurobiCapabilityService().check(run_smoke=False)

    assert payload["available"] is True
    assert payload["provider_status"] == "ok"
    assert payload["checks"]["python_api_available"] is True
    assert payload["runtime"]["python_api"]["version"] == "13.0.0"
    assert payload["fallback_reason"] is None


def test_gurobi_capability_smoke_solve_can_be_mocked(tmp_path, monkeypatch):
    home = _make_fake_gurobi_home(tmp_path)
    monkeypatch.setenv("GUROBI_HOME", str(home))

    import app.services.gurobi_capability_service as module

    class FakeEnv:
        def __init__(self, empty=True):
            self.empty = empty

        def setParam(self, key, value):
            self.key = key
            self.value = value

        def start(self):
            self.started = True

        def dispose(self):
            self.disposed = True

    class FakeModel:
        def __init__(self, name, env=None):
            self.name = name
            self.env = env
            self.status = None
            self.ObjVal = None

        def addVar(self, **kwargs):
            return object()

        def setObjective(self, expr, sense):
            self.expr = expr
            self.sense = sense

        def optimize(self):
            self.status = 2
            self.ObjVal = 1.0

        def dispose(self):
            self.disposed = True

    fake_gp = SimpleNamespace(
        gurobi=SimpleNamespace(version=lambda: (13, 0, 0)),
        GRB=SimpleNamespace(MAXIMIZE=1, OPTIMAL=2),
        Env=FakeEnv,
        Model=FakeModel,
    )
    monkeypatch.setattr(module.importlib, "import_module", lambda name: fake_gp)

    payload = module.GurobiCapabilityService().check(run_smoke=True)

    assert payload["available"] is True
    assert payload["checks"]["smoke_status"] == "ok"
    assert payload["runtime"]["smoke"]["optimal"] is True
    assert payload["runtime"]["smoke"]["objective_value"] == 1.0


def test_gurobi_health_endpoint_returns_safe_payload(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeGurobiCapabilityService:
        def check(self, run_smoke=False):
            return {
                "solver": "gurobi",
                "available": False,
                "provider_status": "degraded",
                "authenticity_level": "C",
                "fallback_solver": "ortools",
                "fallback_reason": "GUROBI_PYTHON_API_UNAVAILABLE",
                "checks": {
                    "install_dir_present": True,
                    "cli_available": True,
                    "license_file_present": True,
                    "python_api_available": False,
                    "smoke_status": "skipped" if run_smoke else "not_run",
                },
                "runtime": {
                    "license_file": {"configured": True, "exists": True, "name": "gurobi.lic"},
                },
                "security": {
                    "license_contents_returned": False,
                    "secret_values_returned": False,
                },
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_gurobi_capability_service",
        lambda: FakeGurobiCapabilityService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    response = client.get("/api/optimization/gurobi/health?smoke=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["solver"] == "gurobi"
    assert payload["available"] is False
    assert payload["fallback_solver"] == "ortools"
    assert payload["checks"]["smoke_status"] == "skipped"
    assert "VERY-SECRET" not in str(payload)
