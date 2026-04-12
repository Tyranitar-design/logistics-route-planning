import requests

print("Testing Spark Cluster...")
try:
    r = requests.get("http://localhost:8080/api/v1/master/workers", timeout=5)
    data = r.json()
    print(f"Spark Workers: {data.get('totalWorkers', 0)}")
    print("Spark: OK")
except Exception as e:
    print(f"Spark Error: {e}")

print("\nTesting Flink Cluster...")
try:
    r = requests.get("http://localhost:8083/overview", timeout=5)
    data = r.json()
    print(f"Flink Version: {data.get('flink-version')}")
    print(f"Running Jobs: {data.get('jobs-running')}")
    print("Flink: OK")
except Exception as e:
    print(f"Flink Error: {e}")

print("\nTesting Kafka...")
try:
    from kafka import KafkaProducer
    import json
    p = KafkaProducer(bootstrap_servers="localhost:9092", value_serializer=lambda v: json.dumps(v).encode())
    p.send("logistics.test", value={"test": "spark"})
    p.flush()
    p.close()
    print("Kafka: OK")
except Exception as e:
    print(f"Kafka Error: {e}")

print("\nTesting Backend API...")
try:
    r = requests.get("http://localhost:5000/api/spark/demand-forecast", timeout=5)
    print(f"Spark API Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  Success: {data.get('success')}")
except Exception as e:
    print(f"Backend Error: {e}")
