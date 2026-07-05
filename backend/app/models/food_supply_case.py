"""Food supply-chain case study models.

These tables keep the peach fresh-food case isolated from production
shipment/order facts. Coordinates are stored as WGS84 lon/lat plus WKT so the
records can be promoted to PostGIS geometry columns without changing the API.
"""

from __future__ import annotations

from datetime import datetime

from app.models import db


class CaseFoodNode(db.Model):
    __tablename__ = "case_food_nodes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    node_code = db.Column(db.String(96), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    node_type = db.Column(db.String(40), nullable=False, index=True)
    role = db.Column(db.String(80))
    city = db.Column(db.String(80))
    address = db.Column(db.String(255))
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    srid = db.Column(db.Integer, default=4326)
    geometry_wkt = db.Column(db.String(128))
    source_file = db.Column(db.String(255))
    data_quality = db.Column(db.String(32), default="ok")
    payload_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("case_id", "node_code", name="uq_case_food_node_code"),
    )


class CaseFoodDemand(db.Model):
    __tablename__ = "case_food_demands"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    demand_type = db.Column(db.String(32), nullable=False, index=True)
    demand_date = db.Column(db.String(16), index=True)
    customer_name = db.Column(db.String(160), index=True)
    region = db.Column(db.String(120), index=True)
    weight_kg = db.Column(db.Float, default=0)
    volume_m3 = db.Column(db.Float, default=0)
    boxes = db.Column(db.Float, default=0)
    address = db.Column(db.String(255))
    source_file = db.Column(db.String(255))
    payload_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CaseFoodResource(db.Model):
    __tablename__ = "case_food_resources"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    resource_type = db.Column(db.String(40), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    capacity_weight_kg = db.Column(db.Float, default=0)
    capacity_volume_m3 = db.Column(db.Float, default=0)
    speed_kmph = db.Column(db.Float, default=0)
    cost_per_km = db.Column(db.Float, default=0)
    cost_per_kg = db.Column(db.Float, default=0)
    cost_per_trip = db.Column(db.Float, default=0)
    range_km = db.Column(db.Float, default=0)
    source_file = db.Column(db.String(255))
    payload_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CaseFoodDistanceMatrix(db.Model):
    __tablename__ = "case_food_distance_matrix"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    source_code = db.Column(db.String(96), nullable=False, index=True)
    target_code = db.Column(db.String(96), nullable=False, index=True)
    distance_km = db.Column(db.Float, default=0)
    duration_min = db.Column(db.Float, default=0)
    distance_source = db.Column(db.String(96), default="haversine_fallback")
    path_source = db.Column(db.String(96), default="local_case_baseline")
    authenticity_level = db.Column(db.String(8), default="C")
    fallback_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("case_id", "source_code", "target_code", "distance_source", name="uq_case_food_distance"),
    )


class CaseFoodScenario(db.Model):
    __tablename__ = "case_food_scenarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    scenario_code = db.Column(db.String(96), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False)
    scenario_type = db.Column(db.String(40), default="food_supply_chain")
    solver = db.Column(db.String(80))
    provider_status = db.Column(db.String(32), default="preview")
    authenticity_level = db.Column(db.String(8), default="C")
    summary_json = db.Column(db.Text)
    payload_json = db.Column(db.Text)
    diagnostics_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CaseFoodRouteComparison(db.Model):
    __tablename__ = "case_food_route_comparisons"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    source_code = db.Column(db.String(96), nullable=False, index=True)
    target_code = db.Column(db.String(96), nullable=False, index=True)
    providers_json = db.Column(db.Text)
    request_hash = db.Column(db.String(64), nullable=False, index=True)
    provider_status = db.Column(db.String(32), default="ok")
    fallback_reason = db.Column(db.String(255))
    distance_source = db.Column(db.String(96), default="mixed_route_compare")
    path_source = db.Column(db.String(96), default="route_provider_compare")
    authenticity_level = db.Column(db.String(16), default="mixed")
    recommended_provider = db.Column(db.String(40))
    recommended_score = db.Column(db.Float)
    best_quality_score = db.Column(db.Float)
    route_count = db.Column(db.Integer, default=0)
    geometry_count = db.Column(db.Integer, default=0)
    summary_json = db.Column(db.Text)
    response_json = db.Column(db.Text)
    diagnostics_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class CaseFoodGeocodingCache(db.Model):
    """C 端地址地理编码缓存。

    按 address_hash 缓存 provider 地理编码结果，避免重复调用高德/天地图。
    仅属于食品案例模块，不写入 shipment_facts/orders/vehicles 等生产事实表。
    """

    __tablename__ = "case_food_geocoding_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(64), nullable=False, index=True)
    address_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    address_raw = db.Column(db.String(512))
    region = db.Column(db.String(120), index=True)
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    provider = db.Column(db.String(40), default="unknown")
    distance_source = db.Column(db.String(96), default="unknown")
    path_source = db.Column(db.String(96), default="unknown")
    authenticity_level = db.Column(db.String(8), default="C")
    fallback_reason = db.Column(db.String(255))
    formatted_address = db.Column(db.String(255))
    payload_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
