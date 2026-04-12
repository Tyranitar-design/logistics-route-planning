"""
车辆轨迹实时分析作业
功能：实时监控车辆位置、检测偏航、统计行驶距离
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction, KeyedProcessFunction
from pyflink.common import Types, WatermarkStrategy
from pyflink.datastream.state import ValueStateDescriptor, ListStateDescriptor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackingParser(MapFunction):
    """解析轨迹数据"""

    def map(self, value: str) -> Dict[str, Any]:
        try:
            data = json.loads(value)
            return {
                'vehicle_id': data.get('vehicle_id'),
                'latitude': float(data.get('latitude', 0)),
                'longitude': float(data.get('longitude', 0)),
                'speed': float(data.get('speed', 0)),
                'timestamp': data.get('timestamp'),
                'event_time': int(datetime.now().timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Failed to parse tracking: {e}")
            return None


class SpeedAlertFunction(KeyedProcessFunction):
    """速度异常检测：检测超速"""

    def __init__(self, max_speed: float = 120.0):
        self.max_speed = max_speed
        self.speed_state = None

    def open(self, runtime_context):
        self.speed_state = runtime_context.get_state(
            ValueStateDescriptor("last_speed", Types.FLOAT())
        )

    def process_element(self, value: Dict[str, Any], ctx):
        current_speed = value.get('speed', 0)
        self.speed_state.update(current_speed)

        # 超速检测
        if current_speed > self.max_speed:
            alert = {
                'type': 'OVERSPEED',
                'vehicle_id': value.get('vehicle_id'),
                'speed': current_speed,
                'max_speed': self.max_speed,
                'location': {
                    'lat': value.get('latitude'),
                    'lng': value.get('longitude')
                },
                'timestamp': datetime.now().isoformat()
            }
            yield json.dumps(alert)


def main():
    """车辆轨迹分析主函数"""
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    env.enable_checkpointing(60000)

    logger.info("Starting Vehicle Tracking Stream Processing...")

    # TODO: 添加 Kafka Source
    # TODO: 添加处理逻辑
    # TODO: 添加 Sink

    # 暂时打印测试
    print("Vehicle Tracking Job placeholder - ready for deployment")

    env.execute("Vehicle Tracking Stream Processing")


if __name__ == "__main__":
    main()
