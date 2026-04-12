import json
from kafka import KafkaProducer, KafkaConsumer
import time

# 发送消息
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

print("发送测试消息...")
for i in range(3):
    msg = {
        "order_id": f"SUCCESS-{i+1}",
        "event_type": "created",
        "status": "pending",
        "cost": 1000.0 * (i + 1)
    }
    future = producer.send("logistics.orders.json", value=msg)
    result = future.get(timeout=10)
    print(f"  Sent: {msg['order_id']} to partition {result.partition}")
    time.sleep(0.5)

producer.flush()
producer.close()
print("发送完成！")
