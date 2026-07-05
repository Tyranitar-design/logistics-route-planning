"""Unified decision scenario routes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.dispatch import DispatchScenario


decision_bp = Blueprint("decision", __name__)

SCENARIO_TYPES = {
    "dispatch": "调度方案",
    "network_design": "仓网设计",
    "cost_optimization": "成本优化",
    "risk_intervention": "风险干预",
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _scenario_code(scenario_type: str) -> str:
    prefix = {
        "dispatch": "DSP",
        "network_design": "NET",
        "cost_optimization": "CST",
        "risk_intervention": "RSK",
    }.get(scenario_type, "DEC")
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def _truth_contract(persisted: bool, scenario_type: str) -> Dict[str, Any]:
    return {
        "scenario_type": scenario_type,
        "business_mutation": "scenario_record_only" if persisted else "none",
        "source_tables_mutated": ["dispatch_scenarios"] if persisted else [],
        "raw_fact_mutation": False,
        "orders_or_vehicles_mutated": False,
        "requires_human_confirmation": True,
        "agent_mode": "advisory_with_human_confirmation",
        "rl_policy_mode": "shadow_rerank_only",
    }


@decision_bp.route("/scenarios", methods=["POST"])
def create_decision_scenario():
    """Create a dry-run or persisted decision scenario envelope."""
    payload = request.get_json(silent=True) or {}
    scenario_type = str(payload.get("scenario_type") or payload.get("type") or "dispatch").strip()
    if scenario_type not in SCENARIO_TYPES:
        return (
            jsonify(
                {
                    "success": False,
                    "provider_status": "degraded",
                    "fallback_reason": "UNSUPPORTED_SCENARIO_TYPE",
                    "supported_types": sorted(SCENARIO_TYPES),
                }
            ),
            400,
        )

    persist = bool(payload.get("persist"))
    scenario_code = _scenario_code(scenario_type)
    name = str(payload.get("name") or SCENARIO_TYPES[scenario_type]).strip()
    scenario_payload = payload.get("payload") or payload.get("scenario_payload") or {}
    summary = payload.get("summary") or {}
    diagnostics = payload.get("diagnostics") or {}

    persisted = False
    scenario_id = None
    if persist:
        try:
            scenario = DispatchScenario(
                scenario_code=scenario_code,
                name=name[:128],
                status="decision_preview",
                solver=str(payload.get("solver") or "decision_console")[:64],
                data_source=str(payload.get("data_source") or "decision_scenario")[:64],
                distance_source=str(payload.get("distance_source") or "not_applicable")[:128],
                provider_status=str(payload.get("provider_status") or "preview")[:32],
                authenticity_level=str(payload.get("authenticity_level") or "C")[:8],
                fallback_reason=payload.get("fallback_reason"),
                wave_filters_json=_json_dumps(payload.get("filters") or {}),
                summary_json=_json_dumps(summary),
                diagnostics_json=_json_dumps(
                    {
                        "scenario_type": scenario_type,
                        "payload": scenario_payload,
                        "diagnostics": diagnostics,
                    }
                ),
                ai_shadow_json=_json_dumps(payload.get("ai_shadow") or {}),
            )
            db.session.add(scenario)
            db.session.commit()
            scenario_id = scenario.id
            persisted = True
        except Exception as exc:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "provider_status": "degraded",
                        "fallback_reason": f"DECISION_SCENARIO_PERSIST_FAILED:{exc.__class__.__name__}",
                        "business_mutation": "none",
                    }
                ),
                500,
            )

    return jsonify(
        {
            "success": True,
            "provider": "decision_scenario",
            "provider_status": "ok",
            "fallback_reason": None,
            "scenario_type": scenario_type,
            "scenario_label": SCENARIO_TYPES[scenario_type],
            "scenario_code": scenario_code,
            "scenario_id": scenario_id,
            "persisted": persisted,
            "business_mutation": "scenario_record_only" if persisted else "none",
            "requires_confirmation": True,
            "deployable": False,
            "summary": summary,
            "diagnostics": diagnostics,
            "scenario_payload": scenario_payload,
            "truth_contract": _truth_contract(persisted, scenario_type),
        }
    )
