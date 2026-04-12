import json
from kafka import KafkaProducer
import time

# 发送消息
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

print("发送新消息...")
msg = {
    "order_id": "FINAL-SUCCESS-001",
    "event_type": "created",
    "status": "pending",
    "cost": 8888.88
}
future = producer.send("logistics.orders.json", value=msg)
result = future.get(timeout=10)
print(f"Sent: {msg['order_id']} to partition {result.partition}, offset {result.offset}")

producer.flush()
producer.close()
print("Done!")
