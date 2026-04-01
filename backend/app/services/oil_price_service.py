#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
油价查询服务（简化版，不依赖数据库）
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import random

logger = logging.getLogger(__name__)


class OilPriceService:
    """油价查询服务（简化版，使用模拟数据）"""

    # 全国平均油价（基准）
    BASE_PRICES = {
        "0": {"name": "0号柴油", "base_price": 7.45},
        "92": {"name": "92号汽油", "base_price": 7.82},
        "95": {"name": "95号汽油", "base_price": 8.33},
        "98": {"name": "98号汽油", "base_price": 9.50}
    }

    # 省份价格系数
    PROVINCE_FACTORS = {
        "北京": 1.02, "上海": 1.03, "广东": 1.05, "江苏": 1.00,
        "浙江": 1.02, "山东": 0.98, "河南": 0.96, "四川": 1.03,
        "湖北": 0.97, "湖南": 0.98, "福建": 1.01, "辽宁": 0.97,
        "陕西": 0.96, "河北": 0.95, "山西": 0.94, "安徽": 0.96,
        "江西": 0.95, "黑龙江": 0.98, "吉林": 0.99,
        "甘肃": 0.95, "云南": 1.02, "贵州": 0.98, "海南": 1.08,
        "青海": 0.94, "内蒙古": 0.93, "广西": 1.00,
        "西藏": 0.92, "宁夏": 0.93, "新疆": 0.91,
        "重庆": 1.01, "天津": 1.00,
    }

    def get_current_prices(self, province: str = "北京") -> Dict[str, Any]:
        """获取当前油价"""
        factor = self.PROVINCE_FACTORS.get(province, 1.0)
        now = datetime.now()
        
        result = {}
        for fuel_type, info in self.BASE_PRICES.items():
            price = round(info["base_price"] * factor + random.uniform(-0.1, 0.1), 2)
            result[fuel_type] = {
                "name": info["name"],
                "price": price,
                "update_time": now.isoformat(),
                "source": "simulated"
            }
        
        return {
            "success": True,
            "province": province,
            "prices": result,
            "update_time": now.isoformat()
        }

    def get_price_history(self, province: str = "北京", days: int = 30) -> List[Dict]:
        """获取油价历史趋势"""
        factor = self.PROVINCE_FACTORS.get(province, 1.0)
        history = []
        
        for i in range(days):
            date = datetime.now() - __import__('datetime').timedelta(days=i)
            # 模拟价格波动
            base_variation = random.uniform(-0.3, 0.3)
            
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "fuel_type": "0",
                "fuel_type_name": "0号柴油",
                "price": round(7.45 * factor + base_variation, 2),
                "province": province
            })
        
        return history

    def calculate_fuel_cost(
        self,
        distance_km: float,
        fuel_type: str = "0",
        province: str = "北京",
        consumption: float = None
    ) -> Dict[str, Any]:
        """计算燃油成本"""
        # 获取当前油价
        prices = self.get_current_prices(province)
        price_data = prices.get("prices", {}).get(fuel_type, {})
        
        if price_data:
            price = price_data.get("price", 7.5)
        else:
            base_info = self.BASE_PRICES.get(fuel_type, {"name": fuel_type, "base_price": 7.5})
            price = base_info["base_price"]

        # 默认油耗（升/百公里）
        if consumption is None:
            consumption = 30 if fuel_type == "0" else 25

        # 计算成本
        fuel_needed = (distance_km / 100) * consumption
        cost = fuel_needed * price

        return {
            "distance_km": distance_km,
            "fuel_type": fuel_type,
            "fuel_type_name": self.BASE_PRICES.get(fuel_type, {}).get("name", fuel_type),
            "price_per_liter": price,
            "consumption_per_100km": consumption,
            "fuel_needed_liters": round(fuel_needed, 2),
            "total_cost": round(cost, 2),
            "province": province,
            "update_time": datetime.now().isoformat()
        }

    def get_supported_provinces(self) -> List[str]:
        """获取支持的省份列表"""
        return list(self.PROVINCE_FACTORS.keys())

    def get_fuel_types(self) -> List[Dict[str, str]]:
        """获取油品类型列表"""
        return [
            {"code": "0", "name": "0号柴油"},
            {"code": "92", "name": "92号汽油"},
            {"code": "95", "name": "95号汽油"},
            {"code": "98", "name": "98号汽油"}
        ]

    def refresh_cache(self) -> Dict[str, Any]:
        """刷新缓存"""
        return {
            "success": True,
            "message": "油价数据已刷新（模拟数据）"
        }


# 单例实例
_oil_price_service_instance = None


def get_oil_price_service() -> OilPriceService:
    """获取油价服务实例"""
    global _oil_price_service_instance
    if _oil_price_service_instance is None:
        _oil_price_service_instance = OilPriceService()
    return _oil_price_service_instance
