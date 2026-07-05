"""
优化引擎 API 路由
================

提供 REST API 接口调用优化引擎

作者: 小彩
日期: 2026-04-19
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any
import numpy as np

from app.services.precise_distance_provider import get_precise_distance_provider
from app.services.vrp_problem_builder import VRPProblemBuilder
from app.services.solver_recommendation_engine import SolverRecommendationEngine
from app.services.result_evaluator import ResultEvaluator
from app.services.gurobi_capability_service import get_gurobi_capability_service
from app.services.gurobi_assignment_service import get_gurobi_assignment_service
from app.services.gurobi_vrp_service import get_gurobi_vrp_service
from app.services.gurobi_network_design_service import get_gurobi_network_design_service
from app.services.optional_capability_service import get_optional_capability_service
from app.services.solver_benchmark_service import get_solver_benchmark_service
from app.services.route_sequence_benchmark_service import get_route_sequence_benchmark_service
from app.services.optimization_engine import (
    SolverFactory,
    VRPProblem,
    CVRPProblem,
    VRPTWProblem,
    FacilityLocationProblem,
    MultiObjectiveVRP,
    VRPData,
    ResultComparator,
    SolverType
)

optimization_bp = Blueprint('optimization', __name__)

problem_builder = VRPProblemBuilder()
recommendation_engine = SolverRecommendationEngine()
evaluator = ResultEvaluator()


def _bool_query_arg(name: str, default: bool = False) -> bool:
    value = request.args.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_query_arg(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(max(value, minimum), maximum)


def _project_geo_points(points):
    lons = [float(item["lon"]) for item in points if item.get("lon") is not None]
    lats = [float(item["lat"]) for item in points if item.get("lat") is not None]
    if not lons or not lats:
        return [[50.0, 50.0] for _ in points]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    lon_span = max(max_lon - min_lon, 1e-6)
    lat_span = max(max_lat - min_lat, 1e-6)

    projected = []
    for item in points:
        lon = float(item.get("lon") or min_lon)
        lat = float(item.get("lat") or min_lat)
        x = 8.0 + ((lon - min_lon) / lon_span) * 84.0
        y = 8.0 + ((lat - min_lat) / lat_span) * 84.0
        projected.append([round(x, 4), round(y, 4)])
    return projected


def _build_real_shipment_vrp_sample() -> Dict[str, Any]:
    customer_limit = _int_query_arg("customer_limit", 12, 3, 12)
    candidate_limit = _int_query_arg("candidate_limit", 4, 1, 8)
    dataset = get_gurobi_network_design_service().database_dataset_payload(
        {
            "customer_limit": customer_limit,
            "candidate_limit": candidate_limit,
        }
    )

    geo_customers = dataset.get("customers") or []
    geo_candidates = dataset.get("candidates") or []
    depot_geo = geo_candidates[0] if geo_candidates else {"name": "虚拟中心仓", "lat": 35.0, "lon": 110.0}
    projected = _project_geo_points([depot_geo, *geo_customers])
    depot = projected[0]
    customers = projected[1:]
    demands = [max(1.0, round(float(item.get("demand") or 1.0), 4)) for item in geo_customers]
    total_demand = sum(demands)
    capacity = round(max(max(demands or [1.0]) * 1.25, total_demand / 3.0 if total_demand else 50.0), 4)

    return {
        "success": True,
        "customers": customers,
        "demands": demands,
        "depot": depot,
        "capacity": capacity,
        "n_customers": len(customers),
        "geo_customers": geo_customers,
        "geo_depot": depot_geo,
        "geo_candidates": geo_candidates,
        "data_source": dataset.get("data_source"),
        "distance_source": "projected_coordinate_plane",
        "path_source": "shipment_fact_city_od_projection",
        "authenticity_level": "C" if dataset.get("data_source") == "shipment_fact_od_aggregate" else "D",
        "fallback_reason": dataset.get("fallback_reason"),
        "source_summary": (
            f"基于 shipment_facts 聚合 {len(geo_customers)} 个目的城市与 "
            f"{len(geo_candidates)} 个始发城市，并投影到 0-100 平面供 VRP 求解器对比。"
        ),
        "summary": dataset.get("summary", {}),
        "authenticity": {
            "level": "C" if dataset.get("data_source") == "shipment_fact_od_aggregate" else "D",
            "distance_source": "projected_coordinate_plane",
            "path_source": "shipment_fact_city_od_projection",
            "fallback_reason": dataset.get("fallback_reason"),
            "message": "真实运单城市聚合样本；路线图为求解器平面投影，不是高德导航路径。",
        },
    }


def _build_vrp_data_from_request(data: Dict[str, Any]) -> VRPData:
    """从请求构建带精确距离矩阵的 VRPData。"""
    customers = np.array(data.get('customers', []), dtype=float)
    demands = np.array(data.get('demands', []))
    depot = np.array(data.get('depot', [50, 50]), dtype=float)
    capacity = data.get('capacity', 50)
    use_precise_distance = bool(data.get('use_precise_distance', True))
    strategy = int(data.get('strategy', 0))

    if len(customers) == 0:
        raise ValueError('客户数据为空')
    if len(demands) != len(customers):
        raise ValueError('demands 长度必须与 customers 一致')

    n_customers = len(customers)
    n_vehicles = max(1, int(np.ceil(demands.sum() / capacity * 1.5)))

    provider = get_precise_distance_provider()
    matrix_result = provider.build_from_depot_and_customers(
        depot=(float(depot[0]), float(depot[1])),
        customers=[(float(row[0]), float(row[1])) for row in customers],
        strategy=strategy,
        use_amap=use_precise_distance,
    )

    vrp_data = VRPData(
        n_customers=n_customers,
        n_vehicles=n_vehicles,
        vehicle_capacity=capacity,
        depot=depot,
        customers=customers,
        demands=demands,
        distance_matrix=np.array(matrix_result.distance_matrix_km, dtype=float),
        duration_matrix=np.array(matrix_result.duration_matrix_min, dtype=float),
        distance_precision=matrix_result.precision,
        source_summary=matrix_result.source_summary,
        metadata={
            'distance_source': 'precise_distance_provider',
            'distance_provider': matrix_result.metadata.get('provider', 'PreciseDistanceProvider'),
            'strategy': strategy,
            'use_precise_distance': use_precise_distance,
            'cache_stats': matrix_result.cache_stats,
        }
    )

    return vrp_data


@optimization_bp.route('/solvers', methods=['GET'])
def list_solvers():
    """
    列出所有可用求解器
    
    Returns:
        {
            "solvers": [
                {
                    "type": "gurobi",
                    "name": "Gurobi",
                    "available": true,
                    "description": "...",
                    "best_for": "..."
                },
                ...
            ]
        }
    """
    solvers = []
    gurobi_health = get_gurobi_capability_service().check(run_smoke=False)
    
    for solver_type in SolverType:
        info = SolverFactory.get_solver_info(solver_type)
        item = {
            "type": solver_type.value,
            "name": info.get("name", solver_type.value),
            "available": SolverFactory.is_available(solver_type),
            "description": info.get("description", ""),
            "best_for": info.get("best_for", "")
        }
        if solver_type in {SolverType.GUROBI, SolverType.GUROBI_VRPTW}:
            item.update({
                "provider_status": gurobi_health["provider_status"],
                "fallback_reason": gurobi_health["fallback_reason"],
                "authenticity_level": gurobi_health["authenticity_level"],
                "checks": gurobi_health["checks"],
            })
        solvers.append(item)
    
    capability_status = get_optional_capability_service().check(run_smoke=False)

    return jsonify({
        "solvers": solvers,
        "capability_summary": capability_status["summary"],
        "capabilities": capability_status["capabilities"],
    })


@optimization_bp.route('/capabilities', methods=['GET'])
@optimization_bp.route('/capability-health', methods=['GET'])
def optimization_capabilities():
    """Return safe optional optimization/AI/RL/geospatial capability status."""
    run_smoke = _bool_query_arg("smoke", False)
    return jsonify(get_optional_capability_service().check(run_smoke=run_smoke))


@optimization_bp.route('/gurobi/health', methods=['GET'])
def gurobi_health():
    """
    Return safe Gurobi runtime capability status.

    Query:
        smoke=1  可选，运行一个 1 变量微型模型验证 license/runtime。
    """
    run_smoke = _bool_query_arg("smoke", False)
    status = get_gurobi_capability_service().check(run_smoke=run_smoke)
    return jsonify({
        "success": True,
        **status,
    })


@optimization_bp.route('/gurobi/smoke', methods=['POST'])
def gurobi_smoke():
    """Run a safe one-variable Gurobi smoke solve."""
    status = get_gurobi_capability_service().check(run_smoke=True)
    return jsonify({
        "success": True,
        **status,
    })


@optimization_bp.route('/gurobi/vehicle-assignment', methods=['POST'])
def gurobi_vehicle_assignment():
    """
    Solve a small vehicle-assignment MILP.

    Request Body:
        {
            "solver": "auto" | "gurobi" | "greedy",
            "orders": [{"id": "...", "weight_tons": 2.0, "volume_m3": 8.0, "priority": "high"}],
            "vehicles": [{"id": "...", "capacity_weight_tons": 8.0, "capacity_volume_m3": 24.0}]
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_gurobi_assignment_service().solve(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/gurobi/vehicle-assignment-demo', methods=['GET'])
def gurobi_vehicle_assignment_demo():
    """Run the bundled small vehicle-assignment demo."""
    service = get_gurobi_assignment_service()
    result = service.solve(service.demo_payload())
    return jsonify(result)


@optimization_bp.route('/gurobi/vrp', methods=['POST'])
def gurobi_vrp():
    """
    Solve a small CVRP instance with Gurobi when available.

    Request Body:
        {
            "solver": "auto" | "gurobi" | "greedy",
            "n_vehicles": 2,
            "vehicle_capacity": 7,
            "demands": [2, 3, 4, 2],
            "distance_matrix": [[0, ...], ...]
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_gurobi_vrp_service().solve(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/gurobi/vrp-demo', methods=['GET'])
def gurobi_vrp_demo():
    """Run the bundled small CVRP demo."""
    service = get_gurobi_vrp_service()
    result = service.solve(service.demo_payload())
    return jsonify(result)


@optimization_bp.route('/gurobi/network-design', methods=['POST'])
def gurobi_network_design():
    """
    Solve a small capacitated network-design MILP.

    Request Body:
        {
            "solver": "auto" | "gurobi" | "greedy",
            "max_facilities": 2,
            "customers": [{"id": "...", "demand": 120, "lat": 23.1, "lon": 113.2}],
            "candidates": [{"id": "...", "capacity": 260, "fixed_cost": 46000, "lat": 23.1, "lon": 113.2}]
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_gurobi_network_design_service().solve(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/gurobi/network-design-demo', methods=['GET'])
def gurobi_network_design_demo():
    """Run the bundled small network-design demo."""
    service = get_gurobi_network_design_service()
    result = service.solve(service.demo_payload())
    return jsonify(result)


@optimization_bp.route('/solver-benchmark', methods=['POST'])
@optimization_bp.route('/gurobi/compare-small-vrp', methods=['POST'])
def solver_benchmark():
    """
    Compare bounded CVRP solvers on one shared input.

    Request Body:
        {
            "solvers": ["gurobi", "ortools", "alns", "greedy"],
            "time_limit": 5,
            "n_vehicles": 2,
            "vehicle_capacity": 7,
            "demands": [2, 3, 4, 2],
            "distance_matrix": [[0, ...], ...]
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_solver_benchmark_service().compare_small_vrp(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/solver-benchmark-demo', methods=['GET'])
@optimization_bp.route('/gurobi/compare-small-vrp-demo', methods=['GET'])
def solver_benchmark_demo():
    """Run the bundled small CVRP solver benchmark demo."""
    service = get_solver_benchmark_service()
    result = service.compare_small_vrp(service.demo_payload())
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/route-sequence-benchmark', methods=['POST'])
def route_sequence_benchmark():
    """
    Compare bounded route-sequence solvers over real nodes/routes.

    Request Body:
        {
            "depot_id": 1,
            "node_ids": [2, 3, 4],
            "solvers": ["nearest_neighbor", "two_opt", "ortools", "gurobi"],
            "return_to_depot": true,
            "allow_haversine_fallback": true
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_route_sequence_benchmark_service().benchmark(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/route-sequence-benchmark-demo', methods=['GET'])
def route_sequence_benchmark_demo():
    """Run the bundled real-node route-sequence benchmark demo."""
    service = get_route_sequence_benchmark_service()
    result = service.benchmark(service.demo_payload())
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@optimization_bp.route('/solve', methods=['POST'])
def solve_vrp():
    """
    求解 VRP 问题
    
    Request Body:
        {
            "customers": [[x, y], ...],
            "demands": [d1, d2, ...],
            "depot": [x, y],
            "capacity": 50,
            "solver": "ortools" | "auto",
            "time_limit": 60,
            "use_precise_distance": true,
            "strategy": 0
        }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "请求数据为空"}), 400
    
    try:
        solver_type_str = str(data.get('solver', 'auto')).lower()
        time_limit = data.get('time_limit', 60)

        build_result = problem_builder.build_from_payload(data)
        problem = build_result.problem
        vrp_data = build_result.vrp_data

        recommendation = None
        if solver_type_str == 'auto':
            recommendation = recommendation_engine.recommend(
                problem_type=build_result.problem_type,
                n_customers=vrp_data.n_customers,
                require_high_accuracy=bool(data.get('require_high_accuracy', False)),
                prefer_fast_response=bool(data.get('prefer_fast_response', False)),
                realtime=bool(data.get('realtime', False)),
                available_solvers=SolverFactory.list_available_solvers(),
            )
            solver_type = recommendation.recommended_solver
        else:
            solver_type = SolverType(solver_type_str)

        solver = SolverFactory.create_solver(solver_type)
        result = solver.solve(problem, time_limit=time_limit)
        quality_report = evaluator.evaluate(problem, result)
        
        return jsonify({
            "success": True,
            "routes": result.routes,
            "total_distance": float(result.primary_objective),
            "solve_time": float(result.solve_time),
            "gap": float(result.gap) if result.gap is not None else 0.0,
            "solver": result.solver_name,
            "solver_type": solver_type.value,
            "distance_precision": vrp_data.distance_precision,
            "source_summary": vrp_data.source_summary,
            "distance_metadata": vrp_data.metadata,
            "result_metadata": result.metadata,
            "build_metadata": build_result.build_metadata,
            "quality_report": quality_report.to_dict(),
            "recommendation": recommendation.to_dict() if recommendation else None,
        })
    
    except ValueError as e:
        return jsonify({"success": False, "error": f"参数错误: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@optimization_bp.route('/compare', methods=['POST'])
def compare_solvers():
    """
    对比多个求解器
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "请求数据为空"}), 400
    
    try:
        solver_strs = data.get('solvers', ['ortools', 'genetic'])
        time_limit = data.get('time_limit', 60)

        build_result = problem_builder.build_from_payload(data)
        problem = build_result.problem
        vrp_data = build_result.vrp_data
        
        # 解析求解器类型（只选可用的）
        solver_types = []
        for s in solver_strs:
            try:
                st = SolverType(str(s).lower())
                if SolverFactory.is_available(st):
                    solver_types.append(st)
            except Exception:
                pass
        
        if not solver_types:
            return jsonify({"success": False, "error": "没有可用的求解器"}), 400
        
        # 用多个求解器求解
        results = SolverFactory.solve_with_all(problem, solver_types, time_limit)
        
        # 格式化结果 + 质量报告
        formatted = {}
        for solver_type, result in results.items():
            quality_report = evaluator.evaluate(problem, result)
            formatted[solver_type.value] = {
                "routes": result.routes,
                "total_distance": float(result.primary_objective),
                "solve_time": float(result.solve_time),
                "gap": float(result.gap) if result.gap is not None else 0.0,
                "result_metadata": result.metadata,
                "quality_report": quality_report.to_dict(),
            }
        
        # 对比
        comparison = ResultComparator.compare(results)
        
        return jsonify({
            "success": True,
            "results": formatted,
            "best_solver": comparison.best_solver.value if comparison.best_solver else None,
            "rankings": [(s.value, float(score)) for s, score in comparison.rankings],
            "distance_precision": vrp_data.distance_precision,
            "source_summary": vrp_data.source_summary,
            "distance_metadata": vrp_data.metadata,
            "build_metadata": build_result.build_metadata,
        })
    
    except ValueError as e:
        return jsonify({"success": False, "error": f"参数错误: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@optimization_bp.route('/distance/precision-report', methods=['POST'])
def distance_precision_report():
    """
    构建一次距离矩阵并返回精度报告。

    Request Body:
        {
            "customers": [[lng, lat], ...],
            "depot": [lng, lat],
            "use_precise_distance": true,
            "strategy": 0
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "请求数据为空"}), 400

    try:
        vrp_data = _build_vrp_data_from_request({
            **data,
            'demands': data.get('demands', [1] * len(data.get('customers', []))),
            'capacity': data.get('capacity', max(1, len(data.get('customers', [])) or 1)),
        })

        total_pairs = vrp_data.distance_precision.get('total_count', 0)
        exact_pairs = vrp_data.distance_precision.get('exact_count', 0)
        approx_pairs = vrp_data.distance_precision.get('approx_count', 0)
        exact_ratio = round(exact_pairs / total_pairs, 4) if total_pairs else 0.0
        approx_ratio = round(approx_pairs / total_pairs, 4) if total_pairs else 0.0

        return jsonify({
            "success": True,
            "node_count": vrp_data.n_nodes,
            "customer_count": vrp_data.n_customers,
            "precision": vrp_data.distance_precision,
            "source_summary": vrp_data.source_summary,
            "distance_metadata": vrp_data.metadata,
            "distance_matrix_shape": list(np.asarray(vrp_data.distance_matrix).shape),
            "duration_matrix_shape": list(np.asarray(vrp_data.duration_matrix).shape) if vrp_data.duration_matrix is not None else None,
            "summary": {
                "exact_ratio": exact_ratio,
                "approx_ratio": approx_ratio,
            }
        })

    except ValueError as e:
        return jsonify({"success": False, "error": f"参数错误: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@optimization_bp.route('/multi-objective', methods=['POST'])
def solve_multi_objective():
    """
    求解多目标 VRP
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "请求数据为空"}), 400
    
    try:
        payload = {
            **data,
            'problem_type': 'multi_objective'
        }
        solver_type_str = str(data.get('solver', 'pymoo_nsga2')).lower()
        n_gen = data.get('n_gen', 100)

        build_result = problem_builder.build_from_payload(payload)
        problem = build_result.problem
        vrp_data = build_result.vrp_data

        solver_type = SolverType(solver_type_str)
        solver = SolverFactory.create_solver(solver_type)
        result = solver.solve(problem, n_gen=n_gen)
        quality_report = evaluator.evaluate(problem, result)
        
        return jsonify({
            "success": True,
            "routes": result.routes,
            "objectives": [float(x) for x in result.objective_values],
            "pareto_front_size": int(result.metadata.get('pareto_front_size', 1)),
            "solve_time": float(result.solve_time),
            "solver": result.solver_name,
            "solver_type": solver_type.value,
            "distance_precision": vrp_data.distance_precision,
            "source_summary": vrp_data.source_summary,
            "distance_metadata": vrp_data.metadata,
            "result_metadata": result.metadata,
            "build_metadata": build_result.build_metadata,
            "quality_report": quality_report.to_dict(),
        })
    
    except ValueError as e:
        return jsonify({"success": False, "error": f"参数错误: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@optimization_bp.route('/recommend', methods=['POST'])
def recommend_solver():
    """
    根据问题特征推荐求解器
    
    Request Body:
        {
            "n_customers": 50,
            "n_objectives": 2,
            "has_time_windows": false,
            "need_exact": false
        }
    
    Returns:
        {
            "recommended": "ortools",
            "reason": "...",
            "alternatives": [...]
        }
    """
    data = request.get_json() or {}
    
    n_customers = data.get('n_customers', 10)
    n_objectives = data.get('n_objectives', 1)
    has_time_windows = data.get('has_time_windows', False)
    need_exact = data.get('need_exact', False)
    
    # 推荐逻辑
    recommended = None
    reason = ""
    alternatives = []
    
    if n_objectives > 1:
        # 多目标
        if n_objectives <= 3:
            recommended = SolverType.PYMOO_NSGA2
            reason = "NSGA-II 适合 2-3 个目标的优化"
            alternatives = [SolverType.PYMOO_NSGA3]
        else:
            recommended = SolverType.PYMOO_NSGA3
            reason = "NSGA-III 适合 4+ 个目标的优化"
            alternatives = [SolverType.PYMOO_NSGA2]
    
    elif need_exact:
        # 需要精确解
        if SolverFactory.is_available(SolverType.GUROBI):
            recommended = SolverType.GUROBI
            reason = "Gurobi 提供精确最优解"
            alternatives = [SolverType.ORTOOLS]
        else:
            recommended = SolverType.ORTOOLS
            reason = "OR-Tools 是可用的最佳选择"
    
    elif n_customers > 100:
        # 大规模问题
        recommended = SolverType.ALNS
        reason = "ALNS 适合大规模问题"
        alternatives = [SolverType.ORTOOLS, SolverType.GENETIC]
    
    else:
        # 一般情况
        recommended = SolverType.ORTOOLS
        reason = "OR-Tools 快速可靠"
        alternatives = [SolverType.GENETIC]
    
    # 检查可用性
    if not SolverFactory.is_available(recommended):
        available = SolverFactory.list_available_solvers()
        if available:
            recommended = available[0]
            reason = f"推荐求解器不可用，使用 {recommended.value}"
    
    return jsonify({
        "recommended": recommended.value,
        "reason": reason,
        "alternatives": [s.value for s in alternatives if SolverFactory.is_available(s)]
    })


@optimization_bp.route('/demo', methods=['GET'])
def get_demo_data():
    """
    获取演示数据
    
    Returns:
        {
            "customers": [[x, y], ...],
            "demands": [d1, d2, ...],
            "depot": [x, y]
        }
    """
    # 生成演示数据
    np.random.seed(42)
    n_customers = 15
    
    # 随机生成客户位置
    customers = np.random.rand(n_customers, 2) * 100
    demands = np.random.randint(5, 20, size=n_customers)
    depot = np.array([50.0, 50.0])
    
    return jsonify({
        "customers": customers.tolist(),
        "demands": demands.tolist(),
        "depot": depot.tolist(),
        "capacity": 50,
        "n_customers": n_customers,
        "data_source": "random_demo",
        "distance_source": "synthetic_euclidean_plane",
        "path_source": "synthetic_preview",
        "authenticity_level": "D",
        "fallback_reason": "generated_demo_data",
        "authenticity": {
            "level": "D",
            "distance_source": "synthetic_euclidean_plane",
            "path_source": "synthetic_preview",
            "fallback_reason": "generated_demo_data",
            "message": "随机演示数据，仅用于算法功能兜底验证。",
        },
    })


@optimization_bp.route('/real-shipment-demo', methods=['GET'])
@optimization_bp.route('/real-vrp-demo', methods=['GET'])
def get_real_shipment_demo_data():
    """Return a bounded VRP sample derived from real shipment_facts city aggregates."""
    try:
        return jsonify(_build_real_shipment_vrp_sample())
    except Exception as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
            "provider_status": "degraded",
            "fallback_reason": f"REAL_SHIPMENT_SAMPLE_FAILED:{exc.__class__.__name__}",
        }), 500
