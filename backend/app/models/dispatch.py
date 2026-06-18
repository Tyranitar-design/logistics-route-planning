"""Dispatch scenario and assignment models."""

from datetime import datetime

from app.models import db


class DispatchScenario(db.Model):
    """Persisted dispatch preview/apply scenario."""

    __tablename__ = "dispatch_scenarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scenario_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128))
    status = db.Column(db.String(32), default="preview", nullable=False, index=True)
    solver = db.Column(db.String(64), default="greedy_wave")
    data_source = db.Column(db.String(64))
    distance_source = db.Column(db.String(128))
    provider_status = db.Column(db.String(32))
    authenticity_level = db.Column(db.String(8))
    fallback_reason = db.Column(db.Text)
    wave_filters_json = db.Column(db.Text)
    summary_json = db.Column(db.Text)
    diagnostics_json = db.Column(db.Text)
    ai_shadow_json = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    applied_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DispatchAssignment(db.Model):
    """Orders assigned to vehicles inside a dispatch scenario."""

    __tablename__ = "dispatch_assignments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("dispatch_scenarios.id"), nullable=False, index=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False, index=True)
    vehicle_plate = db.Column(db.String(32))
    order_source = db.Column(db.String(64), nullable=False, index=True)
    order_ref = db.Column(db.String(128), nullable=False, index=True)
    order_number = db.Column(db.String(128))
    sequence_index = db.Column(db.Integer, default=0)
    assignment_status = db.Column(db.String(32), default="preview", nullable=False, index=True)
    weight_kg = db.Column(db.Float)
    volume_m3 = db.Column(db.Float)
    distance_km = db.Column(db.Float)
    duration_min = db.Column(db.Float)
    cost = db.Column(db.Float)
    route_json = db.Column(db.Text)
    diagnostics_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    scenario = db.relationship("DispatchScenario", backref="assignments")
    vehicle = db.relationship("Vehicle")
