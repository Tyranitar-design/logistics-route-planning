#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask配置文件
"""

import os
from datetime import timedelta

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # 数据库配置 - PostgreSQL 优先，SQLite 仅作兼容兜底
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)  # 确保数据目录存在
    DATABASE_PATH = os.path.abspath(os.path.join(DATA_DIR, 'logistics.db'))
    # 将Windows路径转换为SQLite兼容的URL格式
    DATABASE_PATH_FOR_URL = DATABASE_PATH.replace('\\', '/')
    import urllib.parse
    ENCODED_PATH = urllib.parse.quote(DATABASE_PATH_FOR_URL, safe='/')
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('POSTGRES_DATABASE_URL')
        or os.environ.get('DATABASE_URL')
        or f'sqlite:///{ENCODED_PATH}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
    
    # CORS配置
    CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:5174', 'http://localhost:5175', 
                    'http://127.0.0.1:5173', 'http://127.0.0.1:5174', 'http://127.0.0.1:5175',
                    'http://localhost', 'http://localhost:80', 'http://localhost:8080']
    
    # 高德地图API配置
    AMAP_WEB_KEY = os.environ.get('AMAP_WEB_KEY', '')
    AMAP_SERVICE_KEY = os.environ.get('AMAP_SERVICE_KEY', '')
    
    # 天地图API配置
    TIANDITU_BROWSER_KEY = os.environ.get('TIANDITU_BROWSER_KEY', '')
    TIANDITU_SERVER_KEY = os.environ.get('TIANDITU_SERVER_KEY', '')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境必须设置SECRET_KEY
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-please-change'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'production-jwt-secret-please-change'
    
    # 生产环境优先使用 PostgreSQL 环境变量，没有则使用兼容库
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)  # 确保数据目录存在
    DATABASE_PATH = os.path.abspath(os.path.join(DATA_DIR, 'logistics.db'))
    # 将Windows路径转换为SQLite兼容的URL格式
    DATABASE_PATH_FOR_URL = DATABASE_PATH.replace('\\', '/')
    import urllib.parse
    ENCODED_PATH = urllib.parse.quote(DATABASE_PATH_FOR_URL, safe='/')
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('POSTGRES_DATABASE_URL')
        or os.environ.get('DATABASE_URL')
        or f'sqlite:///{ENCODED_PATH}'
    )


class DockerConfig(Config):
    """Docker 环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

    # Docker/云部署优先使用 PostgreSQL，未配置时才退回兼容 SQLite。
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('POSTGRES_DATABASE_URL')
        or os.environ.get('DATABASE_URL')
        or 'sqlite:////app/data/logistics.db'
    )
    
    # CORS 配置
    CORS_ORIGINS = ['http://localhost', 'http://localhost:80', 'http://localhost:8080', 
                    'http://127.0.0.1', 'http://127.0.0.1:80', 'http://127.0.0.1:8080']


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
