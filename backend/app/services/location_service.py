# 位置服务

from datetime import datetime
from app import db
from app.models import LocationHistory, Order
from sqlalchemy import and_


class LocationService:
    """位置轨迹相关服务"""
    
    def save_location(self, driver_id, latitude, longitude, accuracy=0, speed=0, direction=0, task_id=None):
        """保存位置记录"""
        location = LocationHistory(
            driver_id=driver_id,
            order_id=task_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            direction=direction,
            recorded_at=datetime.now()
        )
        
        db.session.add(location)
        db.session.commit()
        
        return location.id
    
    def get_location_history(self, driver_id, task_id=None, start_time=None, end_time=None):
        """获取轨迹历史"""
        query = LocationHistory.query.filter(LocationHistory.driver_id == driver_id)
        
        if task_id:
            query = query.filter(LocationHistory.order_id == task_id)
        
        if start_time:
            query = query.filter(LocationHistory.recorded_at >= start_time)
        
        if end_time:
            query = query.filter(LocationHistory.recorded_at <= end_time)
        
        locations = query.order_by(LocationHistory.recorded_at.asc()).all()
        
        return {
            'points': [{
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'accuracy': loc.accuracy,
                'speed': loc.speed,
                'direction': loc.direction,
                'recorded_at': loc.recorded_at.isoformat()
            } for loc in locations],
            'count': len(locations)
        }
    
    def get_current_location(self, driver_id):
        """获取当前位置"""
        location = LocationHistory.query.filter(
            LocationHistory.driver_id == driver_id
        ).order_by(LocationHistory.recorded_at.desc()).first()
        
        if not location:
            return None
        
        return {
            'latitude': location.latitude,
            'longitude': location.longitude,
            'accuracy': location.accuracy,
            'speed': location.speed,
            'direction': location.direction,
            'recorded_at': location.recorded_at.isoformat()
        }
    
    def get_driver_trajectory(self, order_id):
        """获取订单的完整轨迹"""
        locations = LocationHistory.query.filter(
            LocationHistory.order_id == order_id
        ).order_by(LocationHistory.recorded_at.asc()).all()
        
        return [{
            'lat': loc.latitude,
            'lng': loc.longitude,
            'time': loc.recorded_at.isoformat(),
            'speed': loc.speed
        } for loc in locations]
    
    def calculate_total_distance(self, order_id):
        """计算订单实际行驶距离"""
        import math
        
        locations = LocationHistory.query.filter(
            LocationHistory.order_id == order_id
        ).order_by(LocationHistory.recorded_at.asc()).all()
        
        if len(locations) < 2:
            return 0
        
        total_distance = 0
        for i in range(1, len(locations)):
            prev = locations[i-1]
            curr = locations[i]
            
            # Haversine 公式计算两点距离
            distance = self._haversine(
                prev.latitude, prev.longitude,
                curr.latitude, curr.longitude
            )
            total_distance += distance
        
        return round(total_distance, 2)
    
    def _haversine(self, lat1, lon1, lat2, lon2):
        """计算两点间距离（公里）"""
        R = 6371  # 地球半径（公里）
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def check_route_deviation(self, order_id, current_lat, current_lng, threshold_km=0.5):
        """检查是否偏离路线"""
        order = Order.query.get(order_id)
        
        if not order or not order.route_points:
            return False
        
        # 简化：检查当前位置是否接近路线上的任意一点
        for point in order.route_points:
            distance = self._haversine(
                current_lat, current_lng,
                point['lat'], point['lng']
            )
            if distance < threshold_km:
                return False
        
        return True  # 偏离路线