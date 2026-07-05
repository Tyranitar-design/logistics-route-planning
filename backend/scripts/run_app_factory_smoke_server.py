#!/usr/bin/env python
"""Run a temporary Flask app-factory server for smoke harness checks.

This helper intentionally bypasses backend/run.py so a smoke check can verify
the current source tree without being affected by an existing 5000 process or
run.py dotenv override behavior. It does not print environment variables or
secrets.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_backend_on_path() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    backend_path = str(backend_dir)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a temporary app-factory smoke server.")
    parser.add_argument("--host", default=os.environ.get("FLASK_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FLASK_PORT", "5066")))
    parser.add_argument("--config", default=os.environ.get("FLASK_CONFIG", "testing"))
    parser.add_argument("--load-local-env", action="store_true", help="Load backend/.env.local without printing any secret values.")
    args = parser.parse_args()

    if args.load_local_env:
        from dotenv import load_dotenv

        backend_dir = Path(__file__).resolve().parents[1]
        load_dotenv(backend_dir / ".env.local", override=True)

    os.environ.setdefault("FLASK_CONFIG", args.config)
    os.environ.setdefault("DISABLE_KAFKA_CONSUMER", "1")
    os.environ.setdefault("DISABLE_ML_ROUTES", "1")

    _ensure_backend_on_path()
    from app import create_app

    app = create_app(args.config)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
