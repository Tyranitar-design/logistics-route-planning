"""分层真实数据模型"""

from datetime import datetime

from app.models import db


class DataImportBatch(db.Model):
    __tablename__ = "data_import_batches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dataset_source = db.Column(db.String(64), nullable=False, index=True)
    source_filename = db.Column(db.String(255))
    quality_status = db.Column(db.String(32), default="pending", nullable=False)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    raw_record_count = db.Column(db.Integer, default=0, nullable=False)
    fact_record_count = db.Column(db.Integer, default=0, nullable=False)
    quarantine_record_count = db.Column(db.Integer, default=0, nullable=False)
    summary_json = db.Column(db.Text)


class RawLogisticsShipmentRecord(db.Model):
    __tablename__ = "raw_logistics_shipment_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("data_import_batches.id"), nullable=False, index=True)
    record_index = db.Column(db.Integer, nullable=False)
    raw_payload = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ShipmentFact(db.Model):
    __tablename__ = "shipment_facts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("data_import_batches.id"), nullable=False, index=True)
    external_shipment_id = db.Column(db.String(128), nullable=False, unique=True, index=True)
    external_order_id = db.Column(db.String(128), index=True)
    customer_name_masked = db.Column(db.String(100))
    customer_phone_masked = db.Column(db.String(32))
    origin_city_raw = db.Column(db.String(100))
    origin_city_std = db.Column(db.String(100), index=True)
    destination_city_raw = db.Column(db.String(100))
    destination_city_std = db.Column(db.String(100), index=True)
    origin_lat = db.Column(db.Float)
    origin_lng = db.Column(db.Float)
    destination_lat = db.Column(db.Float)
    destination_lng = db.Column(db.Float)
    geo_status = db.Column(db.String(32), default="unresolved", nullable=False, index=True)
    cargo_type = db.Column(db.String(64))
    logistics_company = db.Column(db.String(100), index=True)
    transport_mode = db.Column(db.String(32), index=True)
    freight = db.Column(db.Float, default=0)
    insurance_amount = db.Column(db.Float, default=0)
    raw_status = db.Column(db.String(64))
    standard_status = db.Column(db.String(32), nullable=False, index=True)
    shipped_at = db.Column(db.DateTime)
    eta_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    signed_at = db.Column(db.DateTime)
    exception_reason = db.Column(db.Text)
    courier_name_masked = db.Column(db.String(100))
    courier_phone_masked = db.Column(db.String(32))
    weight_kg = db.Column(db.Float)
    volume_m3 = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
