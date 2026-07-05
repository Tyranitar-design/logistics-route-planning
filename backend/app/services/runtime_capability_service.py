"""Runtime diagnostics for the actually running Flask process.

This module intentionally reports only capability state and safe paths. It must
never return database passwords, API keys, tokens, cookies, or license contents.
"""

from __future__ import annotations

import os
import platform
import sys
from datetime import datetime
from typing import Any, Dict

from flask import current_app


EXPECTED_ROUTES: Dict[str, str] = {
    "advanced_ml": "/api/advanced-ml/status",
    "advanced_ml_with_anomaly": "/api/advanced-ml/predict/with-anomaly",
    "enterprise_summary": "/api/analytics/enterprise-summary",
    "data_analytics_carbon": "/api/data-analytics/carbon-footprint/calculate",
    "pricing_forecast": "/api/pricing/forecast",
    "dispatch_health": "/api/dispatch/health",
    "dispatch_preview": "/api/dispatch/preview",
    "dispatch_smart": "/api/dispatch/smart",
    "optimization_capabilities": "/api/optimization/capabilities",
    "gis_provider_health": "/api/gis/provider-health",
    "agent_gateway": "/api/agent/chat",
    "decision_scenarios": "/api/decision/scenarios",
    "runtime_capabilities": "/api/runtime/capabilities",
}


def _safe_count(model: Any) -> tuple[int, str | None]:
    try:
        return int(model.query.count()), None
    except Exception as exc:  # pragma: no cover - depends on caller DB state
        return 0, exc.__class__.__name__


def database_runtime_summary() -> Dict[str, Any]:
    """Return safe database source and key business table counts."""
    from app.models import Order
    from app.models.layered_data import ShipmentFact

    uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if uri.startswith(("postgresql://", "postgresql+")):
        backend = "postgresql"
    elif uri.startswith("sqlite"):
        backend = "sqlite"
    else:
        backend = "unknown"

    shipment_facts, shipment_fact_error = _safe_count(ShipmentFact)
    legacy_orders, legacy_order_error = _safe_count(Order)
    warning = None
    if backend == "sqlite" and not shipment_facts:
        warning = "当前连接为空 SQLite 兜底库；真实 5 万 shipment_facts 需要设置 POSTGRES_DATABASE_URL 或 DATABASE_URL 后重启后端。"

    return {
        "backend": backend,
        "primary_order_source": "shipment_fact" if shipment_facts > 0 else "orders" if legacy_orders > 0 else "empty",
        "shipment_facts": shipment_facts,
        "legacy_orders": legacy_orders,
        "count_errors": {
            "shipment_facts": shipment_fact_error,
            "legacy_orders": legacy_order_error,
        },
        "warning": warning,
    }


def registered_capabilities_summary() -> Dict[str, Any]:
    """Report whether important endpoints are registered in this process."""
    route_rules = {str(rule.rule) for rule in current_app.url_map.iter_rules()}
    capabilities = {
        name: {
            "registered": route in route_rules,
            "route": route,
        }
        for name, route in EXPECTED_ROUTES.items()
    }
    missing = [name for name, item in capabilities.items() if not item["registered"]]
    return {
        "provider_status": "ok" if not missing else "degraded",
        "registered": capabilities,
        "missing": missing,
        "summary": {
            "total": len(capabilities),
            "available": len(capabilities) - len(missing),
            "missing": len(missing),
        },
    }


def interpreter_runtime_summary() -> Dict[str, Any]:
    """Return interpreter/process diagnostics that help catch stale backends."""
    app_root = os.path.abspath(os.path.join(current_app.root_path, os.pardir))
    expected_venv = os.path.normcase(os.path.join(app_root, ".venv"))
    executable = os.path.abspath(sys.executable)
    executable_norm = os.path.normcase(executable)
    using_project_venv = executable_norm.startswith(expected_venv)

    return {
        "python_executable": executable,
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "cwd": os.getcwd(),
        "app_root": app_root,
        "expected_project_venv": os.path.join(app_root, ".venv"),
        "using_project_venv": using_project_venv,
        "warning": None
        if using_project_venv
        else "当前运行解释器不在 backend\\.venv 下；若新接口 404，优先停止旧进程并用 backend\\.venv\\Scripts\\python.exe run.py 重启。",
    }


def provider_key_capabilities() -> Dict[str, Any]:
    from app.services.provider_key_resolver import (
        get_amap_keys,
        get_tianditu_keys,
        provider_key_status,
    )

    amap = provider_key_status("amap", get_amap_keys())
    tianditu = provider_key_status("tianditu", get_tianditu_keys())
    return {
        "amap": {
            **amap,
            "provider_status": "ok" if amap.get("effective_key_configured") else "degraded",
            "fallback_reason": None if amap.get("effective_key_configured") else "AMAP_KEY_MISSING",
        },
        "tianditu": {
            **tianditu,
            "provider_status": "ok" if tianditu.get("effective_key_configured") else "degraded",
            "fallback_reason": None if tianditu.get("effective_key_configured") else "TIANDITU_KEY_MISSING",
        },
        "security": {
            "api_key_values_returned": False,
        },
    }


def agent_gateway_capabilities() -> Dict[str, Any]:
    """Return safe MiniMax/agent configuration status without secret values."""
    try:
        from app.services.agent_gateway_service import get_agent_gateway_service

        return get_agent_gateway_service().key_status()
    except Exception as exc:  # pragma: no cover - defensive guard
        return {
            "provider": "minimax",
            "model": os.environ.get("MINIMAX_MODEL", "MiniMax-M3"),
            "base_url_configured": bool(os.environ.get("MINIMAX_BASE_URL", "https://vsllm.com/v1")),
            "api_key_configured": False,
            "provider_status": "degraded",
            "fallback_reason": f"AGENT_GATEWAY_STATUS_FAILED:{exc.__class__.__name__}",
            "security": {
                "api_key_value_returned": False,
            },
        }


def _build_demo_readiness(
    *,
    routes: Dict[str, Any],
    db_summary: Dict[str, Any],
    providers: Dict[str, Any],
    interpreter: Dict[str, Any],
    solver_registry: Dict[str, Any],
    agent_gateway: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a compact demo-oriented readiness summary."""
    score = 100
    blocking_issues: list[str] = []
    warnings: list[str] = []
    recommended_actions: list[str] = []

    if db_summary.get("backend") != "postgresql":
        score -= 30
        blocking_issues.append("DATABASE_NOT_POSTGRESQL")
        recommended_actions.append("设置 POSTGRES_DATABASE_URL 或 DATABASE_URL 后，用 backend\\.venv\\Scripts\\python.exe run.py 重启后端。")

    if int(db_summary.get("shipment_facts") or 0) <= 0:
        score -= 30
        blocking_issues.append("SHIPMENT_FACTS_EMPTY")
        recommended_actions.append("检查 PostgreSQL 连接串、密码和 logistics_route_system 数据库中的 shipment_facts 表。")

    missing_routes = routes.get("missing") or []
    if missing_routes:
        score -= min(30, len(missing_routes) * 4)
        blocking_issues.append("EXPECTED_ROUTES_MISSING")
        recommended_actions.append("停止占用 5000 端口的旧 run.py 进程，并用当前 backend\\.venv 解释器重启。")

    if not interpreter.get("using_project_venv"):
        score -= 12
        warnings.append("PYTHON_INTERPRETER_NOT_PROJECT_VENV")
        recommended_actions.append("确认 /api/runtime/capabilities 中 python_executable 位于 backend\\.venv。")

    if providers.get("amap", {}).get("provider_status") != "ok":
        score -= 5
        warnings.append("AMAP_KEY_MISSING")
        recommended_actions.append("如需真实道路/天气/路况演示，在后端环境变量中注入高德服务端 key 后重启。")

    if providers.get("tianditu", {}).get("provider_status") != "ok":
        score -= 3
        warnings.append("TIANDITU_KEY_MISSING")

    if agent_gateway.get("provider_status") != "ok":
        score -= 4
        warnings.append("MINIMAX_API_KEY_MISSING")
        recommended_actions.append("MiniMax-M3 Agent 可在后端设置 MINIMAX_API_KEY 后启用；不要写入前端、文档或 Git。")

    if solver_registry.get("provider_status") == "degraded":
        score -= 6
        warnings.append("OPTIONAL_SOLVER_OR_AI_CAPABILITY_DEGRADED")
        recommended_actions.append("可选 solver/AI runtime 降级不阻断演示，但优化引擎页应展示 fallback_reason。")

    score = max(0, min(100, int(round(score))))
    if blocking_issues:
        status = "blocked"
    elif score >= 88:
        status = "ready"
    else:
        status = "watch"

    recommended_actions.append("推荐前端启动：cd frontend && npm run dev -- --host 127.0.0.1 --port 5173。")

    return {
        "status": status,
        "score": score,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "recommended_actions": list(dict.fromkeys(recommended_actions)),
        "checks": {
            "postgresql_connected": db_summary.get("backend") == "postgresql",
            "shipment_facts_visible": int(db_summary.get("shipment_facts") or 0) > 0,
            "expected_routes_registered": not bool(missing_routes),
            "using_project_venv": bool(interpreter.get("using_project_venv")),
            "amap_configured": providers.get("amap", {}).get("provider_status") == "ok",
            "tianditu_configured": providers.get("tianditu", {}).get("provider_status") == "ok",
            "agent_key_configured": bool(agent_gateway.get("api_key_configured")),
            "optional_solver_probe_ok": solver_registry.get("provider_status") in {"ok", "not_checked"},
        },
        "frontend": {
            "recommended_dev_url": "http://127.0.0.1:5173",
            "recommended_command": "npm run dev -- --host 127.0.0.1 --port 5173",
        },
    }


def build_runtime_capabilities(run_solver_probe: bool = True) -> Dict[str, Any]:
    routes = registered_capabilities_summary()
    db_summary = database_runtime_summary()
    providers = provider_key_capabilities()
    interpreter = interpreter_runtime_summary()
    agent_gateway = agent_gateway_capabilities()

    solver_registry = {
        "provider_status": "not_checked",
        "summary": {},
        "capabilities": [],
    }
    if run_solver_probe:
        from app.services.optional_capability_service import get_optional_capability_service

        solver_registry = get_optional_capability_service().check(run_smoke=False)

    degraded_reasons = []
    if routes["missing"]:
        degraded_reasons.append("EXPECTED_ROUTES_MISSING")
    if interpreter["warning"]:
        degraded_reasons.append("PYTHON_INTERPRETER_NOT_PROJECT_VENV")
    if providers["amap"]["provider_status"] != "ok":
        degraded_reasons.append("AMAP_KEY_MISSING")
    if providers["tianditu"]["provider_status"] != "ok":
        degraded_reasons.append("TIANDITU_KEY_MISSING")
    if solver_registry.get("provider_status") == "degraded":
        degraded_reasons.append("OPTIONAL_SOLVER_OR_AI_CAPABILITY_DEGRADED")
    if agent_gateway.get("provider_status") != "ok":
        degraded_reasons.append("MINIMAX_API_KEY_MISSING")

    demo_readiness = _build_demo_readiness(
        routes=routes,
        db_summary=db_summary,
        providers=providers,
        interpreter=interpreter,
        solver_registry=solver_registry,
        agent_gateway=agent_gateway,
    )

    return {
        "success": True,
        "provider": "runtime_capabilities",
        "provider_status": "ok" if not degraded_reasons else "degraded",
        "fallback_reason": ";".join(degraded_reasons) if degraded_reasons else None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "interpreter": interpreter,
        "database_runtime": db_summary,
        "registered_capabilities": routes,
        "providers": providers,
        "agent_gateway": agent_gateway,
        "solver_registry": {
            "provider_status": solver_registry.get("provider_status"),
            "summary": solver_registry.get("summary", {}),
            "capabilities": solver_registry.get("capabilities", []),
            "boundary": solver_registry.get("boundary", {}),
        },
        "demo_readiness": demo_readiness,
        "platform_boundaries": {
            "agent_mode": "advisory_with_human_confirmation",
            "rl_policy_mode": "shadow_rerank_only",
            "dispatch_hard_constraints_owner": "solver_layer",
            "gis_truth_contract": "all route results must disclose distance_source/path_source/authenticity_level/fallback_reason",
        },
        "security": {
            "secret_values_returned": False,
            "api_keys_returned": False,
            "database_password_returned": False,
            "license_contents_returned": False,
        },
    }
