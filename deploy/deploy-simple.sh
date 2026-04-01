#!/bin/bash

# ============================================
# 物流路径规划系统 - 轻量化部署脚本
# 适用于 2G 内存服务器
# ============================================

set -e

echo "============================================"
echo "  物流路径规划系统 - 轻量化部署"
echo "============================================"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================
# 1. 安装依赖
# ============================================
echo -e "${YELLOW}[1/5] 安装系统依赖...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx git curl

# ============================================
# 2. 创建项目目录
# ============================================
echo -e "${YELLOW}[2/5] 创建项目目录...${NC}"
mkdir -p /opt/logistics
cd /opt/logistics

# ============================================
# 3. 安装 Python 环境
# ============================================
echo -e "${YELLOW}[3/5] 安装 Python 环境...${NC}"
python3 -m venv venv
source venv/bin/activate

# 安装核心依赖（精简版，避免内存问题）
pip install --no-cache-dir \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    flask-sqlalchemy==3.1.1 \
    flask-socketio==5.3.6 \
    gunicorn==21.2.0 \
    eventlet==0.33.3 \
    requests==2.31.0 \
    pandas==2.1.0 \
    numpy==1.24.0

# ============================================
# 4. 配置 Nginx
# ============================================
echo -e "${YELLOW}[4/5] 配置 Nginx...${NC}"

cat > /etc/nginx/sites-available/logistics << 'EOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /opt/logistics/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    # WebSocket
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

ln -sf /etc/nginx/sites-available/logistics /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# ============================================
# 5. 创建启动脚本
# ============================================
echo -e "${YELLOW}[5/5] 创建启动脚本...${NC}"

cat > /opt/logistics/start.sh << 'EOF'
#!/bin/bash
cd /opt/logistics
source venv/bin/activate
cd backend
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 run:app
EOF

chmod +x /opt/logistics/start.sh

# 创建 systemd 服务
cat > /etc/systemd/system/logistics.service << 'EOF'
[Unit]
Description=Logistics Route Planning System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/logistics/backend
Environment="PATH=/opt/logistics/venv/bin"
ExecStart=/opt/logistics/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable logistics

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  基础环境安装完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "下一步："
echo "1. 上传后端代码: scp -r backend/ root@122.152.220.116:/opt/logistics/"
echo "2. 上传前端代码: scp -r frontend/dist/ root@122.152.220.116:/opt/logistics/frontend/"
echo "3. 启动服务: systemctl start logistics"
echo ""