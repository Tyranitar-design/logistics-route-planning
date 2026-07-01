"""
Gurobi capability checks.

This module only checks installation/runtime state. It never reads or returns
license contents.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_GUROBI_HOME = Path(r"D:\Gurobi1300")
DEFAULT_LICENSE_PATH = DEFAULT_GUROBI_HOME / "win64" / "bin" / "gurobi.lic"


def _first_env(*names: str) -> tuple[Optional[str], Optional[str]]:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return name, value.strip()
    return None, None


def _safe_path_state(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {
            "configured": False,
            "exists": False,
            "name": None,
            "suffix": None,
        }

    return {
        "configured": True,
        "exists": path.exists(),
        "name": path.name,
        "suffix": path.suffix,
    }


@dataclass
class GurobiCapabilityService:
    """Resolve and probe the local Gurobi runtime safely."""

    default_home: Path = DEFAULT_GUROBI_HOME
    default_license_path: Path = DEFAULT_LICENSE_PATH

    def resolve_home(self) -> tuple[str, Path]:
        source, raw_path = _first_env("GUROBI_HOME")
        if raw_path:
            return source or "GUROBI_HOME", Path(raw_path)
        return "default", self.default_home

    def resolve_license_path(self, home: Optional[Path] = None) -> tuple[str, Path]:
        source, raw_path = _first_env("GRB_LICENSE_FILE", "GUROBI_LICENSE_FILE")
        if raw_path:
            return source or "GRB_LICENSE_FILE", Path(raw_path)

        base = home if home is not None else self.default_home
        return "default", base / "win64" / "bin" / "gurobi.lic"

    def _check_python_api(self) -> Dict[str, Any]:
        try:
            module = importlib.import_module("gurobipy")
        except Exception as exc:
            return {
                "available": False,
                "version": None,
                "error_type": exc.__class__.__name__,
            }

        version = getattr(module, "gurobi", None)
        if version is not None and hasattr(version, "version"):
            try:
                version = ".".join(str(part) for part in version.version())
            except Exception:
                version = None
        else:
            version = getattr(module, "__version__", None)

        return {
            "available": True,
            "version": version,
            "error_type": None,
        }

    def _run_smoke_solve(self) -> Dict[str, Any]:
        try:
            gp = importlib.import_module("gurobipy")
            grb = getattr(gp, "GRB")

            env = gp.Env(empty=True)
            env.setParam("OutputFlag", 0)
            env.start()

            model = gp.Model("logistics_gurobi_health_smoke", env=env)
            x = model.addVar(lb=0.0, ub=1.0, name="x")
            model.setObjective(x, grb.MAXIMIZE)
            model.optimize()

            status = getattr(model, "status", getattr(model, "Status", None))
            optimal_status = getattr(grb, "OPTIMAL", 2)
            objective = getattr(model, "ObjVal", None)

            try:
                model.dispose()
            except Exception:
                pass
            try:
                env.dispose()
            except Exception:
                pass

            if status == optimal_status:
                return {
                    "status": "ok",
                    "optimal": True,
                    "model_status": status,
                    "objective_value": float(objective) if objective is not None else None,
                    "error_type": None,
                }

            return {
                "status": "failed",
                "optimal": False,
                "model_status": status,
                "objective_value": float(objective) if objective is not None else None,
                "error_type": "NonOptimalStatus",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "optimal": False,
                "model_status": None,
                "objective_value": None,
                "error_type": exc.__class__.__name__,
            }

    def check(self, run_smoke: bool = False) -> Dict[str, Any]:
        home_source, home = self.resolve_home()
        license_source, license_path = self.resolve_license_path(home)
        bin_dir = home / "win64" / "bin"
        cli_path = bin_dir / "gurobi_cl.exe"

        python_api = self._check_python_api()
        smoke = {
            "status": "not_run",
            "optimal": None,
            "model_status": None,
            "objective_value": None,
            "error_type": None,
        }

        if run_smoke:
            if python_api["available"]:
                smoke = self._run_smoke_solve()
            else:
                smoke = {
                    "status": "skipped",
                    "optimal": False,
                    "model_status": None,
                    "objective_value": None,
                    "error_type": "PythonApiUnavailable",
                }

        install_dir_present = home.exists()
        cli_available = cli_path.exists()
        license_file_present = license_path.exists()
        python_api_available = bool(python_api["available"])

        if run_smoke:
            available = smoke["status"] == "ok"
        else:
            available = python_api_available and license_file_present

        fallback_reason = None
        if not available:
            if not python_api_available:
                fallback_reason = "GUROBI_PYTHON_API_UNAVAILABLE"
            elif run_smoke and smoke["status"] != "ok":
                fallback_reason = "GUROBI_SMOKE_SOLVE_FAILED"
            elif not license_file_present:
                fallback_reason = "GUROBI_LICENSE_FILE_MISSING"
            elif not cli_available:
                fallback_reason = "GUROBI_CLI_MISSING"
            elif not install_dir_present:
                fallback_reason = "GUROBI_HOME_MISSING"
            else:
                fallback_reason = "GUROBI_UNAVAILABLE"

        provider_status = "ok" if available else "degraded"

        return {
            "solver": "gurobi",
            "available": available,
            "provider_status": provider_status,
            "authenticity_level": "A" if available else "C",
            "fallback_solver": None if available else "ortools",
            "fallback_reason": fallback_reason,
            "checks": {
                "install_dir_present": install_dir_present,
                "cli_available": cli_available,
                "license_file_present": license_file_present,
                "python_api_available": python_api_available,
                "smoke_status": smoke["status"],
            },
            "runtime": {
                "home_source": home_source,
                "home": _safe_path_state(home),
                "license_source": license_source,
                "license_file": _safe_path_state(license_path),
                "cli": _safe_path_state(cli_path),
                "python_api": python_api,
                "smoke": smoke,
            },
            "security": {
                "license_contents_returned": False,
                "secret_values_returned": False,
            },
        }

    def is_available(self, require_smoke: bool = False) -> bool:
        return bool(self.check(run_smoke=require_smoke)["available"])


_service: Optional[GurobiCapabilityService] = None


def get_gurobi_capability_service() -> GurobiCapabilityService:
    global _service
    if _service is None:
        _service = GurobiCapabilityService()
    return _service
