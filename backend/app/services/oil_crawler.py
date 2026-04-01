"""
油价数据爬虫服务
Oil Price Crawler Service
支持多数据源：TianAPI(主力) + 备用数据 + 手动录入
"""
import requests
import json
import time
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from app.database import get_db_path

# ==================== 数据源配置 ====================
TIANAPI_KEY = "e2c7bbdbce2502c8460aa05ad0d57fe1"
TIANAPI_BASE = "https://apis.tianapi.com/oilprice/index"

# 2025年发改委标准参考油价（元/升）- 备用/初始化数据
# 数据来源：基于2025年3月发改委调整的参考值
REFERENCE_OIL_PRICES_2025 = {
    "北京市": {
        "province_code": "BJ", "region": "华北",
        "gasoline_92": 7.85, "gasoline_95": 8.36, "gasoline_98": 9.86,
        "diesel_0": 7.56, "diesel_-10": 8.01, "diesel_-20": 8.39
    },
    "天津市": {
        "province_code": "TJ", "region": "华北",
        "gasoline_92": 7.78, "gasoline_95": 8.23, "gasoline_98": 9.73,
        "diesel_0": 7.50, "diesel_-10": 7.95, "diesel_-20": 8.33
    },
    "河北省": {
        "province_code": "HE", "region": "华北",
        "gasoline_92": 7.79, "gasoline_95": 8.24, "gasoline_98": 9.74,
        "diesel_0": 7.51, "diesel_-10": 7.96, "diesel_-20": 8.34
    },
    "山西省": {
        "province_code": "SX", "region": "华北",
        "gasoline_92": 7.75, "gasoline_95": 8.36, "gasoline_98": 9.97,
        "diesel_0": 7.59, "diesel_-10": 8.04, "diesel_-20": 8.43
    },
    "内蒙古自治区": {
        "province_code": "NM", "region": "华北",
        "gasoline_92": 7.76, "gasoline_95": 8.28, "gasoline_98": 9.72,
        "diesel_0": 7.39, "diesel_-10": 7.83, "diesel_-20": 8.21
    },
    "辽宁省": {
        "province_code": "LN", "region": "东北",
        "gasoline_92": 7.79, "gasoline_95": 8.30, "gasoline_98": 9.04,
        "diesel_0": 7.42, "diesel_-10": 7.87, "diesel_-20": 8.25
    },
    "吉林省": {
        "province_code": "JL", "region": "东北",
        "gasoline_92": 7.80, "gasoline_95": 8.41, "gasoline_98": 9.18,
        "diesel_0": 7.44, "diesel_-10": 7.90, "diesel_-20": 8.29
    },
    "黑龙江省": {
        "province_code": "HL", "region": "东北",
        "gasoline_92": 7.87, "gasoline_95": 8.43, "gasoline_98": 9.57,
        "diesel_0": 7.34, "diesel_-10": 7.77, "diesel_-20": 8.16
    },
    "上海市": {
        "province_code": "SH", "region": "华东",
        "gasoline_92": 7.85, "gasoline_95": 8.36, "gasoline_98": 9.86,
        "diesel_0": 7.56, "diesel_-10": 8.01, "diesel_-20": 8.39
    },
    "江苏省": {
        "province_code": "JS", "region": "华东",
        "gasoline_92": 7.83, "gasoline_95": 8.33, "gasoline_98": 9.73,
        "diesel_0": 7.54, "diesel_-10": 7.99, "diesel_-20": 8.37
    },
    "浙江省": {
        "province_code": "ZJ", "region": "华东",
        "gasoline_92": 7.86, "gasoline_95": 8.36, "gasoline_98": 9.16,
        "diesel_0": 7.57, "diesel_-10": 8.02, "diesel_-20": 8.41
    },
    "安徽省": {
        "province_code": "AH", "region": "华东",
        "gasoline_92": 7.84, "gasoline_95": 8.35, "gasoline_98": 9.79,
        "diesel_0": 7.58, "diesel_-10": 8.03, "diesel_-20": 8.42
    },
    "福建省": {
        "province_code": "FJ", "region": "华东",
        "gasoline_92": 7.86, "gasoline_95": 8.39, "gasoline_98": 9.89,
        "diesel_0": 7.58, "diesel_-10": 8.03, "diesel_-20": 8.42
    },
    "江西省": {
        "province_code": "JX", "region": "华东",
        "gasoline_92": 7.84, "gasoline_95": 8.42, "gasoline_98": 9.92,
        "diesel_0": 7.59, "diesel_-10": 8.04, "diesel_-20": 8.43
    },
    "山东省": {
        "province_code": "SD", "region": "华东",
        "gasoline_92": 7.87, "gasoline_95": 8.44, "gasoline_98": 9.76,
        "diesel_0": 7.58, "diesel_-10": 8.03, "diesel_-20": 8.42
    },
    "河南省": {
        "province_code": "HA", "region": "华中",
        "gasoline_92": 7.84, "gasoline_95": 8.37, "gasoline_98": 9.58,
        "diesel_0": 7.57, "diesel_-10": 8.02, "diesel_-20": 8.41
    },
    "湖北省": {
        "province_code": "HB", "region": "华中",
        "gasoline_92": 7.89, "gasoline_95": 8.45, "gasoline_98": 9.96,
        "diesel_0": 7.60, "diesel_-10": 8.05, "diesel_-20": 8.44
    },
    "湖南省": {
        "province_code": "HN", "region": "华中",
        "gasoline_92": 7.92, "gasoline_95": 8.42, "gasoline_98": 9.82,
        "diesel_0": 7.63, "diesel_-10": 8.08, "diesel_-20": 8.48
    },
    "广东省": {
        "province_code": "GD", "region": "华南",
        "gasoline_92": 7.90, "gasoline_95": 8.56, "gasoline_98": 9.98,
        "diesel_0": 7.60, "diesel_-10": 8.05, "diesel_-20": 8.44
    },
    "广西壮族自治区": {
        "province_code": "GX", "region": "华南",
        "gasoline_92": 7.97, "gasoline_95": 8.61, "gasoline_98": 9.83,
        "diesel_0": 7.65, "diesel_-10": 8.10, "diesel_-20": 8.49
    },
    "海南省": {
        "province_code": "HI", "region": "华南",
        "gasoline_92": 8.99, "gasoline_95": 9.55, "gasoline_98": 10.81,
        "diesel_0": 7.63, "diesel_-10": 8.09, "diesel_-20": 8.48
    },
    "重庆市": {
        "province_code": "CQ", "region": "西南",
        "gasoline_92": 7.99, "gasoline_95": 8.45, "gasoline_98": 9.52,
        "diesel_0": 7.65, "diesel_-10": 8.10, "diesel_-20": 8.49
    },
    "四川省": {
        "province_code": "SC", "region": "西南",
        "gasoline_92": 7.97, "gasoline_95": 8.52, "gasoline_98": 9.25,
        "diesel_0": 7.68, "diesel_-10": 8.14, "diesel_-20": 8.54
    },
    "贵州省": {
        "province_code": "GZ", "region": "西南",
        "gasoline_92": 8.01, "gasoline_95": 8.46, "gasoline_98": 9.37,
        "diesel_0": 7.69, "diesel_-10": 8.15, "diesel_-20": 8.55
    },
    "云南省": {
        "province_code": "YN", "region": "西南",
        "gasoline_92": 8.01, "gasoline_95": 8.60, "gasoline_98": 9.28,
        "diesel_0": 7.69, "diesel_-10": 8.15, "diesel_-20": 8.55
    },
    "西藏自治区": {
        "province_code": "XZ", "region": "西南",
        "gasoline_92": 8.71, "gasoline_95": 9.22, "gasoline_98": 10.29,
        "diesel_0": 8.25, "diesel_-10": 8.74, "diesel_-20": 9.17
    },
    "陕西省": {
        "province_code": "SN", "region": "西北",
        "gasoline_92": 7.78, "gasoline_95": 8.23, "gasoline_98": 9.73,
        "diesel_0": 7.41, "diesel_-10": 7.85, "diesel_-20": 8.23
    },
    "甘肃省": {
        "province_code": "GS", "region": "西北",
        "gasoline_92": 7.80, "gasoline_95": 8.33, "gasoline_98": 9.91,
        "diesel_0": 7.43, "diesel_-10": 7.88, "diesel_-20": 8.26
    },
    "青海省": {
        "province_code": "QH", "region": "西北",
        "gasoline_92": 7.84, "gasoline_95": 8.41, "gasoline_98": 9.58,
        "diesel_0": 7.47, "diesel_-10": 7.92, "diesel_-20": 8.30
    },
    "宁夏回族自治区": {
        "province_code": "NX", "region": "西北",
        "gasoline_92": 7.79, "gasoline_95": 8.24, "gasoline_98": 9.74,
        "diesel_0": 7.41, "diesel_-10": 7.85, "diesel_-20": 8.23
    },
    "新疆维吾尔自治区": {
        "province_code": "XJ", "region": "西北",
        "gasoline_92": 7.73, "gasoline_95": 8.31, "gasoline_98": 9.87,
        "diesel_0": 7.33, "diesel_-10": 7.77, "diesel_-20": 8.15
    },
}

FUEL_TYPES = {
    "gasoline_92": ("92号汽油", "gasoline"),
    "gasoline_95": ("95号汽油", "gasoline"),
    "gasoline_98": ("98号汽油", "gasoline"),
    "diesel_0": ("0号柴油", "diesel"),
    "diesel_-10": ("-10号柴油", "diesel"),
    "diesel_-20": ("-20号柴油", "diesel"),
}


# ==================== 数据源1: TianAPI ====================
def fetch_from_tianapi() -> Optional[List[Dict]]:
    """从天行数据API获取油价数据"""
    try:
        params = {"key": TIANAPI_KEY}
        resp = requests.get(TIANAPI_BASE, params=params, timeout=10)
        data = resp.json()
        
        if data.get("code") == 200:
            records = data.get("result", {}).get("list", [])
            return records
        else:
            print(f"[TianAPI] API error: {data.get('msg')}")
            return None
    except Exception as e:
        print(f"[TianAPI] Request failed: {e}")
        return None


def parse_tianapi_data(records: List[Dict]) -> List[Dict]:
    """解析天行API数据为统一格式"""
    parsed = []
    
    # 省份名归一化（TianAPI raw → 标准省名）
    province_map = {
        "北京": "北京市", "上海": "上海市", "天津": "天津市", "重庆": "重庆市",
        "广州": "广东省", "深圳": "广东省", "成都": "四川省", "杭州": "浙江省",
        "武汉": "湖北省", "西安": "陕西省", "南京": "江苏省", "沈阳": "辽宁省",
        "青岛": "山东省", "济南": "山东省", "郑州": "河南省", "长沙": "湖南省",
        "昆明": "云南省", "贵阳": "贵州省", "南宁": "广西壮族自治区", "拉萨": "西藏自治区",
        "西宁": "青海省", "乌鲁木齐": "新疆维吾尔自治区", "兰州": "甘肃省",
        "银川": "宁夏回族自治区", "呼和浩特": "内蒙古自治区", "哈尔滨": "黑龙江省",
        "长春": "吉林省", "大连": "辽宁省", "石家庄": "河北省", "太原": "山西省",
        "南昌": "江西省", "福州": "福建省", "合肥": "安徽省", "海口": "海南省",
        "苏州": "江苏省", "宁波": "浙江省", "厦门": "福建省", "东莞": "广东省",
        "佛山": "佛山市", "无锡": "无锡市", "温州": "温州市", "内蒙古": "内蒙古自治区",
    }
    
    # 油品类型归一化
    fuel_map = {
        "92#": "92号汽油", "90#": "90号汽油", "93#": "92号汽油",
        "95#": "95号汽油", "97#": "95号汽油", "98#": "98号汽油",
        "0#柴": "0号柴油", "10#柴": "10号柴油", "-10#柴": "-10号柴油",
        "-20#柴": "-20号柴油", "-35#柴": "-35号柴油",
        "汽油": "92号汽油", "柴油": "0号柴油",
        "92号": "92号汽油", "95号": "95号汽油", "98号": "98号汽油",
    }
    
    for rec in records:
        raw_province = rec.get("province", rec.get("city", "")).strip()
        raw_fuel = rec.get("type", rec.get("fuel", "")).strip()
        
        # 省份名归一化
        province = province_map.get(raw_province, raw_province)
        if province and not any(province.endswith(s) for s in ["省", "市", "自治区"]):
            province = province + "市"
        
        # 油品归一化
        fuel_type = fuel_map.get(raw_fuel, raw_fuel)
        if not fuel_type or fuel_type not in ["92号汽油","95号汽油","98号汽油","0号柴油","-10号柴油","-20号柴油","-35号柴油"]:
            fuel_type = "92号汽油"  # 默认
        
        price_val = rec.get("price")
        if price_val is None:
            continue
        try:
            price = float(price_val)
        except (ValueError, TypeError):
            continue
        
        parsed.append({
            "province": province,
            "fuel_type": fuel_type,
            "price": price,
            "update_time": rec.get("updatetime", rec.get("date", "")),
            "unit": rec.get("unit", "元/升"),
            "source": "tianapi",
        })
    return parsed


# ==================== 数据源2: 参考数据（备用） ====================
def fetch_reference_prices() -> List[Dict]:
    """获取2025发改委参考油价数据"""
    records = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for province, info in REFERENCE_OIL_PRICES_2025.items():
        for fuel_key, (fuel_name, fuel_category) in FUEL_TYPES.items():
            price = info.get(fuel_key)
            if price:
                records.append({
                    "province": province,
                    "fuel_type": fuel_name,
                    "fuel_category": fuel_category,
                    "price": price,
                    "update_time": today,
                    "unit": "元/升",
                    "source": "ndrc_reference",
                })
    return records


# ==================== 数据库操作 ====================
def save_oil_price(records: List[Dict], source: str):
    """保存油价数据到数据库"""
    conn = sqlite3.connect(get_db_path("Price.db"))
    cur = conn.cursor()
    saved = 0
    
    for rec in records:
        # 检查是否已存在（同一省份+油品+日期+来源）
        cur.execute("""
            SELECT id, price FROM oil_prices 
            WHERE province=? AND fuel_type=? AND source=? 
            AND DATE(update_time) = DATE(?)
        """, (rec["province"], rec["fuel_type"], source, rec["update_time"][:10]))
        
        existing = cur.fetchone()
        
        if existing:
            # 更新更便宜（更准确）的数据
            if rec["price"] < existing[1]:
                cur.execute("""
                    UPDATE oil_prices SET price=?, update_time=? 
                    WHERE id=?
                """, (rec["price"], rec["update_time"], existing[0]))
                saved += 1
        else:
            cur.execute("""
                INSERT INTO oil_prices (province, fuel_type, fuel_category, price, unit, source, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rec["province"], rec["fuel_type"], rec.get("fuel_category", "gasoline"),
                rec["price"], rec.get("unit", "元/升"), source, rec["update_time"]
            ))
            saved += 1
    
    conn.commit()
    conn.close()
    return saved


def save_crawl_record(source: str, status: str, count: int, error: str = ""):
    """保存爬虫运行记录"""
    conn = sqlite3.connect(get_db_path("Price.db"))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO crawl_records (source, status, records_count, error_message)
        VALUES (?, ?, ?, ?)
    """, (source, status, count, error))
    conn.commit()
    conn.close()


def update_province_prices(records: List[Dict], source: str):
    """更新省份表中的最新油价"""
    conn = sqlite3.connect(get_db_path("Price.db"))
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 按省份分组，取最新价格
    province_latest = {}
    for rec in records:
        prov = rec["province"]
        fuel_type = rec["fuel_type"]
        if prov not in province_latest:
            province_latest[prov] = {}
        province_latest[prov][fuel_type] = rec["price"]
    
    for prov, prices in province_latest.items():
        cur.execute("SELECT id FROM provinces WHERE name=?", (prov,))
        row = cur.fetchone()
        if row:
            update_fields = ["last_updated=?", "data_source=?"]
            update_vals = [now, source]
            
            for fuel_type, price in prices.items():
                if "92" in fuel_type:
                    update_fields.append("current_gasoline_92=?")
                    update_vals.append(price)
                elif "95" in fuel_type:
                    update_fields.append("current_gasoline_95=?")
                    update_vals.append(price)
                elif "98" in fuel_type:
                    update_fields.append("current_gasoline_98=?")
                    update_vals.append(price)
                elif "0号柴" in fuel_type or fuel_type == "diesel_0":
                    update_fields.append("current_diesel_0=?")
                    update_vals.append(price)
            
            update_vals.append(prov)
            cur.execute(f"UPDATE provinces SET {','.join(update_fields)} WHERE name=?", update_vals)
    
    conn.commit()
    conn.close()


# ==================== 主爬虫函数 ====================
def run_oil_crawler() -> Dict[str, Any]:
    """
    运行完整爬虫流程
    返回: {"success": bool, "total_saved": int, "sources": {...}, "message": str}
    """
    print("[OilCrawler] Starting oil price crawler...")
    results = {
        "success": False,
        "total_saved": 0,
        "sources": {},
        "message": "",
        "timestamp": datetime.now().isoformat(),
    }
    
    all_records = []
    
    # ---- 数据源1: TianAPI (主力) ----
    print("[OilCrawler] Trying TianAPI...")
    tianapi_records = fetch_from_tianapi()
    if tianapi_records:
        parsed = parse_tianapi_data(tianapi_records)
        all_records.extend(parsed)
        save_crawl_record("tianapi", "success", len(parsed))
        results["sources"]["tianapi"] = {
            "status": "success", "count": len(parsed), "preview": parsed[:2]
        }
        print(f"[OilCrawler] TianAPI: got {len(parsed)} records")
    else:
        save_crawl_record("tianapi", "failed", 0, "No data or API error")
        results["sources"]["tianapi"] = {"status": "failed", "count": 0}
        print("[OilCrawler] TianAPI: failed")
    
    # ---- 数据源2: 参考数据 (每次都运行，保证有数据) ----
    print("[OilCrawler] Loading reference data (NDRC 2025)...")
    ref_records = fetch_reference_prices()
    all_records.extend(ref_records)
    save_crawl_record("ndrc_reference", "success", len(ref_records))
    results["sources"]["ndrc_reference"] = {
        "status": "success", "count": len(ref_records),
        "note": "2025发改委参考价格，实时数据请配置TianAPI或其他数据源"
    }
    print(f"[OilCrawler] Reference: {len(ref_records)} records")
    
    # ---- 统一保存 ----
    if all_records:
        # 优先保存 TianAPI 数据（更实时）
        tianapi_only = [r for r in all_records if r.get("source") == "tianapi"]
        if tianapi_only:
            saved_tian = save_oil_price(tianapi_only, "tianapi")
            update_province_prices(tianapi_only, "tianapi")
            results["total_saved"] += saved_tian
        
        # 参考数据做补充
        ref_only = [r for r in all_records if r.get("source") == "ndrc_reference"]
        saved_ref = save_oil_price(ref_only, "ndrc_reference")
        update_province_prices(ref_only, "ndrc_reference")
        results["total_saved"] += saved_ref
        
        results["success"] = True
        results["message"] = f"成功获取 {len(all_records)} 条油价数据"
        print(f"[OilCrawler] Total saved: {results['total_saved']} records")
    else:
        results["message"] = "所有数据源均失败"
        print("[OilCrawler] All sources failed!")
    
    return results


def get_crawl_status() -> Dict[str, Any]:
    """获取爬虫最近运行状态"""
    conn = sqlite3.connect(get_db_path("Price.db"))
    cur = conn.cursor()
    cur.execute("""
        SELECT source, status, records_count, error_message, crawled_at 
        FROM crawl_records ORDER BY crawled_at DESC LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()
    
    return {
        "recent_runs": [
            {"source": r[0], "status": r[1], "count": r[2], "error": r[3], "time": r[4]}
            for r in rows
        ]
    }


if __name__ == "__main__":
    result = run_oil_crawler()
    print(json.dumps(result, ensure_ascii=False, indent=2))
