"""验证高德/天地图 key 配置 + provider 真实可用。

用法（项目根目录）:
    backend/.venv/Scripts/python.exe scripts/verify_providers.py

只打印 key 长度与 provider 布尔状态，绝不输出 key 值。
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
    keys = ["AMAP_WEB_KEY", "AMAP_SERVICE_KEY", "TIANDITU_BROWSER_KEY", "TIANDITU_SERVER_KEY"]
    print("=== key configured (len only, values never printed) ===")
    for k in keys:
        v = os.environ.get(k, "")
        print(f"  {k}: {'len=' + str(len(v)) if v else 'MISSING'}")

    print("=== amap geocode smoke (合肥市包河区) ===")
    try:
        from app.services.amap_service import get_amap_service
        result = get_amap_service().geocode("安徽省合肥市包河区", city="合肥")
        ok = bool(getattr(result, "success", False))
        print(f"  success={ok} provider_status={getattr(result, 'provider_status', None)}")
        if ok:
            print(f"  lon={getattr(result,'longitude',None)} lat={getattr(result,'latitude',None)} addr={getattr(result,'formatted_address',None)}")
        else:
            print(f"  fallback_reason={getattr(result, 'fallback_reason', None)}")
    except Exception as exc:
        print(f"  ERROR: {exc.__class__.__name__}: {exc}")

    print("=== tianditu geocode smoke (合肥市包河区) ===")
    try:
        from app.services.tianditu_service import get_tianditu_service
        result = get_tianditu_service().geocode("安徽省合肥市包河区", city="合肥")
        ok = bool(getattr(result, "success", False))
        print(f"  success={ok} provider_status={getattr(result, 'provider_status', None)}")
        if ok:
            print(f"  lon={getattr(result,'longitude',None)} lat={getattr(result,'latitude',None)}")
        else:
            print(f"  fallback_reason={getattr(result, 'fallback_reason', None)}")
    except Exception as exc:
        print(f"  ERROR: {exc.__class__.__name__}: {exc}")


if __name__ == "__main__":
    main()
