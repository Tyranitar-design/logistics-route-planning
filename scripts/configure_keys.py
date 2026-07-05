"""配置高德/天地图 API key 到 backend/.env.local。

读取桌面 key 文件，写入被 .gitignore 忽略的 .env.local。
只打印 key 长度，绝不输出 key 值。

用法（在项目根目录）:
    backend/.venv/Scripts/python.exe scripts/configure_keys.py
"""

from __future__ import annotations

import re
from pathlib import Path

DESKTOP = Path(r"C:\Users\Administrator\Desktop\各API密钥")
ENV_FILE = Path(__file__).resolve().parents[1] / "backend" / ".env.local"

MAPPING = {
    "AMAP_WEB_KEY": "高德地图前端API key.txt",
    "AMAP_SERVICE_KEY": "高德地图后端API key.txt",
    "TIANDITU_BROWSER_KEY": "天地图浏览器端API.txt",
    "TIANDITU_SERVER_KEY": "天地图服务器端API.txt",
}


def main() -> None:
    text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    for key, fname in MAPPING.items():
        src = DESKTOP / fname
        if not src.exists():
            print(f"MISSING: {fname}")
            continue
        val = src.read_text(encoding="utf-8").strip()
        pattern = re.compile(rf"^{key}=.*$", re.M)
        if pattern.search(text):
            text = pattern.sub(f"{key}={val}", text)
        else:
            text += f"\n{key}={val}"
        print(f"ok {key} <- {fname} (len={len(val)})")  # 只打印长度，不打印值
    ENV_FILE.write_text(text, encoding="utf-8")
    print(f"DONE: keys written to {ENV_FILE.name}")


if __name__ == "__main__":
    main()
