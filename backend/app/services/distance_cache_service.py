#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
距离缓存服务
=============

将高德批量距离 API 结果缓存到 SQLite，避免重复调用。

核心设计：
- 缓存键：origin_lng, origin_lat, dest_lng, dest_lat, strategy
- 命中缓存直接返回，未命中则调用高德 API 后写入
- 缓存有效期：7 天（路况会变化）
- 修正系数：Haversine 直线距离 × 1.3 作为兜底

作者: 小彩
日期: 2026-05-04
"""

import math
import time
import logging
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class CachedDistance:
    """缓存距离记录"""
    id: int = 0
    origin_lng: float = 0.0
    origin_lat: float = 0.0
    dest_lng: float = 0.0
    dest_lat: float = 0.0
    strategy: int = 0
    distance_m: int = 0        # 高德返回的驾车距离（米）
    duration_s: int = 0        # 高德返回的驾车时间（秒）
    source: str = ''           # 'amap' | 'haversine_corrected'
    correction_factor: float = 0.0  # 使用的修正系数
    created_at: float = 0.0
    expires_at: float = 0.0


# 缓存有效期（秒）
CACHE_TTL = 7 * 24 * 3600  # 7 天

# Haversine 修正系数（直线距离 → 实际道路距离的修正）
# 中国公路经验值：1.3 是城市间公路的合理修正系数
HAVERSINE_CORRECTION_FACTOR = 1.3

# 高德批量距离 API 单次最大支持点对数
BATCH_MAX_ORIGINS = 50
BATCH_MAX_DESTINATIONS = 50

# 渐进升级：当缓存里已有近似值时，每次矩阵构建最多尝试升级这么多个点对
MAX_AMAP_UPGRADE_PAIRS_PER_CALL = 3

# AMap 矩阵接口偶发返回异常小距离时，必须与直线距离做基本物理校验。
MIN_ROAD_TO_STRAIGHT_RATIO = 0.6


class DistanceCacheService:
    """
    距离缓存服务
    
    三层距离获取策略：
    1. 查 SQLite 缓存（命中 → 直接返回）
    2. 调高德批量距离 API（写入缓存）
    3. 兜底：Haversine × 修正系数（写入缓存，标记 source='haversine_corrected'）
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'distance_cache.db')
        
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn
    
    @contextmanager
    def _connection(self):
        """上下文管理器方式获取连接"""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """初始化数据库表"""
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS distance_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin_lng REAL NOT NULL,
                    origin_lat REAL NOT NULL,
                    dest_lng REAL NOT NULL,
                    dest_lat REAL NOT NULL,
                    strategy INTEGER NOT NULL DEFAULT 0,
                    distance_m INTEGER NOT NULL,
                    duration_s INTEGER NOT NULL,
                    source TEXT NOT NULL DEFAULT 'unknown',
                    correction_factor REAL NOT NULL DEFAULT 0.0,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    
                    UNIQUE(origin_lng, origin_lat, dest_lng, dest_lat, strategy)
                )
            """)
            
            # 索引：加速查询
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_lookup 
                ON distance_cache(origin_lng, origin_lat, dest_lng, dest_lat, strategy)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_expires 
                ON distance_cache(expires_at)
            """)
        
        logger.info(f"距离缓存数据库已初始化: {self.db_path}")
    
    def _make_key_coords(
        self,
        lng: float, lat: float
    ) -> Tuple[float, float]:
        """坐标量化到 6 位小数（约 0.1 米精度），用于缓存键"""
        return (round(lng, 6), round(lat, 6))
    
    # ----------------------------------------------------------------
    # 缓存查询
    # ----------------------------------------------------------------
    
    def get_cached(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        strategy: int = 0
    ) -> Optional[CachedDistance]:
        """
        查询缓存
        
        Args:
            origin: (经度, 纬度)
            destination: (经度, 纬度)
            strategy: 高德路线策略
        
        Returns:
            缓存记录（未过期），或 None
        """
        o_lng, o_lat = self._make_key_coords(*origin)
        d_lng, d_lat = self._make_key_coords(*destination)
        now = time.time()
        
        conn = self._get_conn()
        row = conn.execute("""
            SELECT * FROM distance_cache
            WHERE origin_lng = ? AND origin_lat = ?
              AND dest_lng = ? AND dest_lat = ?
              AND strategy = ?
              AND expires_at > ?
            LIMIT 1
        """, (o_lng, o_lat, d_lng, d_lat, strategy, now)).fetchone()
        
        if row:
            return CachedDistance(
                id=row['id'],
                origin_lng=row['origin_lng'],
                origin_lat=row['origin_lat'],
                dest_lng=row['dest_lng'],
                dest_lat=row['dest_lat'],
                strategy=row['strategy'],
                distance_m=row['distance_m'],
                duration_s=row['duration_s'],
                source=row['source'],
                correction_factor=row['correction_factor'],
                created_at=row['created_at'],
                expires_at=row['expires_at']
            )
        return None
    
    def get_cached_batch(
        self,
        pairs: List[Tuple[Tuple[float, float], Tuple[float, float]]],
        strategy: int = 0
    ) -> Dict[int, CachedDistance]:
        """
        批量查询缓存
        
        Args:
            pairs: [(origin, destination), ...] 列表
            strategy: 路线策略
        
        Returns:
            {索引: CachedDistance} 命中的结果
        """
        results = {}
        now = time.time()
        conn = self._get_conn()
        
        for idx, (origin, destination) in enumerate(pairs):
            o_lng, o_lat = self._make_key_coords(*origin)
            d_lng, d_lat = self._make_key_coords(*destination)
            
            row = conn.execute("""
                SELECT * FROM distance_cache
                WHERE origin_lng = ? AND origin_lat = ?
                  AND dest_lng = ? AND dest_lat = ?
                  AND strategy = ?
                  AND expires_at > ?
                LIMIT 1
            """, (o_lng, o_lat, d_lng, d_lat, strategy, now)).fetchone()
            
            if row:
                results[idx] = CachedDistance(
                    id=row['id'],
                    origin_lng=row['origin_lng'],
                    origin_lat=row['origin_lat'],
                    dest_lng=row['dest_lng'],
                    dest_lat=row['dest_lat'],
                    strategy=row['strategy'],
                    distance_m=row['distance_m'],
                    duration_s=row['duration_s'],
                    source=row['source'],
                    correction_factor=row['correction_factor'],
                    created_at=row['created_at'],
                    expires_at=row['expires_at']
                )
        
        return results
    
    # ----------------------------------------------------------------
    # 缓存写入
    # ----------------------------------------------------------------
    
    def put_cached(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        distance_m: int,
        duration_s: int,
        source: str,
        strategy: int = 0,
        correction_factor: float = 0.0,
        ttl: float = CACHE_TTL
    ) -> None:
        """写入单条缓存"""
        o_lng, o_lat = self._make_key_coords(*origin)
        d_lng, d_lat = self._make_key_coords(*destination)
        now = time.time()
        
        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO distance_cache 
                    (origin_lng, origin_lat, dest_lng, dest_lat, strategy,
                     distance_m, duration_s, source, correction_factor,
                     created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                o_lng, o_lat, d_lng, d_lat, strategy,
                distance_m, duration_s, source, correction_factor,
                now, now + ttl
            ))
    
    def put_cached_batch(
        self,
        records: List[Dict],
        ttl: float = CACHE_TTL
    ) -> int:
        """
        批量写入缓存
        
        Args:
            records: [{
                'origin': (lng, lat),
                'destination': (lng, lat),
                'distance_m': int,
                'duration_s': int,
                'source': str,
                'strategy': int,
                'correction_factor': float
            }]
        
        Returns:
            写入条数
        """
        now = time.time()
        rows = []
        
        for rec in records:
            origin = rec['origin']
            dest = rec['destination']
            o_lng, o_lat = self._make_key_coords(*origin)
            d_lng, d_lat = self._make_key_coords(*dest)
            
            rows.append((
                o_lng, o_lat, d_lng, d_lat,
                rec.get('strategy', 0),
                rec['distance_m'],
                rec['duration_s'],
                rec.get('source', 'unknown'),
                rec.get('correction_factor', 0.0),
                now, now + ttl
            ))
        
        with self._connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO distance_cache 
                    (origin_lng, origin_lat, dest_lng, dest_lat, strategy,
                     distance_m, duration_s, source, correction_factor,
                     created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
        
        return len(rows)
    
    # ----------------------------------------------------------------
    # Haversine 兜底计算
    # ----------------------------------------------------------------
    
    @staticmethod
    def haversine_km(
        coord1: Tuple[float, float],
        coord2: Tuple[float, float]
    ) -> float:
        """
        Haversine 公式计算两点间直线距离（公里）
        
        Args:
            coord1: (经度, 纬度)
            coord2: (经度, 纬度)
        """
        R = 6371.0  # 地球半径（公里）
        lng1, lat1 = coord1
        lng2, lat2 = coord2
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    @staticmethod
    def corrected_distance_km(
        coord1: Tuple[float, float],
        coord2: Tuple[float, float],
        factor: float = HAVERSINE_CORRECTION_FACTOR
    ) -> float:
        """
        Haversine × 修正系数 → 估算实际道路距离（公里）
        
        修正系数 1.3 是中国公路的经验值：
        - 高速公路：1.1 ~ 1.2
        - 国道省道：1.2 ~ 1.4
        - 城市道路：1.3 ~ 1.6
        - 综合均值：1.3
        """
        return DistanceCacheService.haversine_km(coord1, coord2) * factor
    
    @staticmethod
    def estimate_duration_hours(
        distance_km: float,
        avg_speed_kmh: float = 60.0
    ) -> float:
        """根据距离估算行驶时间（小时）"""
        return distance_km / avg_speed_kmh
    
    # ----------------------------------------------------------------
    # 智能距离获取（核心方法）
    # ----------------------------------------------------------------
    
    def get_distance(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        strategy: int = 0,
        use_amap: bool = True
    ) -> Dict:
        """
        智能获取距离：缓存 → 高德 API → Haversine 兜底
        
        Args:
            origin: (经度, 纬度)
            destination: (经度, 纬度)
            strategy: 高德路线策略
            use_amap: 是否尝试调用高德 API
        
        Returns:
            {
                'distance_m': int,       # 距离（米）
                'distance_km': float,    # 距离（公里）
                'duration_s': int,       # 时间（秒）
                'duration_minutes': float,# 时间（分钟）
                'source': str,           # 'cache' | 'amap' | 'haversine_corrected'
                'is_exact': bool,        # 是否精确值
                'correction_factor': float
            }
        """
        # 1. 查缓存
        cached = self.get_cached(origin, destination, strategy)
        if cached:
            # 方案 A：当明确要求 use_amap=True 且缓存只是近似值时，尝试升级为精确值
            if cached.source == 'amap' or not use_amap:
                return {
                    'distance_m': cached.distance_m,
                    'distance_km': round(cached.distance_m / 1000, 2),
                    'duration_s': cached.duration_s,
                    'duration_minutes': round(cached.duration_s / 60, 1),
                    'source': 'cache',
                    'is_exact': cached.source == 'amap',
                    'correction_factor': cached.correction_factor
                }
            
            # cached.source == 'haversine_corrected' and use_amap=True
            try:
                amap_result = self._call_amap_distance(origin, destination, strategy)
                if amap_result:
                    self.put_cached(
                        origin, destination,
                        distance_m=amap_result['distance_m'],
                        duration_s=amap_result['duration_s'],
                        source='amap',
                        strategy=strategy,
                        correction_factor=0.0
                    )
                    return {
                        'distance_m': amap_result['distance_m'],
                        'distance_km': round(amap_result['distance_m'] / 1000, 2),
                        'duration_s': amap_result['duration_s'],
                        'duration_minutes': round(amap_result['duration_s'] / 60, 1),
                        'source': 'amap',
                        'is_exact': True,
                        'correction_factor': 0.0
                    }
            except Exception as e:
                logger.warning(f"近似缓存升级为高德精确距离失败，继续使用缓存值: {e}")
            
            return {
                'distance_m': cached.distance_m,
                'distance_km': round(cached.distance_m / 1000, 2),
                'duration_s': cached.duration_s,
                'duration_minutes': round(cached.duration_s / 60, 1),
                'source': 'cache',
                'is_exact': False,
                'correction_factor': cached.correction_factor
            }
        
        # 2. 尝试高德 API
        if use_amap:
            try:
                amap_result = self._call_amap_distance(origin, destination, strategy)
                if amap_result:
                    # 写入缓存
                    self.put_cached(
                        origin, destination,
                        distance_m=amap_result['distance_m'],
                        duration_s=amap_result['duration_s'],
                        source='amap',
                        strategy=strategy,
                        correction_factor=0.0
                    )
                    return {
                        'distance_m': amap_result['distance_m'],
                        'distance_km': round(amap_result['distance_m'] / 1000, 2),
                        'duration_s': amap_result['duration_s'],
                        'duration_minutes': round(amap_result['duration_s'] / 60, 1),
                        'source': 'amap',
                        'is_exact': True,
                        'correction_factor': 0.0
                    }
            except Exception as e:
                logger.warning(f"高德距离 API 调用失败，使用 Haversine 兜底: {e}")
        
        # 3. Haversine 兜底
        dist_km = self.corrected_distance_km(origin, destination)
        dist_m = int(dist_km * 1000)
        dur_hours = self.estimate_duration_hours(dist_km)
        dur_s = int(dur_hours * 3600)
        
        # 写入缓存
        self.put_cached(
            origin, destination,
            distance_m=dist_m,
            duration_s=dur_s,
            source='haversine_corrected',
            strategy=strategy,
            correction_factor=HAVERSINE_CORRECTION_FACTOR
        )
        
        return {
            'distance_m': dist_m,
            'distance_km': round(dist_km, 2),
            'duration_s': dur_s,
            'duration_minutes': round(dur_s / 60, 1),
            'source': 'haversine_corrected',
            'is_exact': False,
            'correction_factor': HAVERSINE_CORRECTION_FACTOR
        }
    
    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        strategy: int = 0,
        use_amap: bool = True
    ) -> Dict:
        """
        批量获取距离矩阵
        
        策略：
        1. 先批量查缓存
        2. 对未命中的调用高德批量 API
        3. 对高德失败的用 Haversine 兜底
        
        Args:
            origins: 起点列表 [(lng, lat), ...]
            destinations: 终点列表 [(lng, lat), ...]
            strategy: 路线策略
            use_amap: 是否使用高德 API
        
        Returns:
            {
                'matrix': [[{distance_m, duration_s, source, ...}, ...], ...],
                'cache_hits': int,
                'amap_calls': int,
                'haversine_fallbacks': int
            }
        """
        n_origins = len(origins)
        n_dests = len(destinations)
        
        # 构建所有点对
        all_pairs = []
        for i, o in enumerate(origins):
            for j, d in enumerate(destinations):
                all_pairs.append((i, j, o, d))
        
        # 1. 批量查缓存
        pair_keys = [(o, d) for _, _, o, d in all_pairs]
        cached_results = self.get_cached_batch(pair_keys, strategy)
        
        # 构建结果矩阵
        matrix = [[None] * n_dests for _ in range(n_origins)]
        cache_hits = 0
        
        missed_pairs = []  # 未命中的点对
        upgrade_pairs = []  # 已命中近似缓存、但允许尝试升级为精确值的点对
        
        cache_rejected_pairs = 0

        for idx, (i, j, origin, dest) in enumerate(all_pairs):
            if idx in cached_results:
                cached = cached_results[idx]
                cache_is_plausible = True
                if cached.source == 'amap':
                    cache_is_plausible = self._is_plausible_amap_distance(
                        origin,
                        dest,
                        cached.distance_m,
                    )
                
                # 方案 A：use_amap=True 时，近似缓存不直接视为最终命中，而是渐进升级
                if cached.source == 'amap' and not cache_is_plausible and use_amap:
                    matrix[i][j] = {
                        'distance_m': cached.distance_m,
                        'distance_km': round(cached.distance_m / 1000, 2),
                        'duration_s': cached.duration_s,
                        'duration_minutes': round(cached.duration_s / 60, 1),
                        'source': 'cache',
                        'is_exact': False,
                        'correction_factor': cached.correction_factor
                    }
                    cache_hits += 1
                    cache_rejected_pairs += 1
                    if i != j and len(upgrade_pairs) < MAX_AMAP_UPGRADE_PAIRS_PER_CALL:
                        upgrade_pairs.append((i, j, origin, dest))
                elif cached.source == 'amap' or not use_amap:
                    matrix[i][j] = {
                        'distance_m': cached.distance_m,
                        'distance_km': round(cached.distance_m / 1000, 2),
                        'duration_s': cached.duration_s,
                        'duration_minutes': round(cached.duration_s / 60, 1),
                        'source': 'cache',
                        'is_exact': cached.source == 'amap',
                        'correction_factor': cached.correction_factor
                    }
                    cache_hits += 1
                else:
                    # cached.source == 'haversine_corrected' and use_amap=True
                    matrix[i][j] = {
                        'distance_m': cached.distance_m,
                        'distance_km': round(cached.distance_m / 1000, 2),
                        'duration_s': cached.duration_s,
                        'duration_minutes': round(cached.duration_s / 60, 1),
                        'source': 'cache',
                        'is_exact': False,
                        'correction_factor': cached.correction_factor
                    }
                    cache_hits += 1
                    if i != j and len(upgrade_pairs) < MAX_AMAP_UPGRADE_PAIRS_PER_CALL:
                        upgrade_pairs.append((i, j, origin, dest))
            else:
                missed_pairs.append((i, j, origin, dest))

        candidate_amap_pairs = missed_pairs + upgrade_pairs

        
        # 2. 对未命中的调用高德批量 API
        amap_calls = 0
        haversine_fallbacks = 0
        
        amap_failure_reason = None
        amap_provider_status = None
        amap_attempted_pairs = 0
        amap_successes = 0
        amap_route_attempted_pairs = 0
        amap_route_successes = 0
        amap_rejected_pairs = 0
        distance_matrix_fallback_reason = None

        if candidate_amap_pairs and use_amap:
            amap_attempted_pairs = len(candidate_amap_pairs)
            amap_response = self._call_amap_batch_distance(
                candidate_amap_pairs, strategy
            )
            amap_results = amap_response.get('results') if amap_response else None
            amap_failure_reason = amap_response.get('fallback_reason') if amap_response else None
            amap_provider_status = amap_response.get('provider_status') if amap_response else None
            distance_matrix_fallback_reason = amap_failure_reason
            
            if amap_results:
                # 写入缓存
                cache_records = []
                for (i, j, origin, dest), result in zip(candidate_amap_pairs, amap_results):
                    if result is not None and not self._is_plausible_amap_distance(origin, dest, result['distance_m']):
                        result = None
                        amap_rejected_pairs += 1
                        distance_matrix_fallback_reason = (
                            distance_matrix_fallback_reason
                            or 'AMAP_DISTANCE_MATRIX_IMPLAUSIBLE_DISTANCE'
                        )
                    if result is None:
                        amap_route_attempted_pairs += 1
                        try:
                            route_result = self._call_amap_route_distance(origin, dest, strategy)
                        except Exception as e:
                            logger.warning(f"高德驾车路径规划兜底失败: {e}")
                            route_result = None
                        if route_result:
                            result = route_result
                            amap_route_successes += 1
                    if result is not None:
                        matrix[i][j] = {
                            'distance_m': result['distance_m'],
                            'distance_km': round(result['distance_m'] / 1000, 2),
                            'duration_s': result['duration_s'],
                            'duration_minutes': round(result['duration_s'] / 60, 1),
                            'source': result.get('source', 'amap'),
                            'is_exact': True,
                            'correction_factor': 0.0
                        }
                        cache_records.append({
                            'origin': origin,
                            'destination': dest,
                            'distance_m': result['distance_m'],
                            'duration_s': result['duration_s'],
                            'source': 'amap',
                            'strategy': strategy,
                            'correction_factor': 0.0
                        })
                        amap_calls += 1
                        amap_successes += 1
                    elif (i, j, origin, dest) in missed_pairs:
                        # 对真正未命中的点对，高德失败时才落回 Haversine
                        dist_km = self.corrected_distance_km(origin, dest)
                        dist_m = int(dist_km * 1000)
                        dur_s = int(self.estimate_duration_hours(dist_km) * 3600)
                        
                        matrix[i][j] = {
                            'distance_m': dist_m,
                            'distance_km': round(dist_km, 2),
                            'duration_s': dur_s,
                            'duration_minutes': round(dur_s / 60, 1),
                            'source': 'haversine_corrected',
                            'is_exact': False,
                            'correction_factor': HAVERSINE_CORRECTION_FACTOR
                        }
                        cache_records.append({
                            'origin': origin,
                            'destination': dest,
                            'distance_m': dist_m,
                            'duration_s': dur_s,
                            'source': 'haversine_corrected',
                            'strategy': strategy,
                            'correction_factor': HAVERSINE_CORRECTION_FACTOR
                        })
                        haversine_fallbacks += 1
                
                # 批量写入缓存
                if cache_records:
                    self.put_cached_batch(cache_records)
            else:
                # 高德批量 API 完全失败：逐对尝试驾车路径规划补 exact；
                # 仍失败时只对真正未命中的点对兜底，已有近似缓存的点保持原值。
                cache_records = []
                for i, j, origin, dest in candidate_amap_pairs:
                    amap_route_attempted_pairs += 1
                    try:
                        route_result = self._call_amap_route_distance(origin, dest, strategy)
                    except Exception as e:
                        logger.warning(f"高德驾车路径规划兜底失败: {e}")
                        route_result = None
                    if not route_result:
                        continue

                    matrix[i][j] = {
                        'distance_m': route_result['distance_m'],
                        'distance_km': round(route_result['distance_m'] / 1000, 2),
                        'duration_s': route_result['duration_s'],
                        'duration_minutes': round(route_result['duration_s'] / 60, 1),
                        'source': 'amap_route',
                        'is_exact': True,
                        'correction_factor': 0.0
                    }
                    cache_records.append({
                        'origin': origin,
                        'destination': dest,
                        'distance_m': route_result['distance_m'],
                        'duration_s': route_result['duration_s'],
                        'source': 'amap',
                        'strategy': strategy,
                        'correction_factor': 0.0
                    })
                    amap_calls += 1
                    amap_successes += 1
                    amap_route_successes += 1

                for i, j, origin, dest in missed_pairs:
                    if matrix[i][j] is not None:
                        continue
                    dist_km = self.corrected_distance_km(origin, dest)
                    dist_m = int(dist_km * 1000)
                    dur_s = int(self.estimate_duration_hours(dist_km) * 3600)
                    
                    matrix[i][j] = {
                        'distance_m': dist_m,
                        'distance_km': round(dist_km, 2),
                        'duration_s': dur_s,
                        'duration_minutes': round(dur_s / 60, 1),
                        'source': 'haversine_corrected',
                        'is_exact': False,
                        'correction_factor': HAVERSINE_CORRECTION_FACTOR
                    }
                    haversine_fallbacks += 1
                
                for i, j, origin, dest in missed_pairs:
                    if matrix[i][j] is not None:
                        continue
                    dist_km = self.corrected_distance_km(origin, dest)
                    dist_m = int(dist_km * 1000)
                    dur_s = int(self.estimate_duration_hours(dist_km) * 3600)
                    cache_records.append({
                        'origin': origin,
                        'destination': dest,
                        'distance_m': dist_m,
                        'duration_s': dur_s,
                        'source': 'haversine_corrected',
                        'strategy': strategy,
                        'correction_factor': HAVERSINE_CORRECTION_FACTOR
                    })
                if cache_records:
                    self.put_cached_batch(cache_records)
        elif missed_pairs:
            # 不使用高德，全部兜底
            cache_records = []
            for i, j, origin, dest in missed_pairs:
                dist_km = self.corrected_distance_km(origin, dest)
                dist_m = int(dist_km * 1000)
                dur_s = int(self.estimate_duration_hours(dist_km) * 3600)
                
                matrix[i][j] = {
                    'distance_m': dist_m,
                    'distance_km': round(dist_km, 2),
                    'duration_s': dur_s,
                    'duration_minutes': round(dur_s / 60, 1),
                    'source': 'haversine_corrected',
                    'is_exact': False,
                    'correction_factor': HAVERSINE_CORRECTION_FACTOR
                }
                haversine_fallbacks += 1
                
                cache_records.append({
                    'origin': origin,
                    'destination': dest,
                    'distance_m': dist_m,
                    'duration_s': dur_s,
                    'source': 'haversine_corrected',
                    'strategy': strategy,
                    'correction_factor': HAVERSINE_CORRECTION_FACTOR
                })
            if cache_records:
                self.put_cached_batch(cache_records)
        
        return {
            'matrix': matrix,
            'cache_hits': cache_hits,
            'amap_calls': amap_calls,
            'haversine_fallbacks': haversine_fallbacks,
            'total_pairs': len(all_pairs),
            'amap_attempted_pairs': amap_attempted_pairs,
            'amap_successes': amap_successes,
            'amap_route_attempted_pairs': amap_route_attempted_pairs,
            'amap_route_successes': amap_route_successes,
            'amap_rejected_pairs': amap_rejected_pairs,
            'cache_rejected_pairs': cache_rejected_pairs,
            'provider_status': amap_provider_status or ('ok' if not amap_failure_reason else 'degraded'),
            'fallback_reason': None if amap_successes > 0 else amap_failure_reason,
            'distance_matrix_fallback_reason': distance_matrix_fallback_reason,
        }
    
    # ----------------------------------------------------------------
    # 高德 API 调用
    # ----------------------------------------------------------------
    
    def _call_amap_distance(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        strategy: int = 0
    ) -> Optional[Dict]:
        """调用高德单对距离 API"""
        from app.services.amap_service import get_amap_service
        
        service = get_amap_service()
        result = service.distance_matrix([origin], [destination], strategy)
        
        if result.get('success') and result.get('results'):
            item = result['results'][0]
            distance_m = item.get('distance', 0)
            duration_s = item.get('duration', 0)
            
            # 高德返回 0 或负值表示无法计算
            if distance_m > 0:
                return {
                    'distance_m': distance_m,
                    'duration_s': duration_s
                }
        
        return None
    
    def _call_amap_batch_distance(
        self,
        pairs: List[Tuple[int, int, Tuple[float, float], Tuple[float, float]]],
        strategy: int = 0
    ) -> Dict:
        """
        调用高德批量距离 API
        
        高德 API 限制：
        - 单次最多 50 个起点 × 50 个终点
        - 超过时需要分批
        
        Args:
            pairs: [(matrix_i, matrix_j, origin, dest), ...]
            strategy: 路线策略
        
        Returns:
            与 pairs 等长的列表，每个元素为 Dict 或 None
        """
        from app.services.amap_service import get_amap_service
        
        if not pairs:
            return {
                'results': [],
                'provider_status': 'ok',
                'fallback_reason': None,
            }
        
        # 提取去重的起点和终点
        unique_origins = {}
        unique_dests = {}
        
        for i, j, origin, dest in pairs:
            o_key = self._make_key_coords(*origin)
            d_key = self._make_key_coords(*dest)
            if o_key not in unique_origins:
                unique_origins[o_key] = origin
            if d_key not in unique_dests:
                unique_dests[d_key] = dest
        
        origin_list = list(unique_origins.values())
        dest_list = list(unique_dests.values())
        
        # 分批调用（高德限制 50×50）
        all_results = {}
        
        service = get_amap_service()
        fallback_reason = None
        provider_status = 'ok'
        
        for o_start in range(0, len(origin_list), BATCH_MAX_ORIGINS):
            for d_start in range(0, len(dest_list), BATCH_MAX_DESTINATIONS):
                o_batch = origin_list[o_start:o_start + BATCH_MAX_ORIGINS]
                d_batch = dest_list[d_start:d_start + BATCH_MAX_DESTINATIONS]
                
                try:
                    result = service.distance_matrix(o_batch, d_batch, strategy)
                    
                    if result.get('success') and result.get('results'):
                        for item in result['results']:
                            o_idx = int(item.get('origin_id', 0)) - 1 + o_start
                            d_idx = int(item.get('dest_id', 0)) - 1 + d_start
                            distance_m = item.get('distance', 0)
                            duration_s = item.get('duration', 0)
                            
                            if distance_m > 0:
                                o_key = self._make_key_coords(*o_batch[
                                    int(item.get('origin_id', 1)) - 1
                                ])
                                d_key = self._make_key_coords(*d_batch[
                                    int(item.get('dest_id', 1)) - 1
                                ])
                                all_results[(o_key, d_key)] = {
                                    'distance_m': distance_m,
                                    'duration_s': duration_s
                                }
                    else:
                        provider_status = result.get('provider_status') or 'degraded'
                        fallback_reason = (
                            result.get('fallback_reason')
                            or result.get('error')
                            or result.get('info')
                            or 'AMAP_DISTANCE_MATRIX_FAILED'
                        )
                except Exception as e:
                    logger.warning(f"高德批量距离 API 调用失败: {e}")
                    provider_status = 'degraded'
                    fallback_reason = str(e)
                    continue
        
        # 按原始 pairs 顺序组装结果
        output = []
        for i, j, origin, dest in pairs:
            o_key = self._make_key_coords(*origin)
            d_key = self._make_key_coords(*dest)
            output.append(all_results.get((o_key, d_key)))
        
        if not all_results and not fallback_reason:
            provider_status = 'degraded'
            fallback_reason = 'AMAP_DISTANCE_MATRIX_RETURNED_NO_RESULTS'

        return {
            'results': output,
            'provider_status': provider_status,
            'fallback_reason': fallback_reason,
        }

    def _is_plausible_amap_distance(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        distance_m: int,
    ) -> bool:
        """Basic sanity guard for provider distances before treating them as exact."""
        if self._make_key_coords(*origin) == self._make_key_coords(*destination):
            return distance_m == 0

        straight_m = self.haversine_km(origin, destination) * 1000
        if straight_m <= 1000:
            return distance_m > 0

        return distance_m >= straight_m * MIN_ROAD_TO_STRAIGHT_RATIO

    def _call_amap_route_distance(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        strategy: int = 0,
    ) -> Optional[Dict]:
        """调用高德驾车路径规划作为矩阵接口失败后的精确道路距离兜底。"""
        if self._make_key_coords(*origin) == self._make_key_coords(*destination):
            return None

        from app.services.amap_service import get_amap_service

        service = get_amap_service()
        result = service.driving_route(
            origin,
            destination,
            strategy=strategy,
            show_traffic=False,
        )

        if getattr(result, 'success', False) and getattr(result, 'distance', 0) > 0:
            return {
                'distance_m': int(result.distance),
                'duration_s': int(result.duration or 0),
                'source': 'amap_route',
            }

        return None
    
    # ----------------------------------------------------------------
    # 缓存管理
    # ----------------------------------------------------------------
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        now = time.time()
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM distance_cache WHERE expires_at <= ?", (now,)
            )
            return cursor.rowcount
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        conn = self._get_conn()
        
        total = conn.execute("SELECT COUNT(*) FROM distance_cache").fetchone()[0]
        amap_count = conn.execute(
            "SELECT COUNT(*) FROM distance_cache WHERE source = 'amap'"
        ).fetchone()[0]
        haversine_count = conn.execute(
            "SELECT COUNT(*) FROM distance_cache WHERE source = 'haversine_corrected'"
        ).fetchone()[0]
        expired = conn.execute(
            "SELECT COUNT(*) FROM distance_cache WHERE expires_at <= ?", (time.time(),)
        ).fetchone()[0]
        
        return {
            'total_entries': total,
            'amap_exact': amap_count,
            'haversine_corrected': haversine_count,
            'expired': expired,
            'db_path': self.db_path
        }
    
    def clear_all(self) -> int:
        """清空所有缓存"""
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM distance_cache")
            return cursor.rowcount


# 单例
_distance_cache = None


def get_distance_cache() -> DistanceCacheService:
    """获取距离缓存服务实例"""
    global _distance_cache
    if _distance_cache is None:
        _distance_cache = DistanceCacheService()
    return _distance_cache
