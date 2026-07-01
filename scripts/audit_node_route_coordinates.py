#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a read-only Node/Route coordinate foundation audit."""

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


def _print_text_report(result: dict) -> None:
    summary = result["summary"]
    nodes = result["nodes"]["summary"]
    routes = result["routes"]["summary"]
    shipments = result["shipment_facts"]["summary"]

    print("=== Node/Route Coordinate Foundation Audit ===")
    print(f"nodes_total={summary['nodes_total']} active={summary['nodes_active']} issues={summary['node_issue_count']}")
    print(f"routes_total={summary['routes_total']} active={summary['routes_active']} issues={summary['route_issue_count']}")
    print(
        "shipment_facts="
        f"{summary['shipment_fact_total']} coordinate_issues={summary['shipment_fact_coordinate_issue_count']}"
    )
    print("")

    print("[node issues]")
    for key, value in nodes.items():
        print(f"{key}={value}")

    print("")
    print("[route issues]")
    for key, value in routes.items():
        print(f"{key}={value}")

    print("")
    print("[shipment coverage]")
    for key, value in shipments.items():
        print(f"{key}={value}")

    print("")
    print("[recommendations]")
    for item in result["recommendations"]:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("FLASK_CONFIG", "production"))
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="print the full JSON payload")
    args = parser.parse_args()

    _load_local_database_url()

    from app import create_app
    from app.services.node_route_audit_service import audit_node_route_coordinates

    app = create_app(args.config)
    with app.app_context():
        result = audit_node_route_coordinates(sample_limit=args.sample_limit)

    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        _print_text_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
