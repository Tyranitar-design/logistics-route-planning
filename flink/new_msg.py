import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

msg = {"order_id": "NEW-MSG-001", "event_type": "created", "status": "pending", "cost": 12345.67}
future = producer.send("logistics.orders.json", value=msg)
result = future.get(timeout=10)
print(f"Sent to offset {result.offset}")
producer.flush()
producer.close()
