"""Safe optional runtime capability probes for optimization and AI features.

The service reports only installation/runtime status. It never reads or returns
API keys, database passwords, SSH material, or solver license contents.
"""

from __future__ import annotations

import importlib
import importlib.metadata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from app.services.gurobi_capability_service import get_gurobi_capability_service


@dataclass(frozen=True)
class RuntimeProbe:
    id: str
    label: str
    category: str
    role: str
    modules: tuple[str, ...]
    distributions: tuple[str, ...] = ()
    fallback_to: Optional[str] = None
    execution_mode: str = "optional"
    boundary: str = "optional capability; normal Flask startup must not depend on it"


RUNTIME_PROBES: tuple[RuntimeProbe, ...] = (
    RuntimeProbe(
        id="cplex_docplex",
        label="CPLEX / docplex",
        category="exact_solver",
        role="bounded MILP readiness for assignment, network design, and future CPLEX branches",
        modules=("cplex", "docplex.mp.model"),
        distributions=("cplex", "docplex"),
        fallback_to="gurobi_or_ortools",
        execution_mode="bounded_exact_solver",
        boundary="optional exact solver; do not send full 50k shipment waves into MILP",
    ),
    RuntimeProbe(
        id="ortools",
        label="Google OR-Tools",
        category="heuristic_solver",
        role="constraint-safe routing and assignment heuristic baseline",
        modules=("ortools.constraint_solver.pywrapcp",),
        distributions=("ortools",),
        fallback_to="balanced_dispatch",
        execution_mode="interactive_solver",
    ),
    RuntimeProbe(
        id="pymoo",
        label="pymoo NSGA-II/III",
        category="multi_objective",
        role="Pareto multi-objective scenario comparison",
        modules=("pymoo", "pymoo.algorithms.moo.nsga2", "pymoo.algorithms.moo.nsga3"),
        distributions=("pymoo",),
        fallback_to="weighted_solver_comparison",
        execution_mode="bounded_shadow_or_manual",
    ),
    RuntimeProbe(
        id="torch",
        label="PyTorch",
        category="deep_learning",
        role="LSTM/Transformer/readiness jobs and neural policy experiments",
        modules=("torch",),
        distributions=("torch",),
        fallback_to="tabular_baseline",
        execution_mode="background_or_shadow",
        boundary="deep models must use training-window readiness gates before being marked production-ready",
    ),
    RuntimeProbe(
        id="stable_baselines3",
        label="Stable-Baselines3 / Gymnasium",
        category="reinforcement_learning",
        role="PPO/DQN/Fitted-Q style dispatch policy shadow training and evaluation",
        modules=("stable_baselines3", "gymnasium"),
        distributions=("stable-baselines3", "gymnasium"),
        fallback_to="solver_only",
        execution_mode="shadow_only",
        boundary="RL is advisory rerank/shadow only; dispatch solver owns hard constraints",
    ),
    RuntimeProbe(
        id="optuna",
        label="Optuna",
        category="tuning",
        role="solver and model hyperparameter tuning jobs",
        modules=("optuna",),
        distributions=("optuna",),
        fallback_to="default_parameters",
        execution_mode="manual_background",
    ),
    RuntimeProbe(
        id="lightgbm",
        label="LightGBM",
        category="forecasting",
        role="tabular ETA, delay, cost, and capacity-gap baseline upgrade",
        modules=("lightgbm",),
        distributions=("lightgbm",),
        fallback_to="sklearn_or_numpy_baseline",
        execution_mode="background_or_interactive_small",
    ),
    RuntimeProbe(
        id="transformers",
        label="Transformers",
        category="deep_learning",
        role="future TransformerEncoder/TFT-style sequence model experiments",
        modules=("transformers",),
        distributions=("transformers",),
        fallback_to="lstm_gru_or_baseline",
        execution_mode="background_shadow",
        boundary="requires real time-axis sufficiency before claiming deep time-series production readiness",
    ),
    RuntimeProbe(
        id="geospatial_stack",
        label="GeoPandas / Shapely / PyProj / Geopy",
        category="geospatial",
        role="network audit, spatial enrichment, coordinate validation, and local-provider comparison",
        modules=("geopandas", "shapely", "pyproj", "geopy"),
        distributions=("geopandas", "shapely", "pyproj", "geopy"),
        fallback_to="postgis_sql_or_haversine",
        execution_mode="interactive_audit_or_batch",
    ),
)


def _version_for(distributions: Iterable[str], fallback_module: Optional[Any] = None) -> Optional[str]:
    versions: List[str] = []
    for dist in distributions:
        try:
            versions.append(f"{dist} {importlib.metadata.version(dist)}")
        except importlib.metadata.PackageNotFoundError:
            continue
        except Exception:
            continue
    if versions:
        return ", ".join(versions)

    module_version = getattr(fallback_module, "__version__", None) if fallback_module is not None else None
    return str(module_version) if module_version else None


def _probe_imports(probe: RuntimeProbe) -> Dict[str, Any]:
    imported: Dict[str, bool] = {}
    errors: Dict[str, str] = {}
    first_module = None

    for module_name in probe.modules:
        try:
            module = importlib.import_module(module_name)
            imported[module_name] = True
            if first_module is None:
                first_module = module
        except Exception as exc:
            imported[module_name] = False
            errors[module_name] = exc.__class__.__name__

    available = all(imported.values()) if imported else False
    fallback_reason = None if available else f"{probe.id.upper()}_UNAVAILABLE"

    return {
        "id": probe.id,
        "label": probe.label,
        "category": probe.category,
        "role": probe.role,
        "available": available,
        "provider_status": "ok" if available else "degraded",
        "fallback_reason": fallback_reason,
        "fallback_to": None if available else probe.fallback_to,
        "version": _version_for(probe.distributions, first_module),
        "execution_mode": probe.execution_mode,
        "boundary": probe.boundary,
        "checks": {
            "imports": imported,
            "errors": errors,
        },
    }


class OptionalCapabilityService:
    """Aggregate safe optional capability state for control-tower use."""

    def check(self, run_smoke: bool = False) -> Dict[str, Any]:
        capabilities = [self._gurobi_row(run_smoke=run_smoke)]
        capabilities.extend(_probe_imports(probe) for probe in RUNTIME_PROBES)

        available_count = sum(1 for row in capabilities if row["available"])
        degraded = [row for row in capabilities if not row["available"]]
        categories = sorted({row["category"] for row in capabilities})
        by_category = {
            category: {
                "available": sum(1 for row in capabilities if row["category"] == category and row["available"]),
                "total": sum(1 for row in capabilities if row["category"] == category),
            }
            for category in categories
        }

        summary = {
            "total": len(capabilities),
            "available": available_count,
            "degraded": len(degraded),
            "provider_status": "ok" if not degraded else "degraded",
            "exact_solver_available": any(
                row["available"] and row["category"] == "exact_solver" for row in capabilities
            ),
            "multi_objective_available": any(
                row["available"] and row["category"] == "multi_objective" for row in capabilities
            ),
            "rl_shadow_available": any(
                row["available"] and row["category"] == "reinforcement_learning" for row in capabilities
            ),
            "deep_learning_available": any(
                row["available"] and row["category"] == "deep_learning" for row in capabilities
            ),
            "geospatial_available": any(
                row["available"] and row["category"] == "geospatial" for row in capabilities
            ),
            "by_category": by_category,
        }

        recommendations = [
            f"{row['label']} degraded: {row['fallback_reason']} -> {row.get('fallback_to') or 'no fallback'}"
            for row in degraded[:6]
        ]
        if not recommendations:
            recommendations = [
                "Optional optimization, AI, RL, and geospatial runtimes are importable; keep heavy training and RL in manual/background shadow mode.",
            ]

        return {
            "success": True,
            "provider": "optional_runtime_capabilities",
            "provider_status": summary["provider_status"],
            "authenticity_level": "B-runtime-probe" if not degraded else "C-runtime-degraded",
            "summary": summary,
            "capabilities": capabilities,
            "recommendations": recommendations,
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

    def _gurobi_row(self, run_smoke: bool = False) -> Dict[str, Any]:
        status = get_gurobi_capability_service().check(run_smoke=run_smoke)
        return {
            "id": "gurobi",
            "label": "Gurobi",
            "category": "exact_solver",
            "role": "bounded MILP/CVRP/network design exact solver",
            "available": bool(status.get("available")),
            "provider_status": status.get("provider_status", "degraded"),
            "fallback_reason": status.get("fallback_reason"),
            "fallback_to": status.get("fallback_solver"),
            "version": (status.get("runtime") or {}).get("python_api", {}).get("version"),
            "execution_mode": "bounded_exact_solver",
            "boundary": "optional exact solver; license contents are never returned",
            "checks": status.get("checks", {}),
        }


_service: Optional[OptionalCapabilityService] = None


def get_optional_capability_service() -> OptionalCapabilityService:
    global _service
    if _service is None:
        _service = OptionalCapabilityService()
    return _service
