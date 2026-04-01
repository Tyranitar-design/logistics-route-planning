#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask应用初始化 - 敏捷路径优化版本
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
# 从 models 导入统一的 db 实例
from app.models import db

# 初始化 JWT
jwt = JWTManager()


def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    jwt.init_app(app)
    
    # JWT错误处理
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token已过期', 'message': '请重新登录'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"[JWT错误] 无效Token: {error}")
        return jsonify({'error': '无效的Token', 'message': '请重新登录', 'detail': str(error)}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': '缺少Token', 'message': '请先登录'}), 401
    
    # 注册蓝图
    from app.routes.auth import auth_bp
    from app.routes.nodes import nodes_bp
    from app.routes.routes import routes_bp
    from app.routes.vehicles import vehicles_bp
    from app.routes.orders import orders_bp
    from app.routes.stats import stats_bp
    from app.routes.map import map_bp
    from app.routes.amap import amap_bp
    from app.routes.tracking import tracking_bp
    from app.routes.cost import cost_bp
    from app.routes.data import data_bp
    from app.routes.weather import weather_bp
    from app.routes.dispatch import dispatch_bp
    from app.routes.realtime import realtime_bp
    from app.routes.trajectory import trajectory_bp
    from app.routes.traffic import traffic_bp
    from app.routes.multi_objective import multi_obj_bp
    from app.routes.oil_price import oil_price_bp
    from app.routes.analytics import analytics_bp
    from app.routes.ml import register_ml_routes
    from app.routes.agile import agile_bp
    from app.routes.risk import risk_bp
    from app.routes.alert import alert_bp
    from app.routes.advanced_route import advanced_route_bp
    from app.routes.advanced_ml import register_advanced_ml_routes
    from app.routes.pricing import register_pricing_routes
    from app.routes.inventory import register_inventory_routes
    from app.routes.multimodal import register_multimodal_routes
    from app.routes.anomaly import register_anomaly_routes
    from app.routes.data_analytics import register_data_analytics_routes
    from app.routes.driver import driver_bp
    from app.routes.supplier import supplier_bp
    from app.routes.audit import audit_bp
    from app.routes.test_data import test_data_bp
    from app.routes.speech import speech_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(nodes_bp, url_prefix='/api/nodes')
    app.register_blueprint(routes_bp, url_prefix='/api/routes')
    app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(stats_bp, url_prefix='/api/stats')
    app.register_blueprint(map_bp, url_prefix='/api/map')
    app.register_blueprint(amap_bp, url_prefix='/api/amap')
    app.register_blueprint(tracking_bp, url_prefix='/api/tracking')
    app.register_blueprint(cost_bp, url_prefix='/api/cost')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(weather_bp, url_prefix='/api/weather')
    app.register_blueprint(dispatch_bp, url_prefix='/api/dispatch')
    app.register_blueprint(realtime_bp, url_prefix='/api/realtime')
    app.register_blueprint(trajectory_bp, url_prefix='/api/trajectory')
    app.register_blueprint(traffic_bp, url_prefix='/api/traffic')
    app.register_blueprint(multi_obj_bp, url_prefix='/api/multi-objective')
    app.register_blueprint(oil_price_bp, url_prefix='/api/oil-price')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(agile_bp, url_prefix='/api/agile')
    app.register_blueprint(risk_bp, url_prefix='/api/risk')
    app.register_blueprint(alert_bp, url_prefix='/api/alert')
    app.register_blueprint(advanced_route_bp, url_prefix='/api/advanced-route')
    
    # 司机端 API
    app.register_blueprint(driver_bp, url_prefix='/api/driver')
    
    # 供应商管理 API
    app.register_blueprint(supplier_bp)
    
    # 审计日志 API
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    
    # 测试数据 API
    app.register_blueprint(test_data_bp, url_prefix='/api/test-data')
    
    # 语音识别 API
    app.register_blueprint(speech_bp, url_prefix='/api/speech')
    
    # 注册新功能路由
    register_advanced_ml_routes(app)
    register_pricing_routes(app)
    register_inventory_routes(app)
    register_multimodal_routes(app)
    register_anomaly_routes(app)
    register_data_analytics_routes(app)
    
    # 注册 ML 预测路由
    register_ml_routes(app)
    
    # 注册健康检查蓝图
    from app.routes.health import health_bp
    app.register_blueprint(health_bp, url_prefix='/api')
    
    # 根路径
    @app.route('/')
    def index():
        return jsonify({
            'message': '物流路径规划系统 API',
            'version': '2.0',
            'features': 43,
            'documentation': '/api/docs'
        })
    
    # API 文档入口
    @app.route('/api/docs')
    def api_docs():
        return jsonify({
            'name': '物流路径规划系统 API',
            'version': '2.0',
            'features': 43,
            'modules': {
                'auth': '用户认证 (登录/注册/Token刷新)',
                'orders': '订单管理 (CRUD/状态追踪)',
                'vehicles': '车辆管理 (档案/状态监控)',
                'nodes': '节点管理 (仓库/配送站)',
                'routes': '路线管理 (路径规划/成本估算)',
                'dispatch': '智能调度 (遗传算法/多目标优化)',
                'analytics': '数据分析 (仪表盘/趋势分析)',
                'ml': 'ML预测 (LSTM需求预测)',
                'alert': '预警中心 (实时告警/健康度)',
                'risk': '风险管理 (供应链风险评估)',
                'supplier': '供应商管理 (档案/绩效评估)',
                'driver': '司机端API (小程序支持)'
            },
            'endpoints': {
                'health': '/api/health',
                'login': '/api/auth/login',
                'dashboard': '/api/analytics/dashboard'
            }
        })
    
    return app
