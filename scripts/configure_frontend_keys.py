"""配置前端高德 key 到 frontend/.env.local（VITE_AMAP_KEY / VITE_AMAP_SECURITY_KEY）。

用法: backend/.venv/Scripts/python.exe scripts/configure_frontend_keys.py
只打印长度，不输出 key 值。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path(r"C:\Users\Administrator\Desktop\各API密钥")
ENV_FILE = ROOT / "frontend" / ".env.local"
SOURCE = DESKTOP / "高德地图前端API key.txt"


def main() -> None:
    if not SOURCE.exists():
        print(f"[ERROR] source not found: {SOURCE}")
        return
    raw = SOURCE.read_text(encoding="utf-8").strip()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    key = lines[0] if lines else ""
    security = lines[1] if len(lines) > 1 else ""
    if not security and "," in key:
        parts = key.split(",", 1)
        key, security = parts[0].strip(), parts[1].strip()
    if not key:
        print("[ERROR] empty key")
        return

    text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    for name, val in (("VITE_AMAP_KEY", key), ("VITE_AMAP_SECURITY_KEY", security)):
        pattern = re.compile(rf"^{name}=.*$", re.M)
        if pattern.search(text):
            text = pattern.sub(f"{name}={val}", text)
        else:
            text += f"\n{name}={val}"
        print(f"  ok {name} (len={len(val)})")
    ENV_FILE.write_text(text, encoding="utf-8")
    print(f"DONE: {ENV_FILE.name}")


if __name__ == "__main__":
    main()
