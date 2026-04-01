#!/bin/bash

# ============================================
# 物流路径规划系统 - 云服务器一键部署脚本
# ============================================

set -e

echo "============================================"
echo "  物流路径规划系统 - 云服务器部署"
echo "============================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/opt/logistics"
DATA_DIR="/opt/logistics/data"

# ============================================
# 1. 安装依赖
# ============================================
echo -e "${YELLOW}[1/6] 安装系统依赖...${NC}"
apt-get update
apt-get install -y git curl wget unzip

# ============================================
# 2. 安装 Docker（如果没装）
# ============================================
echo -e "${YELLOW}[2/6] 检查 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    echo "安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo -e "${GREEN}Docker 版本: $(docker --version)${NC}"

# ============================================
# 3. 创建项目目录
# ============================================
echo -e "${YELLOW}[3/6] 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $DATA_DIR

# ============================================
# 4. 创建 Docker Compose 配置
# ============================================
echo -e "${YELLOW}[4/6] 创建 Docker 配置...${NC}"

# 创建后端 Dockerfile
cat > $PROJECT_DIR/Dockerfile.backend << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（简化版，避免内存问题）
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    flask-sqlalchemy==3.1.1 \
    flask-socketio==5.3.6 \
    gunicorn==21.2.0 \
    eventlet==0.33.3 \
    requests==2.31.0 \
    pandas==2.1.0 \
    numpy==1.24.0 \
    openpyxl==3.1.2 \
    reportlab==4.0.4

# 复制应用代码
COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "run:app"]
EOF

# 创建前端 Dockerfile
cat > $PROJECT_DIR/Dockerfile.frontend << 'EOF'
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm install --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
EOF

# 创建 Nginx 配置
cat > $PROJECT_DIR/nginx.conf << 'EOF'
server {
    listen 80;
    server_name _;

    # 前端
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://backend:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket
    location /socket.io/ {
        proxy_pass http://backend:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

# 创建 docker-compose.yml
cat > $PROJECT_DIR/docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: ../Dockerfile.backend
    container_name: logistics-backend
    restart: always
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=your-secret-key-change-me
    volumes:
      - ../data:/app/data
    expose:
      - "5000"
    networks:
      - logistics-network
    deploy:
      resources:
        limits:
          memory: 512M

  frontend:
    build:
      context: ./frontend
      dockerfile: ../Dockerfile.frontend
    container_name: logistics-frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - logistics-network

networks:
  logistics-network:
    driver: bridge
EOF

echo -e "${GREEN}Docker 配置创建完成${NC}"

# ============================================
# 5. 提示上传代码
# ============================================
echo ""
echo -e "${YELLOW}[5/6] 项目代码准备${NC}"
echo "请将项目代码上传到服务器："
echo ""
echo "  方法1: 使用 SCP (在本地电脑执行)"
echo "  scp -r D:\\物流路径规划系统项目\\backend root@122.152.220.116:/opt/logistics/"
echo "  scp -r D:\\物流路径规划系统项目\\frontend root@122.152.220.116:/opt/logistics/"
echo ""
echo "  方法2: 使用 Git (如果有仓库)"
echo "  cd /opt/logistics && git clone <你的仓库地址> ."
echo ""

# ============================================
# 6. 配置防火墙
# ============================================
echo -e "${YELLOW}[6/6] 配置防火墙...${NC}"
# 开放端口
iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
iptables -I INPUT -p tcp --dport 5000 -j ACCEPT 2>/dev/null || true

echo -e "${GREEN}防火墙配置完成${NC}"

echo ""
echo "============================================"
echo -e "${GREEN}  部署脚本准备完成！${NC}"
echo "============================================"
echo ""
echo "下一步："
echo "1. 在腾讯云控制台开放安全组端口: 80, 443"
echo "2. 上传项目代码到服务器"
echo "3. 运行: cd /opt/logistics && docker-compose up -d --build"
echo ""