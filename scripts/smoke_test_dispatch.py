#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dispatch 线上链路烟雾测试

验证智能调度核心接口链路：/auth/login → /dispatch/health → /dispatch/preview
用于快速确认线上调度服务是否健康、数据源是否接通真实物流明细（shipment_facts）。

用法：
    python scripts/smoke_test_dispatch.py
    BASE_URL=https://your-host/api python scripts/smoke_test_dispatch.py

环境变量（可选）：
    BASE_URL        接口根地址，默认 https://logistics-demo-yu.top/api
    SMOKE_USERNAME  登录用户名，默认 admin
    SMOKE_PASSWORD  登录密码，默认 admin123
    SMOKE_TOKEN     直接传入已有 JWT，可跳过登录步骤

注意：
    /dispatch/preview 默认会落库一条 dispatch_scenarios(status=preview) 记录用于回放，
    频繁运行会在 DB 累积 preview 场景，请按需清理。
"""

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.environ.get("BASE_URL", "https://logistics-demo-yu.top/api")
USERNAME = os.environ.get("SMOKE_USERNAME", "admin")
PASSWORD = os.environ.get("SMOKE_PASSWORD", "admin123")


def request_json(path, method="GET", token=None, payload=None, timeout=40):
    """发送 JSON 请求并返回 (status, parsed_body)。"""
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _solver_name(solver_value):
    """solver 在新结构里是算法名字符串(如 'balanced')；兼容旧 dict 写法。"""
    if isinstance(solver_value, str):
        return solver_value
    if isinstance(solver_value, dict):
        return solver_value.get("name") or solver_value.get("algorithm")
    return None


def main():
    try:
        # 1. 登录（或复用环境变量里的 token）
        token = os.environ.get("SMOKE_TOKEN")
        if token:
            print("login=skipped(uses SMOKE_TOKEN)")
        else:
            status, login = request_json(
                "/auth/login",
                method="POST",
                payload={"username": USERNAME, "password": PASSWORD},
            )
            token = login.get("access_token") or login.get("token")
            print(f"login_status={status}")
            print(f"login_has_token={bool(token)}")
            if not token:
                return 2

        # 2. 调度健康检查（health 的 orders/vehicles 嵌套在 order_sources/vehicle_source 下）
        health_status, health = request_json("/dispatch/health", token=token)
        order_sources = health.get("order_sources") or {}
        vehicle_source = health.get("vehicle_source") or {}
        legacy_orders = order_sources.get("orders") or {}
        fact_orders = order_sources.get("shipment_facts") or {}
        print(f"dispatch_health_status={health_status}")
        print(f"dispatch_health_source={health.get('data_source')}")
        print(f"dispatch_health_dispatchable_orders={health.get('dispatchable_orders')}")
        print(f"dispatch_health_orders_total={legacy_orders.get('total')}")
        print(f"dispatch_health_orders_dispatchable={legacy_orders.get('dispatchable')}")
        print(f"dispatch_health_facts_total={fact_orders.get('total')}")
        print(f"dispatch_health_facts_dispatchable={fact_orders.get('dispatchable')}")
        print(f"dispatch_health_vehicles_total={vehicle_source.get('vehicles_total')}")
        print(f"dispatch_health_vehicles_available={vehicle_source.get('available_vehicles')}")
        print(f"dispatch_health_provider_status={health.get('provider_status')}")
        print(f"dispatch_health_authenticity={health.get('authenticity_level')}")

        # 3. 调度预览（注意：会落库一条 preview 场景）
        preview_status, preview = request_json(
            "/dispatch/preview",
            method="POST",
            token=token,
            payload={
                "limit": 20,
                "data_source": "auto",
                "algorithm": "balanced",
                "use_precise_distance": False,
            },
        )
        summary = preview.get("summary") or {}
        diagnostics = preview.get("diagnostics") or {}
        reason_counts = diagnostics.get("reason_counts") or {}
        print(f"dispatch_preview_status={preview_status}")
        print(f"preview_success={preview.get('success')}")
        print(f"preview_solver={_solver_name(preview.get('solver'))}")
        print(f"preview_requested_solver={preview.get('requested_solver')}")
        print(f"preview_plans={len(preview.get('plans') or [])}")
        print(f"preview_assigned={summary.get('assigned_orders')}")
        print(f"preview_unassigned={summary.get('unassigned_orders')}")
        print(f"preview_distance_source={preview.get('distance_source')}")
        print(f"preview_provider_status={preview.get('provider_status')}")
        print(f"preview_authenticity={preview.get('authenticity_level')}")
        print(f"preview_solve_time_ms={preview.get('solve_time_ms')}")
        for key, value in reason_counts.items():
            print(f"unassigned_reason_{key}={value}")
        return 0

    except urllib.error.HTTPError as exc:
        print(f"http_error_status={exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:1200])
        return 1
    except Exception as exc:
        print(f"smoke_error={type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
