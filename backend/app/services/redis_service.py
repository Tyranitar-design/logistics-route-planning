"""
Redis 缓存服务
- 热门路线排行
- 车辆状态缓存
- 订单计数器
- 实时统计缓存
"""

import redis
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Redis 配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Redis 客户端（延迟初始化）
_redis_client = None


def get_redis_client():
    """获取 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            # 测试连接
            _redis_client.ping()
            print(f"✅ Redis 连接成功: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            print(f"⚠️ Redis 连接失败: {e}")
            _redis_client = None
    return _redis_client


# ============== 热门路线排行 ==============

def record_route_access(route_id: str, route_name: str):
    """
    记录路线访问（用于热门排行）
    
    Args:
        route_id: 路线ID
        route_name: 路线名称
    """
    client = get_redis_client()
    if not client:
        return
    
    key = "logistics:popular_routes"
    
    # 记录路线名称
    client.hset("logistics:route_names", route_id, route_name)
    
    # 增加访问计数
    client.zincrby(key, 1, route_id)
    
    # 设置过期时间（7天）
    client.expire(key, 7 * 24 * 60 * 60)


def get_popular_routes(limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取热门路线排行
    
    Args:
        limit: 返回数量
    
    Returns:
        [{"route_id": "xxx", "route_name": "xxx", "score": 100}, ...]
    """
    client = get_redis_client()
    if not client:
        return []
    
    key = "logistics:popular_routes"
    
    # 获取排行榜
    routes = client.zrevrange(key, 0, limit - 1, withscores=True)
    
    result = []
    for route_id, score in routes:
        route_name = client.hget("logistics:route_names", route_id) or route_id
        result.append({
            "route_id": route_id,
            "route_name": route_name,
            "score": int(score)
        })
    
    return result


# ============== 车辆状态缓存 ==============

def cache_vehicle_status(vehicle_id: int, status: dict, expire: int = 300):
    """
    缓存车辆状态
    
    Args:
        vehicle_id: 车辆ID
        status: 状态字典
        expire: 过期时间（秒），默认5分钟
    """
    client = get_redis_client()
    if not client:
        return
    
    key = f"logistics:vehicle:{vehicle_id}"
    client.setex(key, expire, json.dumps(status, ensure_ascii=False))


def get_vehicle_status(vehicle_id: int) -> Optional[dict]:
    """
    获取车辆缓存状态
    
    Args:
        vehicle_id: 车辆ID
    
    Returns:
        状态字典或None
    """
    client = get_redis_client()
    if not client:
        return None
    
    key = f"logistics:vehicle:{vehicle_id}"
    data = client.get(key)
    
    if data:
        return json.loads(data)
    return None


def get_all_vehicle_statuses() -> List[Dict[str, Any]]:
    """获取所有缓存的车辆状态"""
    client = get_redis_client()
    if not client:
        return []
    
    keys = client.keys("logistics:vehicle:*")
    result = []
    
    for key in keys:
        data = client.get(key)
        if data:
            vehicle_id = key.split(":")[-1]
            status = json.loads(data)
            status["vehicle_id"] = int(vehicle_id)
            result.append(status)
    
    return result


# ============== 订单计数器 ==============

def increment_order_count(region: str = "total"):
    """
    增加订单计数
    
    Args:
        region: 区域名称，"total" 表示总计
    """
    client = get_redis_client()
    if not client:
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 日计数
    client.incr(f"logistics:orders:{today}:{region}")
    
    # 总计数
    client.incr(f"logistics:orders:total:{region}")


def get_order_count(region: str = "total", date: str = None) -> int:
    """
    获取订单计数
    
    Args:
        region: 区域名称
        date: 日期，None表示今日，"total"表示总计
    
    Returns:
        订单数量
    """
    client = get_redis_client()
    if not client:
        return 0
    
    if date == "total":
        key = f"logistics:orders:total:{region}"
    else:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        key = f"logistics:orders:{target_date}:{region}"
    
    count = client.get(key)
    return int(count) if count else 0


# ============== 实时统计缓存 ==============

def cache_dashboard_stats(stats: dict, expire: int = 60):
    """
    缓存仪表盘统计数据
    
    Args:
        stats: 统计数据字典
        expire: 过期时间（秒），默认1分钟
    """
    client = get_redis_client()
    if not client:
        return
    
    key = "logistics:dashboard_stats"
    client.setex(key, expire, json.dumps(stats, ensure_ascii=False))


def get_cached_dashboard_stats() -> Optional[dict]:
    """
    获取缓存的仪表盘统计数据
    
    Returns:
        统计数据字典或None
    """
    client = get_redis_client()
    if not client:
        return None
    
    key = "logistics:dashboard_stats"
    data = client.get(key)
    
    if data:
        return json.loads(data)
    return None


# ============== 搜索历史 ==============

def add_search_history(user_id: int, query: str, max_size: int = 20):
    """
    添加搜索历史
    
    Args:
        user_id: 用户ID
        query: 搜索词
        max_size: 最大保存数量
    """
    client = get_redis_client()
    if not client:
        return
    
    key = f"logistics:search_history:{user_id}"
    
    # 移除旧记录
    client.lrem(key, 0, query)
    
    # 添加到头部
    client.lpush(key, query)
    
    # 限制数量
    client.ltrim(key, 0, max_size - 1)
    
    # 设置过期（30天）
    client.expire(key, 30 * 24 * 60 * 60)


def get_search_history(user_id: int, limit: int = 10) -> List[str]:
    """
    获取搜索历史
    
    Args:
        user_id: 用户ID
        limit: 返回数量
    
    Returns:
        搜索词列表
    """
    client = get_redis_client()
    if not client:
        return []
    
    key = f"logistics:search_history:{user_id}"
    return client.lrange(key, 0, limit - 1)


# ============== 连接状态 ==============

def is_redis_connected() -> bool:
    """检查 Redis 是否连接"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.ping()
        return True
    except:
        return False


def get_redis_info() -> dict:
    """获取 Redis 信息"""
    client = get_redis_client()
    if not client:
        return {"connected": False}
    
    try:
        info = client.info()
        return {
            "connected": True,
            "version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace": info.get("db0", {}).get("keys", 0) if info.get("db0") else 0
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
