#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read-only verification for the local layered PostgreSQL logistics data."""

from __future__ import annotations

import pathlib
import re

import psycopg2


STARTUP_FILE = pathlib.Path(r"C:\Users\Administrator\Desktop\物流路径规划系统项目启动方式.txt")


def get_database_url() -> str:
    text = STARTUP_FILE.read_text(encoding="utf-8")
    match = re.search(r'POSTGRES_DATABASE_URL="([^"]+)"', text)
    if not match:
        raise RuntimeError("POSTGRES_DATABASE_URL not found in startup file")
    return match.group(1)


def main() -> None:
    conn = psycopg2.connect(get_database_url())
    try:
        cur = conn.cursor()
        for table in [
            "shipment_facts",
            "raw_logistics_shipment_records",
            "data_import_batches",
            "orders",
            "nodes",
            "routes",
            "vehicles",
        ]:
            cur.execute(f"select count(*) from {table}")
            print(table, cur.fetchone()[0])

        cur.execute(
            """
            select
                min(shipped_at),
                max(shipped_at),
                count(distinct origin_city_std),
                count(distinct destination_city_std),
                count(distinct external_shipment_id)
            from shipment_facts
            """
        )
        print("shipment_summary", cur.fetchone())

        cur.execute(
            """
            select standard_status, count(*)
            from shipment_facts
            group by standard_status
            order by count(*) desc
            """
        )
        print("status_counts", cur.fetchall())
    finally:
        conn.close()


if __name__ == "__main__":
    main()
