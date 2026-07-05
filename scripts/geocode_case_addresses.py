"""批量 geocoding C 端 region 名 + 货运机场城市名，缓存到 case_food_geocoding_cache。

用法（项目根目录）:
    backend/.venv/Scripts/python.exe scripts/geocode_case_addresses.py

跑完后 c2c_clusters / multimodal 读缓存，authenticity C→A。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def load_env_local() -> None:
    env = BACKEND / ".env.local"
    if not env.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env, override=True)
    except ImportError:
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k] = v


def main() -> None:
    load_env_local()
    from app import create_app
    from app.services.food_supply_case_service import get_food_supply_case_service

    app = create_app("development")
    with app.app_context():
        svc = get_food_supply_case_service()
        result = svc.geocode_case_regions({"persist": True, "provider": "amap"})
        s = result["summary"]
        print("=== geocode_case_regions ===")
        print(f"  total: {s['total']}")
        print(f"  resolved: {s['resolved']}")
        print(f"  cached: {s['cached']}")
        print(f"  needs_geocoding: {s['needs_geocoding']}")
        print(f"  authenticity: {result['authenticity_level']}")
        if result.get("fallback_reason"):
            print(f"  fallback: {result['fallback_reason']}")

        clusters = svc.c2c_clusters({"cluster_limit": 40})
        a_count = sum(1 for c in clusters["clusters"] if c.get("cluster_authenticity_level") == "A")
        c_count = sum(1 for c in clusters["clusters"] if c.get("cluster_authenticity_level") == "C")
        print("=== c2c_clusters after geocoding ===")
        print(f"  total clusters: {clusters['summary']['cluster_count']}")
        print(f"  A-level (real geocoded): {a_count}")
        print(f"  C-level (local fallback): {c_count}")


if __name__ == "__main__":
    main()
