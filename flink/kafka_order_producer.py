#!/usr/bin/env python3
"""
Kafka 测试数据生产者
发送模拟订单到 Kafka，测试 Flink 流处理
"""
import json
import time
import random
from datetime import datetime

try:
    from kafka import KafkaProducer
except ImportError:
    print("Installing kafka-python...")
    import subprocess
    subprocess.check_call(['py', '-3', '-m', 'pip', 'install', 'kafka-python', '-q'])
    from kafka import KafkaProducer

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'logistics.orders'

# 模拟订单数据
STATUSES = ['pending', 'in_transit', 'completed', 'cancelled']
CUSTOMERS = ['张三', '李四', '王五', '赵六', '陈七', '刘八', '周九', '吴十']
PICKUP_NODES = ['24', '25', '26', '27', '28']
DELIVERY_NODES = ['26', '27', '28', '29', '30', '33']


def create_producer():
    """创建 Kafka 生产者"""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
    )


def generate_order(order_id):
    """生成模拟订单"""
    pickup = random.choice(PICKUP_NODES)
    delivery = random.choice([n for n in DELIVERY_NODES if n != pickup])
    
    return {
        'order_id': f'ORD-{order_id:06d}',
        'order_number': f'LOG-2026-{order_id:05d}',
        'status': random.choice(STATUSES),
        'cost': round(random.uniform(500, 15000), 2),
        'pickup_node_id': pickup,
        'delivery_node_id': delivery,
        'customer_name': random.choice(CUSTOMERS),
        'vehicle_id': f'V{random.randint(1, 20):03d}',
        'created_at': datetime.now().isoformat()
    }


def main():
    print("=" * 50)
    print("  Kafka 订单数据生产者")
    print("=" * 50)
    print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Topic: {KAFKA_TOPIC}")
    print("-" * 50)
    
    try:
        producer = create_producer()
        print("[OK] Kafka 连接成功")
    except Exception as e:
        print(f"[ERROR] Kafka 连接失败: {e}")
        return
    
    print("\n开始发送测试订单 (按 Ctrl+C 停止)...\n")
    
    order_count = 0
    
    try:
        while True:
            order_count += 1
            order = generate_order(order_count)
            
            # 发送到 Kafka
            future = producer.send(KAFKA_TOPIC, value=order)
            result = future.get(timeout=10)
            
            # 打印发送结果
            alert_flag = " [HIGH VALUE!]" if order['cost'] > 10000 else ""
            print(f"[{order_count}] {order['order_id']} | {order['status']:12} | ¥{order['cost']:>8.2f} | {order['pickup_node_id']}->{order['delivery_node_id']}{alert_flag}")
            
            # 随机间隔
            time.sleep(random.uniform(0.5, 2))
            
    except KeyboardInterrupt:
        print(f"\n\n[INFO] 停止发送。共发送 {order_count} 条订单。")
    finally:
        producer.flush()
        producer.close()


if __name__ == '__main__':
    main()
