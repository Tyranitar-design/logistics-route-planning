#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量审计（只读）—— 审计 shipment_facts 的坐标/城市/状态/来源分布。

用法：
    # 方式1：环境变量（推荐，通用）
    set POSTGRES_DATABASE_URL=postgresql://user:pwd@localhost:5432/logistics_route_system
    python scripts/audit_data_quality.py

    # 方式2：本机桌面启动文件自动 fallback（无需设环境变量）

全部为 SELECT，不修改任何数据。
"""

import os
import pathlib
import re
import sys

import psycopg2


def get_database_url() -> str:
    """优先环境变量，fallback 本机桌面启动文件。"""
    url = os.environ.get("POSTGRES_DATABASE_URL")
    if url:
        return url
    startup = pathlib.Path(r"C:\Users\Administrator\Desktop\物流路径规划系统项目启动方式.txt")
    if startup.exists():
        text = startup.read_text(encoding="utf-8")
        match = re.search(r'POSTGRES_DATABASE_URL="([^"]+)"', text)
        if match:
            return match.group(1)
    print("ERROR: 请设置 POSTGRES_DATABASE_URL 环境变量", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    conn = psycopg2.connect(get_database_url())
    try:
        cur = conn.cursor()

        print("=== 1. 总量 ===")
        cur.execute("select count(*) from shipment_facts")
        print("shipment_facts:", cur.fetchone()[0])

        print("\n=== 2. geo_status 分布（坐标解析状态）===")
        cur.execute("select geo_status, count(*) from shipment_facts group by geo_status order by count(*) desc")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

        print("\n=== 3. 坐标缺失明细 ===")
        cur.execute("""
            select
              count(*) total,
              count(*) filter (where origin_lat is null or origin_lng is null) origin_missing,
              count(*) filter (where destination_lat is null or destination_lng is null) dest_missing,
              count(*) filter (where origin_lat is null or origin_lng is null
                               or destination_lat is null or destination_lng is null) any_missing
            from shipment_facts
        """)
        row = cur.fetchone()
        print(f"  total={row[0]} origin_missing={row[1]} dest_missing={row[2]} any_missing={row[3]}")

        print("\n=== 4. 数据来源批次（DataImportBatch）===")
        cur.execute("""
            select id, dataset_source, source_filename, quality_status,
                   raw_record_count, fact_record_count, imported_at
            from data_import_batches order by id
        """)
        for row in cur.fetchall():
            print(f"  {row}")

        print("\n=== 5. 缺坐标的城市（origin_city_std Top20）===")
        cur.execute("""
            select origin_city_std, count(*)
            from shipment_facts
            where origin_lat is null or origin_lng is null
            group by origin_city_std
            order by count(*) desc
            limit 20
        """)
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

        print("\n=== 6. 城市覆盖 ===")
        cur.execute("select count(distinct origin_city_std), count(distinct destination_city_std) from shipment_facts")
        print("  distinct origin/dest cities:", cur.fetchone())

        print("\n=== 7. 标准状态分布 ===")
        cur.execute("select standard_status, count(*) from shipment_facts group by standard_status order by count(*) desc")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

        print("\n=== 8. 时间范围 / 运输方式 / 物流公司 ===")
        cur.execute("select min(shipped_at), max(shipped_at) from shipment_facts")
        print("  shipped_at range:", cur.fetchone())
        cur.execute("select transport_mode, count(*) from shipment_facts group by transport_mode order by count(*) desc")
        print("  transport_mode:", cur.fetchall())
        cur.execute("select logistics_company, count(*) from shipment_facts group by logistics_company order by count(*) desc limit 10")
        print("  logistics_company top10:", cur.fetchall())

    finally:
        conn.close()


if __name__ == "__main__":
    main()
