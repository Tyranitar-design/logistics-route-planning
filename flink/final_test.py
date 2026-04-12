import json
from kafka import KafkaProducer, KafkaConsumer

# 1. 发送消息
print("Connecting to Kafka...")
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

msg = {
    "order_id": "SUCCESS-TEST-001",
    "event_type": "created", 
    "status": "pending",
    "cost": 8888.88,
    "timestamp": "2026-04-11T14:00:00Z"
}

print(f"Sending: {msg}")
producer.send("logistics.orders.json.v2", value=msg)
producer.flush()
producer.close()
print("Message sent!")

# 2. 检查输出 topic
print("\nChecking output topic...")
consumer = KafkaConsumer(
    "logistics.order.stats",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    consumer_timeout_ms=5000,
    value_deserializer=lambda m: m.decode("utf-8")
)

for msg in consumer:
    print(f"Received: {msg.value}")
