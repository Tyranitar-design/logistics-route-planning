#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级路径优化 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.advanced_route_optimization import get_advanced_route_optimization_service
import logging

logger = logging.getLogger(__name__)

advanced_route_bp = Blueprint('advanced_route', __name__)


@advanced_route_bp.route('/optimize', methods=['POST'])
@jwt_required()
def optimize_route():
    """
    高级路径优化
    
    Body:
        node_ids: 节点ID列表（可选）
        algorithm: 算法选择
            - 'aco': 蚁群算法
            - 'pso': 粒子群优化
            - 'drl': 深度强化学习(Q-Learning)
            - 'hybrid': 混合算法（默认）
        params: 算法参数（可选）
    
    Returns:
        {
            "success": true,
            "best_route": [...],
            "best_cost": 123.45,
            "algorithm": "aco",
            "iterations": 100,
            "convergence_history": [...],
            "execution_time": 2.5
        }
    """
    try:
        data = request.get_json() or {}
        
        node_ids = data.get('node_ids')
        algorithm = data.get('algorithm', 'hybrid')
        params = data.get('params')
        
        service = get_advanced_route_optimization_service()
        result = service.optimize(node_ids, algorithm, params)
        
        if result.success:
            return jsonify({
                'success': True,
                'best_route': result.best_route,
                'best_cost': result.best_cost,
                'best_distance': result.best_distance,
                'algorithm': result.algorithm,
                'iterations': result.iterations,
                'convergence_history': result.convergence_history,
                'execution_time': result.execution_time,
                'metadata': result.metadata
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        logger.error(f"高级路径优化失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@advanced_route_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_algorithms():
    """
    对比不同算法效果
    
    Body:
        node_ids: 节点ID列表（可选）
    
    Returns:
        各算法对比结果
    """
    try:
        data = request.get_json() or {}
        node_ids = data.get('node_ids')
        
        service = get_advanced_route_optimization_service()
        results = service.compare_algorithms(node_ids)
        
        # 找出最优算法
        best_algo = min(
            [(k, v) for k, v in results.items() if v['success']],
            key=lambda x: x[1]['best_cost']
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'best_algorithm': best_algo[0] if best_algo else None,
            'recommendation': f'推荐使用 {best_algo[0]} 算法，成本最低为 {best_algo[1]["best_cost"]}' if best_algo else '所有算法都失败了'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@advanced_route_bp.route('/algorithms', methods=['GET'])
@jwt_required()
def get_algorithms():
    """获取可用算法列表"""
    return jsonify({
        'success': True,
        'algorithms': [
            {
                'id': 'aco',
                'name': '蚁群算法',
                'name_en': 'Ant Colony Optimization',
                'description': '模拟蚂蚁觅食行为，通过信息素更新寻找最优路径',
                'best_for': 'TSP问题、VRP问题、大规模节点优化',
                'performance': '收敛稳定，适合离散优化',
                'convergence': '较慢但结果质量高',
                'parameters': {
                    'ant_count': {'default': 30, 'description': '蚂蚁数量', 'range': '10-100'},
                    'max_iterations': {'default': 100, 'description': '最大迭代次数'},
                    'alpha': {'default': 1.0, 'description': '信息素重要程度'},
                    'beta': {'default': 2.0, 'description': '启发函数重要程度'},
                    'rho': {'default': 0.5, 'description': '信息素挥发系数'}
                }
            },
            {
                'id': 'pso',
                'name': '粒子群优化',
                'name_en': 'Particle Swarm Optimization',
                'description': '模拟鸟群觅食行为，通过群体协作寻找最优解',
                'best_for': '连续优化问题、快速求解场景',
                'performance': '收敛速度快，易于实现',
                'convergence': '快速但可能陷入局部最优',
                'parameters': {
                    'particle_count': {'default': 30, 'description': '粒子数量'},
                    'max_iterations': {'default': 100, 'description': '最大迭代次数'},
                    'w': {'default': 0.729, 'description': '惯性权重'},
                    'c1': {'default': 1.494, 'description': '个体学习因子'},
                    'c2': {'default': 1.494, 'description': '社会学习因子'}
                }
            },
            {
                'id': 'drl',
                'name': '深度强化学习',
                'name_en': 'Deep Reinforcement Learning (Q-Learning)',
                'description': '通过与环境交互学习最优策略，适合动态环境',
                'best_for': '动态变化环境、在线优化场景',
                'performance': '学习能力强，可处理不确定性',
                'convergence': '需要训练时间，但适应性强',
                'parameters': {
                    'learning_rate': {'default': 0.1, 'description': '学习率'},
                    'discount_factor': {'default': 0.95, 'description': '折扣因子'},
                    'epsilon': {'default': 0.3, 'description': '探索率'},
                    'episodes': {'default': 500, 'description': '训练回合数'}
                }
            },
            {
                'id': 'hybrid',
                'name': '混合算法',
                'name_en': 'Hybrid Optimization',
                'description': '结合多种算法优点，自动选择最优结果',
                'best_for': '追求最优解的场景、不确定哪种算法最优时',
                'performance': '综合多种算法优势',
                'convergence': '执行时间较长但结果最优',
                'parameters': {}
            }
        ]
    })


@advanced_route_bp.route('/convergence/<algorithm>', methods=['GET'])
@jwt_required()
def get_convergence_data(algorithm: str):
    """
    获取算法收敛曲线数据（用于可视化）
    
    Args:
        algorithm: 算法名称
    
    Returns:
        收敛曲线数据
    """
    try:
        node_ids = request.args.get('node_ids')
        if node_ids:
            node_ids = [int(x.strip()) for x in node_ids.split(',') if x.strip().isdigit()]
        
        service = get_advanced_route_optimization_service()
        result = service.optimize(node_ids, algorithm)
        
        if result.success:
            return jsonify({
                'success': True,
                'algorithm': result.algorithm,
                'convergence_history': result.convergence_history,
                'best_cost': result.best_cost,
                'iterations': result.iterations
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500