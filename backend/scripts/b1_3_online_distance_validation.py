#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
B1-3 在线验证脚本
===================

用途：
1. 登录后端获取 JWT
2. 调用真实距离验证接口 /api/amap/distance/validate
3. 调用缓存统计接口 /api/amap/distance/cache/stats
4. 输出在线验证结果

默认账号：admin / admin123
默认地址：http://127.0.0.1:5000

运行：
    py -3 backend\\scripts\\b1_3_online_distance_validation.py
"""

import json
import requests

BASE_URL = "http://127.0.0.1:5000"
USERNAME = "admin"
PASSWORD = "admin123"


def pretty(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def login():
    url = f"{BASE_URL}/api/auth/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }
    resp = requests.post(url, json=payload, timeout=15)
    return resp


def call_validate(token):
    url = f"{BASE_URL}/api/amap/distance/validate"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "origin": {
            "longitude": 116.397,
            "latitude": 39.908
        },
        "destination": {
            "longitude": 121.473,
            "latitude": 31.230
        },
        "strategy": 0,
        "use_amap": False
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    return resp


def call_cache_stats(token):
    url = f"{BASE_URL}/api/amap/distance/cache/stats"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    return resp


def main():
    print("=" * 60)
    print("B1-3 在线真实距离验证")
    print("=" * 60)
    print(f"BASE_URL: {BASE_URL}")
    print()

    # Step 1: 登录
    print("[Step 1] 登录获取 JWT...")
    try:
        login_resp = login()
        print(f"状态码: {login_resp.status_code}")
        login_data = login_resp.json()
        print(pretty(login_data))
    except Exception as e:
        print(f"[FAIL] 登录请求失败: {e}")
        return

    if login_resp.status_code != 200 or not login_data.get("success"):
        print("[FAIL] 登录失败，无法继续在线验证")
        return

    token = login_data.get("access_token")
    if not token:
        print("[FAIL] 未拿到 access_token")
        return

    print("[OK] 登录成功")
    print()

    # Step 2: 真实距离验证接口
    print("[Step 2] 调用 /api/amap/distance/validate ...")
    try:
        validate_resp = call_validate(token)
        print(f"状态码: {validate_resp.status_code}")
        validate_data = validate_resp.json()
        print(pretty(validate_data))
    except Exception as e:
        print(f"[FAIL] distance/validate 请求失败: {e}")
        return

    if validate_resp.status_code == 200 and validate_data.get("success"):
        print("[OK] 真实距离验证接口在线可用")
    else:
        print("[WARN] 真实距离验证接口返回异常")
    print()

    # Step 3: 缓存统计接口
    print("[Step 3] 调用 /api/amap/distance/cache/stats ...")
    try:
        stats_resp = call_cache_stats(token)
        print(f"状态码: {stats_resp.status_code}")
        stats_data = stats_resp.json()
        print(pretty(stats_data))
    except Exception as e:
        print(f"[FAIL] cache/stats 请求失败: {e}")
        return

    if stats_resp.status_code == 200 and stats_data.get("success"):
        print("[OK] 缓存统计接口在线可用")
    else:
        print("[WARN] 缓存统计接口返回异常")
    print()

    print("=" * 60)
    print("B1-3 在线验证脚本执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
