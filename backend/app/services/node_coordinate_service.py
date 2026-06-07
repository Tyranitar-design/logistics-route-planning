#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
节点坐标治理服务

负责：
1. 构造更稳健的地理编码查询候选
2. 逐候选调用高德地理编码
3. 输出可追踪的解析尝试信息
"""

from __future__ import annotations

from typing import Dict, List


NOISE_TOKENS = [
    "（由真实运单网络自动生成）",
    "(由真实运单网络自动生成)",
    "物流节点",
]


CITY_ALIAS_MAP = {
    "澳门特别行政区": ["澳门"],
    "秀英区": ["海口秀英区", "海南省海口市秀英区"],
    "乐清": ["温州乐清", "浙江省温州市乐清市"],
    "成县": ["陇南成县", "甘肃省陇南市成县"],
}


def _clean_text(value: str | None) -> str:
    if not value:
        return ""

    cleaned = value.strip()
    for token in NOISE_TOKENS:
        cleaned = cleaned.replace(token, "")
    return " ".join(cleaned.split()).strip()


def build_resolution_candidates(node) -> List[str]:
    """
    为节点构造从高置信到低置信的地理编码查询候选。
    """
    city = _clean_text(getattr(node, "city", None))
    province = _clean_text(getattr(node, "province", None))
    district = _clean_text(getattr(node, "district", None))
    address = _clean_text(getattr(node, "address", None))
    name = _clean_text(getattr(node, "name", None))

    base_name = name
    for token in NOISE_TOKENS:
        base_name = base_name.replace(token, "")
    base_name = base_name.strip()

    candidates: List[str] = []

    def add(value: str | None):
        value = _clean_text(value)
        if value and value not in candidates:
            candidates.append(value)

    add(city)
    add(district)
    add(address)
    add(base_name)

    if city and district:
        add(f"{city}{district}")
    if city and base_name:
        add(f"{city}{base_name}")
    if province and city:
        add(f"{province}{city}")
    if province and city and district:
        add(f"{province}{city}{district}")
    if province and city and base_name:
        add(f"{province}{city}{base_name}")

    for key in [city, district, base_name]:
        if key and key in CITY_ALIAS_MAP:
            for alias in CITY_ALIAS_MAP[key]:
                add(alias)

    return candidates


def resolve_node_coordinates(node, amap_service) -> Dict:
    """
    按候选查询串逐步尝试解析节点坐标。
    """
    candidates = build_resolution_candidates(node)
    attempts = []
    city_hint = _clean_text(getattr(node, "city", None)) or _clean_text(getattr(node, "province", None)) or None

    last_failure = None
    for candidate in candidates:
        result = amap_service.geocode(candidate, city_hint)
        attempts.append({
            "query": candidate,
            "success": bool(result.success),
            "provider_status": getattr(result, "provider_status", None),
            "fallback_reason": getattr(result, "fallback_reason", None),
            "error": getattr(result, "error", None),
        })

        if result.success:
            return {
                "success": True,
                "longitude": result.longitude,
                "latitude": result.latitude,
                "formatted_address": result.formatted_address,
                "province": result.province,
                "city": result.city,
                "district": result.district,
                "provider": result.provider,
                "provider_status": result.provider_status,
                "degraded": result.degraded,
                "fallback_reason": result.fallback_reason,
                "authenticity": result.authenticity,
                "resolution_query_used": candidate,
                "resolution_attempts": attempts,
            }

        last_failure = result

    return {
        "success": False,
        "error": getattr(last_failure, "error", "AMAP_GEOCODE_EMPTY") if last_failure else "AMAP_GEOCODE_EMPTY",
        "provider": getattr(last_failure, "provider", "amap") if last_failure else "amap",
        "provider_status": getattr(last_failure, "provider_status", "degraded") if last_failure else "degraded",
        "degraded": getattr(last_failure, "degraded", True) if last_failure else True,
        "fallback_reason": getattr(last_failure, "fallback_reason", "AMAP_GEOCODE_EMPTY") if last_failure else "AMAP_GEOCODE_EMPTY",
        "authenticity": getattr(last_failure, "authenticity", None) if last_failure else None,
        "resolution_query_used": None,
        "resolution_attempts": attempts,
    }
