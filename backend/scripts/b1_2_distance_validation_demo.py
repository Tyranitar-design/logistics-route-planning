import sys
import os
import json

# add backend to path
BACKEND = r'D:\物流路径规划系统项目\backend'
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.services.distance_cache_service import get_distance_cache


def run():
    svc = get_distance_cache()

    origin = (116.397, 39.908)      # 北京天安门附近
    destination = (121.473, 31.230) # 上海人民广场附近

    print('=== B1-2 distance validation demo ===')
    print('origin:', origin)
    print('destination:', destination)

    r1 = svc.get_distance(origin, destination, strategy=0, use_amap=False)
    print('[1] fallback result:')
    print(json.dumps(r1, ensure_ascii=False, indent=2))

    r2 = svc.get_distance(origin, destination, strategy=0, use_amap=False)
    print('[2] cached result:')
    print(json.dumps(r2, ensure_ascii=False, indent=2))

    print('[3] cache stats:')
    print(json.dumps(svc.get_stats(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
