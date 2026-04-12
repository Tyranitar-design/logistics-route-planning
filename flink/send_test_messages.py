#!/usr/bin/env python3
"""发送正确格式的 JSON 消息到 Kafka"""
import json
import time

try:
    from kafka import KafkaProducer
    
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
    )
    
    # 发送测试消息
    messages = [
        {"order_id": "FINAL-TEST-001", "event_type": "created", "status": "pending", "cost": 1234.56},
        {"order_id": "FINAL-TEST-002", "event_type": "created", "status": "pending", "cost": 5678.90},
        {"order_id": "FINAL-TEST-003", "event_type": "created", "status": "completed", "cost": 9999.99},
    ]
    
    for msg in messages:
        future = producer.send('logistics.orders.json', value=msg)
        result = future.get(timeout=10)
        print(f"Sent: {msg['order_id']} to partition {result.partition}")
        time.sleep(0.5)
    
    producer.flush()
    producer.close()
    print("\nAll messages sent successfully!")
    
except Exception as e:
    print(f"Error: {e}")
