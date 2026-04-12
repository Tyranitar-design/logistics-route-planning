import json
from kafka import KafkaProducer

# 发送消息
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

msg = {"order_id": "PYTHON-TEST-001", "event_type": "created", "status": "pending", "cost": 8888.88}
future = producer.send("logistics.orders.json", value=msg)
result = future.get(timeout=10)
print(f"Sent to partition {result.partition}")

producer.flush()
producer.close()
print("Done!")
