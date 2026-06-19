#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地实测 dispatch authenticity —— 连本地 PG，调 orchestration service，不启动 HTTP。
用于验证数据补全 / 距离优化后的 authenticity 与 solve_time。

用法：
    # 方式1：环境变量（推荐）
    set POSTGRES_DATABASE_URL=postgresql://...
    set AMAP_SERVICE_KEY=高德后端key
    python scripts/localtest_dispatch.py

    # 方式2：本机桌面配置文件自动 fallback
"""

import os
import pathlib
import re
import sys

BACKEND = pathlib.Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(str(BACKEND))

os.environ.setdefault("DISABLE_ML_ROUTES", "1")
os.environ.setdefault("FLASK_ENV", "development")

# POSTGRES_DATABASE_URL 优先环境变量，fallback 桌面启动文件
if not os.environ.get("POSTGRES_DATABASE_URL"):
    startup = pathlib.Path(r"C:\Users\Administrator\Desktop\物流路径规划系统项目启动方式.txt")
    if startup.exists():
        text = startup.read_text(encoding="utf-8")
        m = re.search(r'POSTGRES_DATABASE_URL="([^"]+)"', text)
        if m:
            os.environ["POSTGRES_DATABASE_URL"] = m.group(1)

# AMAP_SERVICE_KEY 优先环境变量，fallback 桌面密钥文件
if not os.environ.get("AMAP_SERVICE_KEY"):
    key_file = pathlib.Path(r"C:\Users\Administrator\Desktop\各API密钥\高德地图后端API key.txt")
    if key_file.exists():
        try:
            os.environ["AMAP_SERVICE_KEY"] = key_file.read_text(encoding="utf-8").splitlines()[0].strip()
        except Exception:
            pass

from app import create_app
from app.services.dispatch_orchestration_service import get_dispatch_orchestration_service


def main():
    app = create_app()
    with app.app_context():
        svc = get_dispatch_orchestration_service()

        print("=== HEALTH ===")
        h = svc.health()
        print("  data_source:", h.get("data_source"))
        print("  authenticity:", h.get("authenticity_level"))
        print("  provider_status:", h.get("provider_status"))
        print("  dispatchable_orders:", h.get("dispatchable_orders"))
        vs = h.get("vehicle_source") or {}
        print("  vehicles_available:", vs.get("available_vehicles"))

        print("\n=== PREVIEW (use_precise_distance=True) ===")
        r = svc.preview(
            {"limit": 20, "data_source": "auto", "algorithm": "balanced", "use_precise_distance": True},
            user_id=1, persist=False,
        )
        print("  authenticity:", r.get("authenticity_level"))
        print("  distance_source:", r.get("distance_source"))
        print("  provider_status:", r.get("provider_status"))
        print("  fallback_reason:", r.get("fallback_reason"))
        print("  assigned:", r["summary"]["assigned_orders"])
        print("  unassigned:", r["summary"]["unassigned_orders"])
        print("  solve_time_ms:", r.get("solve_time_ms"))

        print("\n=== PREVIEW (use_precise_distance=False, 对比) ===")
        r2 = svc.preview(
            {"limit": 20, "data_source": "auto", "algorithm": "balanced", "use_precise_distance": False},
            user_id=1, persist=False,
        )
        print("  authenticity:", r2.get("authenticity_level"))
        print("  distance_source:", r2.get("distance_source"))


if __name__ == "__main__":
    main()
