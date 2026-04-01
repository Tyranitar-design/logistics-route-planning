# Backend Dockerfile - 物流路径规划系统后端
# 支持 Flask + WebSocket + ML 预测

FROM python:3.11-slim

LABEL maintainer="小彩 <xiaocai@openclaw.ai>"
LABEL version="2.0"
LABEL description="物流路径规划系统后端 - 43项功能完整版"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建必要目录
RUN mkdir -p /app/data /app/logs /app/database

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用清华镜像加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 环境变量
ENV FLASK_CONFIG=docker
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 启动命令 - 使用 gunicorn + eventlet 支持 WebSocket
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "--worker-class", "eventlet", "--keep-alive", "5", "run:app"]
