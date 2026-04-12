import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# 发送正确的 JSON 格式消息
msg = {
    "order_id": "FINAL-SUCCESS-001",
    "event_type": "created",
    "status": "pending",
    "cost": 9999.99,
    "timestamp": "2026-04-11T14:00:00Z"
}

future = producer.send("logistics.orders.json.v2", value=msg)
result = future.get(timeout=10)
print(f"Sent: {msg['order_id']}")
print(f"Partition: {result.partition}, Offset: {result.offset}")
producer.flush()
producer.close()
print("Done!")
