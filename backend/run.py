"""
Flask 应用入口 - 支持 WebSocket
"""
import os
import sys

# 把项目根目录加入模块搜索路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from app import create_app
from app.services.websocket_service import init_socketio, start_background_push, stop_background_push
from app.routes.websocket import register_socketio_events

# 创建应用实例（gunicorn 需要这个）
config_name = os.getenv("FLASK_CONFIG", "development")
app = create_app(config_name)

# 初始化 SocketIO
socketio = init_socketio(app)

# 注册 SocketIO 事件
register_socketio_events(socketio)

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    print("=" * 50)
    print("   物流路径规划系统 - 后端服务启动")
    print("=" * 50)
    print(f"  HTTP:  http://{host}:{port}")
    print(f"  WebSocket: ws://{host}:{port}")
    print(f"  模式: {config_name}")
    print("=" * 50)
    
    # 启动后台推送线程
    start_background_push()
    
    try:
        # 使用 SocketIO 运行（支持 WebSocket）
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    finally:
        # 停止后台推送
        stop_background_push()