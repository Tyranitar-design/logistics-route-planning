#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Backfill missing routes.distance with explicit provenance metadata."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _load_local_database_url() -> None:
    if os.environ.get("POSTGRES_DATABASE_URL") or os.environ.get("DATABASE_URL"):
        return

    startup = pathlib.Path(r"C:\Users\Administrator\Desktop\物流路径规划系统项目启动方式.txt")
    if not startup.exists():
        return

    text = startup.read_text(encoding="utf-8")
    match = re.search(r'POSTGRES_DATABASE_URL="([^"]+)"', text)
    if match:
        os.environ["POSTGRES_DATABASE_URL"] = match.group(1)


def _print_report(result: dict) -> None:
    summary = result["summary"]
    mode = "APPLY" if not summary["dry_run"] else "DRY_RUN"
    print(f"=== Route Distance Backfill {mode} ===")
    print(f"candidate_routes={summary['candidate_routes']}")
    print(f"updated={summary['updated']}")
    print(f"skipped={summary['skipped']}")
    print(f"provider={summary['provider']}")
    print(f"source_summary={summary['source_summary']}")
    print("")
    print("[samples]")
    for item in result.get("samples", []):
        print(
            f"route_id={item['route_id']} success={item['success']} "
            f"distance_km={item.get('distance_km')} source={item.get('distance_source')} "
            f"fallback={item.get('fallback_reason')}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("FLASK_CONFIG", "production"))
    parser.add_argument("--provider", choices=["haversine", "amap"], default="haversine")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true", help="write updates; default is dry-run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    _load_local_database_url()

    from app import create_app
    from app.services.route_distance_backfill_service import backfill_route_distances

    app = create_app(args.config)
    with app.app_context():
        result = backfill_route_distances(apply=args.apply, provider=args.provider, limit=args.limit)

    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        _print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
