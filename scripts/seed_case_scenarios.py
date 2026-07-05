"""种子场景：创建几个持久化案例场景供 scenarios 对比页展示。

用法: backend/.venv/Scripts/python.exe scripts/seed_case_scenarios.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def load_env() -> None:
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


def _sum(rows, key):
    return round(sum(float(r.get(key) or 0) for r in rows), 2)


def main() -> None:
    load_env()
    from app import create_app
    app = create_app("development")
    with app.test_client() as c:
        c.post("/api/cases/food-supply/import/apply", json={"persist": True})

        fixtures = []

        r1 = c.post("/api/cases/food-supply/optimize/dispatch-fresh",
                    json={"wave_date": "06-01", "store_limit": 8, "solver_mode": "greedy", "persist": False}).get_json()
        plans1 = r1.get("plans", [])
        fixtures.append(("greedy 调度基线", {
            "cost": _sum(plans1, "cost"), "carbon_kg": round(_sum(plans1, "distance_km") * 0.00018 * 40, 2),
            "duration_min": _sum(plans1, "duration_min"), "freshness_score": r1.get("summary", {}).get("avg_freshness_score", 0.82),
            "service_level": 0.90, "feasible": True,
        }))

        r2 = c.post("/api/cases/food-supply/optimize/dispatch-fresh",
                    json={"wave_date": "06-01", "store_limit": 8, "solver_mode": "ortools", "persist": False}).get_json()
        plans2 = r2.get("plans", [])
        fixtures.append(("OR-Tools VRPTW", {
            "cost": _sum(plans2, "cost"), "carbon_kg": round(_sum(plans2, "distance_km") * 0.00018 * 40, 2),
            "duration_min": _sum(plans2, "duration_min"), "freshness_score": r2.get("summary", {}).get("avg_freshness_score", 0.88),
            "service_level": 0.95, "feasible": True,
        }))

        r3 = c.post("/api/cases/food-supply/optimize/multimodal",
                    json={"cluster_limit": 6, "persist": False}).get_json()
        air_cost = round(sum(
            next((float(m.get("cost") or 0) for m in cl.get("modes", []) if m.get("mode") == "air_plus_road" and m.get("feasible")), 0)
            for cl in r3.get("clusters", [])
        ), 2)
        fixtures.append(("空运多式联运", {
            "cost": air_cost, "carbon_kg": round(air_cost * 0.4, 2), "duration_min": 320,
            "freshness_score": 0.95, "service_level": 0.98, "feasible": True,
        }))

        fixtures.append(("纯无人机方案(载重受限)", {
            "cost": 60, "carbon_kg": 0, "duration_min": 90,
            "freshness_score": 0.99, "service_level": 0.55, "feasible": False,
        }))

        for name, summary in fixtures:
            resp = c.post("/api/cases/food-supply/scenarios", json={"name": name, "persist": True, "summary": summary})
            print(f"  seeded: {name} -> {resp.get_json().get('scenario_code')}")

        cmp = c.post("/api/cases/food-supply/scenarios/compare", json={}).get_json()
        print(f"\n=== scenarios compare: {len(cmp.get('comparison', []))} rows ===")
        print(f"recommended: {cmp.get('recommended_scenario')}")
        for row in cmp.get("comparison", []):
            print(f"  {row['name']}: cost={row['cost']} feasible={row['feasible']} freshness={row['freshness_score']}")


if __name__ == "__main__":
    main()
