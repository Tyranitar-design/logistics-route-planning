#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能调度路由
"""

import threading
from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.dispatch_service import get_dispatch_service
from app.services.smart_dispatch_service import get_smart_dispatch_service
from app.services.dispatch_orchestration_service import get_dispatch_orchestration_service
from app.services.dispatch_learning_dataset_service import get_dispatch_learning_dataset_service
from app.utils.rate_limiter import rate_limit, RateLimits

dispatch_bp = Blueprint('dispatch', __name__)
_POLICY_JOBS = {}
_POLICY_JOB_LOCK = threading.Lock()


SMART_DISPATCH_TRUTH_CONTRACT = {
    'data_source': 'postgres_orders_vehicles_nodes',
    'distance_source': 'haversine_legacy_dispatch',
    'path_source': 'dispatch_assignment_sequence',
    'authenticity_level': 'C',
    'fallback_reason': (
        'smart_dispatch_legacy_service_uses_haversine_distance_matrix; '
        'not_yet_precise_road_distance_or_turn_by_turn_path'
    ),
}


def _current_user_id():
    try:
        identity = get_jwt_identity()
        return int(identity) if identity is not None else None
    except Exception:
        return None


def _coerce_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _runtime_profile(payload=None, default="interactive"):
    value = (payload or {}).get("runtime_profile") or request.args.get("runtime_profile") or default
    return "full" if str(value).lower() == "full" else "interactive"


def _apply_shadow_runtime_profile(payload=None, default="interactive"):
    payload = dict(payload or {})
    profile = _runtime_profile(payload, default=default)
    payload["runtime_profile"] = profile
    if profile == "interactive":
        payload["scenario_limit"] = max(1, min(1, _coerce_int(payload.get("scenario_limit"), 1)))
        payload["row_limit"] = max(1, min(20, _coerce_int(payload.get("row_limit"), 20)))
        payload["anomaly_source_limit"] = max(1, min(2000, _coerce_int(payload.get("anomaly_source_limit"), 2000)))
        payload["anomaly_limit"] = max(1, min(40, _coerce_int(payload.get("anomaly_limit"), 20)))
        if payload.get("top_k") is not None:
            payload["top_k"] = max(1, min(5, _coerce_int(payload.get("top_k"), 3)))
        payload["use_ml"] = False
    else:
        payload["scenario_limit"] = max(1, _coerce_int(payload.get("scenario_limit"), 50))
        payload["row_limit"] = max(1, _coerce_int(payload.get("row_limit"), 200))
        payload["anomaly_source_limit"] = max(1, _coerce_int(payload.get("anomaly_source_limit"), 50000))
        payload["anomaly_limit"] = max(1, _coerce_int(payload.get("anomaly_limit"), 80))
        payload["top_k"] = max(1, _coerce_int(payload.get("top_k"), 10))
        payload["use_ml"] = _coerce_bool(payload.get("use_ml"), default=False)
    return payload


def _attach_shadow_runtime(result, payload):
    if isinstance(result, dict):
        result.setdefault("runtime_profile", payload.get("runtime_profile", "interactive"))
        result.setdefault(
            "runtime_limits",
            {
                "scenario_limit": payload.get("scenario_limit"),
                "row_limit": payload.get("row_limit"),
                "anomaly_source_limit": payload.get("anomaly_source_limit"),
                "anomaly_limit": payload.get("anomaly_limit"),
                "top_k": payload.get("top_k"),
                "use_ml": payload.get("use_ml"),
            },
        )
    return result


def _degraded_shadow_payload(endpoint, payload, exc):
    current_app.logger.exception("optional dispatch shadow endpoint degraded: %s", endpoint)
    return {
        "success": False,
        "provider_status": "degraded",
        "fallback_reason": f"{endpoint.upper()}_DEGRADED:{type(exc).__name__}",
        "runtime_profile": payload.get("runtime_profile", "interactive"),
        "runtime_limits": {
            "scenario_limit": payload.get("scenario_limit"),
            "row_limit": payload.get("row_limit"),
            "anomaly_source_limit": payload.get("anomaly_source_limit"),
            "anomaly_limit": payload.get("anomaly_limit"),
            "top_k": payload.get("top_k"),
            "use_ml": payload.get("use_ml"),
        },
        "summary": {},
        "recommendations": [
            "高级 AI shadow 已降级；请先确认 dispatch_scenarios/assignments 存在，再手动运行 full 模式。",
        ],
        "truth_contract": {
            "mutation": "none",
            "deployable": False,
            "shadow_boundary": "optional shadow endpoint degraded without mutating business data",
        },
    }


def _shadow_response(endpoint, raw_payload, runner):
    payload = _apply_shadow_runtime_profile(raw_payload)
    try:
        result = runner(payload)
        return jsonify(_attach_shadow_runtime(result, payload)), 200
    except Exception as exc:
        return jsonify(_degraded_shadow_payload(endpoint, payload, exc)), 200


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _policy_job_summary(job):
    return {
        'job_id': job.get('job_id'),
        'status': job.get('status'),
        'policy_family': job.get('policy_family'),
        'runtime_profile': job.get('runtime_profile'),
        'provider_status': job.get('provider_status'),
        'fallback_reason': job.get('fallback_reason'),
        'progress': job.get('progress', 0.0),
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
        'completed_at': job.get('completed_at'),
    }


def _update_policy_job(job_id, **updates):
    with _POLICY_JOB_LOCK:
        job = _POLICY_JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job['updated_at'] = _utc_now()


def _run_policy_job(job_id, payload, app):
    def run_inside_context():
        _update_policy_job(job_id, status='running', provider_status='running', progress=0.1)
        try:
            family = str(payload.get('policy_family') or payload.get('model_family') or 'fitted_q').lower()
            service = get_dispatch_learning_dataset_service()
            if family in {'dqn', 'dql', 'ppo', 'rl_shadow', 'q_shadow'}:
                result = service.run_rl_shadow_runner(payload)
            elif family in {'fitted_q', 'fitted-q', 'fitted_q_shadow'}:
                result = service.train_fitted_q_shadow_model(payload)
            else:
                result = service.build_shadow_benchmark_report(payload)
            _update_policy_job(
                job_id,
                status='completed',
                provider_status=result.get('provider_status', 'ok' if result.get('success') else 'degraded'),
                fallback_reason=result.get('fallback_reason'),
                progress=1.0,
                result=result,
                completed_at=_utc_now(),
            )
        except Exception as exc:  # pragma: no cover - defensive background boundary
            current_app.logger.exception("dispatch policy job failed: %s", job_id)
            _update_policy_job(
                job_id,
                status='failed',
                provider_status='degraded',
                fallback_reason=f"DISPATCH_POLICY_JOB_FAILED:{type(exc).__name__}",
                progress=1.0,
                error=str(exc),
                completed_at=_utc_now(),
            )

    with app.app_context():
        run_inside_context()


def _create_policy_job(payload):
    safe_payload = _apply_shadow_runtime_profile(payload, default='full')
    job_id = f"dispatch-policy-{uuid4().hex[:12]}"
    created_at = _utc_now()
    job = {
        'job_id': job_id,
        'status': 'queued',
        'policy_family': safe_payload.get('policy_family') or safe_payload.get('model_family') or 'fitted_q',
        'runtime_profile': safe_payload.get('runtime_profile'),
        'provider_status': 'queued',
        'fallback_reason': None,
        'progress': 0.0,
        'created_at': created_at,
        'updated_at': created_at,
        'request': {
            key: safe_payload.get(key)
            for key in (
                'policy_family',
                'model_family',
                'runtime_profile',
                'scenario_id',
                'scenario_limit',
                'row_limit',
                'top_k',
                'test_ratio',
                'use_ml',
            )
            if key in safe_payload
        },
        'truth_contract': {
            'mutation': 'none',
            'deployable': False,
            'hard_constraints_owner': 'dispatch solver layer',
            'job_boundary': 'background shadow policy job only',
        },
    }
    with _POLICY_JOB_LOCK:
        _POLICY_JOBS[job_id] = job
    thread = threading.Thread(
        target=_run_policy_job,
        args=(job_id, safe_payload, current_app._get_current_object()),
        name=f"dispatch-policy-job-{job_id}",
        daemon=True,
    )
    thread.start()
    return {
        'success': True,
        'provider_status': 'accepted',
        'fallback_reason': None,
        'job_id': job_id,
        'status': job['status'],
        'policy_family': job['policy_family'],
        'runtime_profile': job['runtime_profile'],
        'job': _policy_job_summary(job),
        'poll_url': f"/api/dispatch/policy/jobs/{job_id}",
        'runtime_limits': {
            'scenario_limit': safe_payload.get('scenario_limit'),
            'row_limit': safe_payload.get('row_limit'),
            'anomaly_source_limit': safe_payload.get('anomaly_source_limit'),
            'anomaly_limit': safe_payload.get('anomaly_limit'),
            'top_k': safe_payload.get('top_k'),
            'use_ml': safe_payload.get('use_ml'),
        },
        'truth_contract': job['truth_contract'],
    }


def _normalize_smart_dispatch_summary(summary, plans, unassigned_orders):
    """Keep legacy summary keys while adding frontend display and truth-contract keys."""
    summary = dict(summary or {})
    assigned_orders = sum(len(getattr(plan, 'orders', []) or []) for plan in plans)
    if assigned_orders == 0:
        assigned_orders = summary.get('assigned_orders', 0)

    unassigned_count = len(unassigned_orders or [])
    if unassigned_count == 0:
        unassigned_count = summary.get('unassigned_orders', 0)

    vehicles_used = len(plans or [])
    if vehicles_used == 0:
        vehicles_used = summary.get('vehicles_used', 0)

    total_distance = round(float(summary.get('total_distance', 0) or 0), 2)
    total_duration = round(float(summary.get('total_duration', 0) or 0), 2)
    total_cost = round(float(summary.get('total_cost', 0) or 0), 2)
    avg_cost = summary.get('avg_cost_per_order')
    if avg_cost is None:
        avg_cost = round(total_cost / assigned_orders, 2) if assigned_orders else 0

    summary.update({
        'assigned_orders': assigned_orders,
        'unassigned_orders': unassigned_count,
        'vehicles_used': vehicles_used,
        'total_distance': total_distance,
        'total_duration': total_duration,
        'total_cost': total_cost,
        'avg_cost_per_order': round(float(avg_cost or 0), 2),
        'total_orders_assigned': assigned_orders,
        'total_orders_unassigned': unassigned_count,
        'total_vehicles_used': vehicles_used,
        'total_distance_km': total_distance,
        'total_duration_min': total_duration,
        'average_cost_per_order': round(float(avg_cost or 0), 2),
        **SMART_DISPATCH_TRUTH_CONTRACT,
    })
    return summary


@dispatch_bp.route('/auto', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=15, window_seconds=60, key_func=lambda: f"auto_dispatch:{get_jwt_identity()}")
def auto_dispatch():
    """
    自动调度
    
    Body:
        order_ids: 订单ID列表（可选，默认处理所有待分配订单）
        vehicle_ids: 车辆ID列表（可选）
        consider_weather: 是否考虑天气（默认 true）
        consider_traffic: 是否考虑路况（默认 true）
        max_orders_per_vehicle: 每车最大订单数（默认 5）
    
    Returns:
        {
            "success": true,
            "plans": [...],  // 调度计划列表
            "unassigned_orders": [...],  // 未分配订单
            "summary": {...}  // 汇总信息
        }
    """
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        consider_weather = data.get('consider_weather', True)
        consider_traffic = data.get('consider_traffic', True)
        max_orders = data.get('max_orders_per_vehicle', 5)
        
        service = get_dispatch_orchestration_service()
        result = service.preview(
            {
                'order_ids': order_ids,
                'vehicle_ids': vehicle_ids,
                'consider_weather': consider_weather,
                'consider_traffic': consider_traffic,
                'max_orders_per_vehicle': max_orders,
                'algorithm': data.get('algorithm', 'balanced'),
                'weights': data.get('weights', {'cost': 0.4, 'time': 0.3, 'satisfaction': 0.3}),
                'limit': data.get('limit', data.get('per_page', 100)),
            },
            user_id=_current_user_id(),
        )

        status = 200 if result.get('success') else 400
        return jsonify(result), status
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/merge-suggestions', methods=['GET'])
@jwt_required()
def suggest_merge():
    """
    获取可合并订单建议
    
    Query params:
        order_ids: 订单ID列表（逗号分隔，可选）
        max_distance: 最大合并距离（公里，默认 50）
    
    Returns:
        {
            "success": true,
            "clusters": [
                {
                    "orders": [...],
                    "order_ids": [...],
                    "center": {"latitude": ..., "longitude": ...},
                    "total_weight": ...,
                    "total_volume": ...
                }
            ]
        }
    """
    try:
        order_ids_str = request.args.get('order_ids')
        max_distance = request.args.get('max_distance', 50, type=float)
        
        order_ids = None
        if order_ids_str:
            order_ids = [int(x.strip()) for x in order_ids_str.split(',') if x.strip().isdigit()]
        
        service = get_dispatch_service()
        clusters = service.suggest_merge_orders(
            order_ids=order_ids,
            max_merge_distance=max_distance
        )
        
        return jsonify({
            'success': True,
            'clusters': clusters,
            'total_clusters': len(clusters)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/apply', methods=['POST'])
@jwt_required()
def apply_dispatch():
    """
    应用调度计划
    
    Body:
        plans: 调度计划列表
        [
            {
                "vehicle_id": 1,
                "order_ids": [1, 2, 3]
            }
        ]
    
    Returns:
        应用结果
    """
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        result = service.apply(data, user_id=_current_user_id())
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_dispatch():
    """
    预览调度结果（不实际应用）
    
    统一调度预览，不修改原始订单/物流明细。
    """
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        persist = data.get('persist', True) is not False
        result = service.preview(data, user_id=_current_user_id(), persist=persist)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/health', methods=['GET'])
@jwt_required()
def dispatch_health():
    """调度数据健康与可执行性诊断。"""
    try:
        service = get_dispatch_orchestration_service()
        return jsonify(service.health())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/waves', methods=['POST'])
@jwt_required()
def create_dispatch_wave():
    """创建可计算的调度波次。"""
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        return jsonify(service.create_wave(data))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/scenarios', methods=['GET'])
@jwt_required()
def list_dispatch_scenarios():
    """列出最近调度场景。"""
    try:
        limit = request.args.get('limit', 20, type=int)
        service = get_dispatch_orchestration_service()
        return jsonify(service.list_scenarios(limit=limit))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/scenarios/<int:scenario_id>', methods=['GET'])
@jwt_required()
def get_dispatch_scenario(scenario_id):
    """查看调度场景详情。"""
    try:
        service = get_dispatch_orchestration_service()
        result = service.scenario_detail(scenario_id)
        status = 200 if result.get('success') else 404
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/learning-dataset', methods=['GET', 'POST'])
@jwt_required()
def dispatch_learning_dataset():
    """Return persisted dispatch assignments as an AI shadow training dataset."""
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
        else:
            payload = {
                'scenario_id': request.args.get('scenario_id', type=int),
                'scenario_ids': request.args.get('scenario_ids'),
                'scenario_limit': request.args.get('scenario_limit', 50, type=int),
                'row_limit': request.args.get('row_limit', 200, type=int),
                'status': request.args.get('status'),
                'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
            }
        payload = _apply_shadow_runtime_profile(payload)
        service = get_dispatch_learning_dataset_service()
        result = service.build_dataset(payload)
        return jsonify(_attach_shadow_runtime(result, payload))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/policy-scorer', methods=['GET', 'POST'])
@jwt_required()
def dispatch_policy_scorer():
    """Compare offline shadow dispatch policies over persisted learning rows."""
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
        else:
            payload = {
                'scenario_id': request.args.get('scenario_id', type=int),
                'scenario_ids': request.args.get('scenario_ids'),
                'scenario_limit': request.args.get('scenario_limit', 50, type=int),
                'row_limit': request.args.get('row_limit', 200, type=int),
                'top_k': request.args.get('top_k', 10, type=int),
                'status': request.args.get('status'),
                'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
            }
        payload = _apply_shadow_runtime_profile(payload)
        service = get_dispatch_learning_dataset_service()
        result = service.score_policies(payload)
        return jsonify(_attach_shadow_runtime(result, payload))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/reward-model', methods=['GET', 'POST'])
@jwt_required()
def dispatch_reward_model():
    """Train/evaluate a lightweight offline shadow reward model."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 50, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'test_ratio': request.args.get('test_ratio', 0.3, type=float),
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'reward-model',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().train_reward_model(safe_payload),
    )


@dispatch_bp.route('/redispatch-simulator', methods=['GET', 'POST'])
@jwt_required()
def dispatch_redispatch_simulator():
    """Run a read-only dynamic re-dispatch shadow simulation."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'top_k': request.args.get('top_k', 10, type=int),
            'delay_minutes': request.args.get('delay_minutes', 45, type=float),
            'delay_vehicle_ids': request.args.get('delay_vehicle_ids'),
            'unavailable_vehicle_ids': request.args.get('unavailable_vehicle_ids'),
            'cost_multiplier': request.args.get('cost_multiplier', 1.12, type=float),
            'provider_degradation': request.args.get('provider_degradation', 'true').lower() != 'false',
            'reliability_drop': request.args.get('reliability_drop', 0.25, type=float),
            'priority_order_refs': request.args.get('priority_order_refs'),
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'redispatch-simulator',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().simulate_redispatch(safe_payload),
    )


@dispatch_bp.route('/redispatch-profiles', methods=['GET', 'POST'])
@jwt_required()
def dispatch_redispatch_profiles():
    """Generate redispatch simulator profiles from real anomaly signals."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'anomaly_source_limit': request.args.get('anomaly_source_limit', 50000, type=int),
            'anomaly_limit': request.args.get('anomaly_limit', 80, type=int),
            'tasks': request.args.get('tasks'),
            'city': request.args.get('city') or request.args.get('destination_city'),
            'use_ml': request.args.get('use_ml', 'false').lower() == 'true',
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'redispatch-profiles',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().build_redispatch_profiles(safe_payload),
    )


@dispatch_bp.route('/redispatch-scenario-generator', methods=['GET', 'POST'])
@jwt_required()
def dispatch_redispatch_scenario_generator():
    """Generate read-only historical disruption scenarios for shadow replay."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'top_k': request.args.get('top_k', 10, type=int),
            'anomaly_source_limit': request.args.get('anomaly_source_limit', 50000, type=int),
            'anomaly_limit': request.args.get('anomaly_limit', 80, type=int),
            'tasks': request.args.get('tasks'),
            'city': request.args.get('city') or request.args.get('destination_city'),
            'use_ml': request.args.get('use_ml', 'false').lower() == 'true',
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'redispatch-scenario-generator',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().build_redispatch_scenario_generator(safe_payload),
    )


@dispatch_bp.route('/rl-shadow-runner', methods=['GET', 'POST'])
@jwt_required()
def dispatch_rl_shadow_runner():
    """Run an offline RL-style shadow benchmark over redispatch episodes."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'top_k': request.args.get('top_k', 10, type=int),
            'anomaly_source_limit': request.args.get('anomaly_source_limit', 50000, type=int),
            'anomaly_limit': request.args.get('anomaly_limit', 80, type=int),
            'tasks': request.args.get('tasks'),
            'city': request.args.get('city') or request.args.get('destination_city'),
            'use_ml': request.args.get('use_ml', 'false').lower() == 'true',
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'rl-shadow-runner',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().run_rl_shadow_runner(safe_payload),
    )


@dispatch_bp.route('/fitted-q-shadow-model', methods=['GET', 'POST'])
@jwt_required()
def dispatch_fitted_q_shadow_model():
    """Train/evaluate an offline fitted-Q shadow model over redispatch episodes."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'top_k': request.args.get('top_k', 10, type=int),
            'test_ratio': request.args.get('test_ratio', 0.3, type=float),
            'anomaly_source_limit': request.args.get('anomaly_source_limit', 50000, type=int),
            'anomaly_limit': request.args.get('anomaly_limit', 80, type=int),
            'tasks': request.args.get('tasks'),
            'city': request.args.get('city') or request.args.get('destination_city'),
            'use_ml': request.args.get('use_ml', 'false').lower() == 'true',
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'fitted-q-shadow-model',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().train_fitted_q_shadow_model(safe_payload),
    )


@dispatch_bp.route('/shadow-benchmark', methods=['GET', 'POST'])
@jwt_required()
def dispatch_shadow_benchmark():
    """Return a unified dispatch AI/RL shadow readiness scorecard."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'top_k': request.args.get('top_k', 10, type=int),
            'test_ratio': request.args.get('test_ratio', 0.3, type=float),
            'anomaly_source_limit': request.args.get('anomaly_source_limit', 50000, type=int),
            'anomaly_limit': request.args.get('anomaly_limit', 80, type=int),
            'tasks': request.args.get('tasks'),
            'city': request.args.get('city') or request.args.get('destination_city'),
            'use_ml': request.args.get('use_ml', 'false').lower() == 'true',
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'shadow-benchmark',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().build_shadow_benchmark_report(safe_payload),
    )


@dispatch_bp.route('/shadow-benchmark/snapshot', methods=['GET', 'POST'])
@jwt_required()
def dispatch_shadow_benchmark_snapshot():
    """Export a non-persistent dispatch AI/RL shadow benchmark snapshot."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            'scenario_id': request.args.get('scenario_id', type=int),
            'scenario_ids': request.args.get('scenario_ids'),
            'scenario_limit': request.args.get('scenario_limit', 1, type=int),
            'row_limit': request.args.get('row_limit', 200, type=int),
            'top_k': request.args.get('top_k', 10, type=int),
            'test_ratio': request.args.get('test_ratio', 0.3, type=float),
            'anomaly_source_limit': request.args.get('anomaly_source_limit', 50000, type=int),
            'anomaly_limit': request.args.get('anomaly_limit', 80, type=int),
            'tasks': request.args.get('tasks'),
            'city': request.args.get('city') or request.args.get('destination_city'),
            'use_ml': request.args.get('use_ml', 'false').lower() == 'true',
            'status': request.args.get('status'),
            'include_preview': request.args.get('include_preview', 'true').lower() != 'false',
        }
    return _shadow_response(
        'shadow-benchmark-snapshot',
        payload,
        lambda safe_payload: get_dispatch_learning_dataset_service().export_shadow_benchmark_snapshot(safe_payload),
    )


@dispatch_bp.route('/policy/jobs', methods=['POST'])
@jwt_required()
def create_dispatch_policy_job():
    """Create a non-blocking dispatch AI/RL shadow policy job."""
    payload = request.get_json(silent=True) or {}
    result = _create_policy_job(payload)
    return jsonify(result), 202 if result.get('success') else 400


@dispatch_bp.route('/policy/jobs/<job_id>', methods=['GET'])
@jwt_required()
def get_dispatch_policy_job(job_id):
    """Return a dispatch policy shadow job status."""
    with _POLICY_JOB_LOCK:
        job = dict(_POLICY_JOBS.get(job_id) or {})
    if not job:
        return jsonify({
            'success': False,
            'provider_status': 'degraded',
            'fallback_reason': 'DISPATCH_POLICY_JOB_NOT_FOUND',
            'job_id': job_id,
        }), 404
    return jsonify({
        'success': True,
        'provider_status': job.get('provider_status', 'unknown'),
        'fallback_reason': job.get('fallback_reason'),
        'job_id': job.get('job_id'),
        'status': job.get('status'),
        'policy_family': job.get('policy_family'),
        'runtime_profile': job.get('runtime_profile'),
        'progress': job.get('progress', 0.0),
        'job': job,
        'truth_contract': job.get('truth_contract') or {
            'mutation': 'none',
            'deployable': False,
            'hard_constraints_owner': 'dispatch solver layer',
        },
    })


@dispatch_bp.route('/smart', methods=['POST'])
@jwt_required()
def smart_dispatch():
    """
    智能调度 - 使用遗传算法优化
    
    Body:
        order_ids: 订单ID列表（可选，默认处理所有待分配订单）
        vehicle_ids: 车辆ID列表（可选）
        weights: 多目标权重（可选）
            {
                "cost": 0.4,        # 成本权重
                "time": 0.3,        # 时间权重
                "satisfaction": 0.3 # 满意度权重
            }
        consider_weather: 是否考虑天气（默认 true）
        consider_traffic: 是否考虑路况（默认 true）
        algorithm: 算法选择（默认 'genetic'）
            - 'genetic': 遗传算法（推荐）
            - 'greedy': 贪心算法
    
    Returns:
        {
            "success": true,
            "plans": [...],
            "unassigned_orders": [...],
            "summary": {...},
            "algorithm": "genetic",
            "generations": 100,
            "convergence_score": 0.85
        }
    """
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        weights = data.get('weights', {'cost': 0.4, 'time': 0.3, 'satisfaction': 0.3})
        consider_weather = data.get('consider_weather', True)
        consider_traffic = data.get('consider_traffic', True)
        algorithm = data.get('algorithm', 'genetic')
        
        service = get_dispatch_orchestration_service()
        result = service.preview(
            {
                'order_ids': order_ids,
                'vehicle_ids': vehicle_ids,
                'weights': weights,
                'consider_weather': consider_weather,
                'consider_traffic': consider_traffic,
                'algorithm': algorithm,
                'policy_mode': data.get('policy_mode', 'solver_only'),
                'limit': data.get('limit', data.get('per_page', 100)),
                'max_orders_per_vehicle': data.get('max_orders_per_vehicle', 5),
                'use_precise_distance': data.get('use_precise_distance', True),
            },
            user_id=_current_user_id(),
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/algorithms', methods=['GET'])
@jwt_required()
def get_algorithms():
    """获取可用的调度算法列表"""
    return jsonify({
        'success': True,
        'algorithms': [
            {
                'id': 'balanced',
                'name': '均衡策略',
                'description': '综合考虑距离、容量、成本，当前生产默认策略',
                'best_for': '真实数据调度、稳定预览',
                'performance': '快速且可解释'
            },
            {
                'id': 'greedy',
                'name': '贪心算法',
                'description': '快速分配，每次选择局部最优解',
                'best_for': '快速响应、简单场景',
                'performance': '快速但可能不是全局最优'
            },
            {
                'id': 'capacity_first',
                'name': '载重优先',
                'description': '优先提升车辆装载率，适合运力紧张波次',
                'best_for': '车辆不足、拼单场景',
                'performance': '快速且偏装载率'
            },
            {
                'id': 'ortools',
                'name': 'OR-Tools',
                'description': '求解器目录已接入；当前按可用性进入影子对比',
                'best_for': '后续约束求解主链路',
                'performance': '可用时快速'
            },
            {
                'id': 'alns',
                'name': 'ALNS',
                'description': '自适应大邻域搜索；当前按可用性进入影子对比',
                'best_for': '大规模 VRP 迭代优化',
                'performance': '适合中大波次'
            },
            {
                'id': 'genetic',
                'name': '遗传算法',
                'description': '保留为对比算法，不再作为生产默认主链路',
                'best_for': '教学演示、对照实验',
                'performance': '较慢'
            }
        ],
        'weight_options': {
            'cost': '成本优化权重（0-1）',
            'time': '时间优化权重（0-1）',
            'satisfaction': '满意度优化权重（0-1）'
        }
    })


@dispatch_bp.route('/optimize-v2', methods=['POST'])
@jwt_required()
def optimize_dispatch_v2():
    """
    使用优化引擎进行调度（V2）
    
    Body:
        order_ids: 订单ID列表
        vehicle_ids: 车辆ID列表
        solver: 求解器类型
        multi_objective: 是否多目标优化
        time_limit: 时间限制
    """
    from app.models import Order, Vehicle, Node
    from app.services.smart_dispatch_service_v2 import smart_dispatch_v2
    
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids', [])
        vehicle_ids = data.get('vehicle_ids', [])
        solver = data.get('solver', 'genetic')
        multi_objective = data.get('multi_objective', False)
        time_limit = data.get('time_limit', 60)
        
        # 获取数据
        orders = Order.query.filter(Order.id.in_(order_ids)).all() if order_ids else Order.query.filter(Order.status == 'pending').all()
        vehicles = Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).all() if vehicle_ids else Vehicle.query.filter(Vehicle.status == 'available').all()
        nodes = Node.query.all()
        
        # 找仓库
        depot = Node.query.filter(Node.type == 'depot').first()
        if not depot:
            depot = nodes[0] if nodes else None
        
        if not depot:
            return jsonify({'success': False, 'error': '找不到仓库节点'}), 400
        
        # 调用优化引擎
        result = smart_dispatch_v2.optimize_dispatch(
            orders=orders,
            vehicles=vehicles,
            nodes=nodes,
            depot_node=depot,
            solver_type=solver,
            multi_objective=multi_objective,
            time_limit=time_limit
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'plans': [
                    {
                        'vehicle_id': p.vehicle_id,
                        'vehicle_info': p.vehicle_info,
                        'orders': p.orders,
                        'route_sequence': p.route_sequence,
                        'total_distance': p.total_distance,
                        'total_duration': p.total_duration,
                        'total_cost': p.total_cost,
                        'score': p.score,
                        'load_utilization': p.load_utilization
                    }
                    for p in result.plans
                ],
                'unassigned_orders': result.unassigned_orders,
                'summary': result.summary,
                'solver': result.solver,
                'solve_time': result.solve_time,
                'objectives': result.objectives
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/multi-objective-v2', methods=['POST'])
@jwt_required()
def multi_objective_optimize_v2():
    """
    多目标优化（V2）
    
    返回 Pareto 前沿上的最优解
    """
    from app.models import Order, Vehicle, Node
    from app.services.smart_dispatch_service_v2 import smart_dispatch_v2
    
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids', [])
        vehicle_ids = data.get('vehicle_ids', [])
        solver = data.get('solver', 'pymoo_nsga2')
        n_gen = data.get('n_gen', 100)
        
        # 获取数据
        orders = Order.query.filter(Order.id.in_(order_ids)).all() if order_ids else Order.query.filter(Order.status == 'pending').all()
        vehicles = Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).all() if vehicle_ids else Vehicle.query.filter(Vehicle.status == 'available').all()
        nodes = Node.query.all()
        
        depot = Node.query.filter(Node.type == 'depot').first()
        if not depot:
            depot = nodes[0] if nodes else None
        
        if not depot:
            return jsonify({'success': False, 'error': '找不到仓库节点'}), 400
        
        # 调用多目标优化
        result = smart_dispatch_v2.multi_objective_optimize(
            orders=orders,
            vehicles=vehicles,
            nodes=nodes,
            depot_node=depot,
            solver_type=solver,
            n_gen=n_gen
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'plans': [
                    {
                        'vehicle_id': p.vehicle_id,
                        'vehicle_info': p.vehicle_info,
                        'orders': p.orders,
                        'route_sequence': p.route_sequence,
                        'total_distance': p.total_distance,
                        'load_utilization': p.load_utilization
                    }
                    for p in result.plans
                ],
                'summary': result.summary,
                'solver': result.solver,
                'solve_time': result.solve_time,
                'objectives': result.objectives,
                'pareto_front_size': result.summary.get('pareto_size', 1)
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/compare-solvers', methods=['POST'])
@jwt_required()
def compare_solvers():
    """
    对比多个求解器
    """
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        result = service.compare_solvers(data)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
