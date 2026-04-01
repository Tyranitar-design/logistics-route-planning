import requests
import json

# 测试登录
url = "http://127.0.0.1:5000/api/auth/login"
data = {
    "username": "admin",
    "password": "admin123"  # 尝试常见密码
}

print("测试登录 API...")
print(f"URL: {url}")
print(f"Data: {data}")
print()

try:
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"错误: {e}")
