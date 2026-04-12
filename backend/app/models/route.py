"""路线模型"""

from datetime import datetime
from app.models import db


class Route(db.Model):
    """路线模型"""
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    start_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    end_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    distance = db.Column(db.Float)
    duration = db.Column(db.Float)
    estimated_time = db.Column(db.Float)
    toll_cost = db.Column(db.Float)
    fuel_cost = db.Column(db.Float)
    route_data = db.Column(db.Text)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    start_node = db.relationship('Node', foreign_keys=[start_node_id])
    end_node = db.relationship('Node', foreign_keys=[end_node_id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_node_id": self.start_node_id,
            "end_node_id": self.end_node_id,
            "start_node": {"id": self.start_node.id, "name": self.start_node.name} if self.start_node else None,
            "end_node": {"id": self.end_node.id, "name": self.end_node.name} if self.end_node else None,
            "origin": self.origin,
            "destination": self.destination,
            "distance": self.distance,
            "duration": self.duration,
            "estimated_time": self.estimated_time,
            "toll_cost": self.toll_cost,
            "fuel_cost": self.fuel_cost,
            "total_cost": (self.toll_cost or 0) + (self.fuel_cost or 0),
            "route_data": self.route_data,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
