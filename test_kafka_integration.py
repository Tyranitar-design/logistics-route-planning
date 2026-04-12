#!/usr/bin/env python3
"""测试后端 Kafka 集成"""
import requests
import json

BASE_URL = 'http://localhost:5000'

# 1. 登录获取 token
login_resp = requests.post(f'{BASE_URL}/api/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})
print(f"登录状态: {login_resp.status_code}")

if login_resp.status_code != 200:
    print(f"登录失败: {login_resp.text}")
    exit(1)

token = login_resp.json().get('access_token')
print(f"Token: {token[:50]}...")

headers = {'Authorization': f'Bearer {token}'}

# 2. 创建订单
order_data = {
    'pickup_node_id': 24,
    'delivery_node_id': 26,
    'cost': 9999.99,
    'customer_name': 'Kafka集成测试',
    'customer_phone': '13800138000'
}

print(f"\n创建订单...")
order_resp = requests.post(f'{BASE_URL}/api/orders', json=order_data, headers=headers)
print(f"订单状态: {order_resp.status_code}")

if order_resp.status_code == 201:
    order = order_resp.json()
    print(f"订单创建成功: {json.dumps(order, ensure_ascii=False, indent=2)}")
else:
    print(f"订单创建失败: {order_resp.text}")

print("\n检查 Kafka 消息...")
