# 🚀 云服务器部署指南

## 📋 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 122.152.220.116 |
| 密码 | luyuLUYU.211 |
| 系统 | Ubuntu 22.04 |

---

## 第一步：连接服务器

### Windows 用户（推荐使用 PowerShell）

```powershell
ssh root@122.152.220.116
```

输入密码：`luyuLUYU.211`

### 如果提示没有 ssh 命令

1. 打开 **Windows Terminal** 或 **PowerShell**
2. 或使用 **PuTTY** / **XShell** 等工具

---

## 第二步：安装基础环境

连接服务器后，依次执行以下命令：

```bash
# 更新系统
apt-get update

# 安装必要软件
apt-get install -y python3 python3-pip python3-venv nginx git curl

# 创建项目目录
mkdir -p /opt/logistics
```

---

## 第三步：上传项目代码

### 在你的本地电脑（Windows）打开新的 PowerShell

```powershell
# 上传后端代码
scp -r "D:\物流路径规划系统项目\backend" root@122.152.220.116:/opt/logistics/

# 上传前端构建产物（需要先在本地构建）
cd "D:\物流路径规划系统项目\frontend"
npm run build
scp -r "D:\物流路径规划系统项目\frontend\dist" root@122.152.220.116:/opt/logistics/frontend/
```

---

## 第四步：配置后端环境

回到服务器 SSH 终端：

```bash
# 进入项目目录
cd /opt/logistics

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖（精简版，避免内存问题）
pip install flask flask-cors flask-sqlalchemy flask-socketio gunicorn eventlet requests pandas numpy openpyxl reportlab

# 初始化数据库
cd backend
python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

---

## 第五步：配置 Nginx

```bash
# 创建 Nginx 配置
cat > /etc/nginx/sites-available/logistics << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        root /opt/logistics/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 启用配置
ln -sf /etc/nginx/sites-available/logistics /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试并重启
nginx -t && systemctl restart nginx
```

---

## 第六步：启动后端服务

```bash
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
ExecStart=/opt/logistics/venv/bin/gunicorn --bind 0.0.0.1:5000 --workers 1 --timeout 120 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl enable logistics
systemctl start logistics

# 查看状态
systemctl status logistics
```

---

## 第七步：开放安全组端口

在 **腾讯云控制台**：

1. 进入 **轻量应用服务器** 管理页面
2. 找到你的服务器，点击进入详情
3. 点击 **防火墙** 标签
4. 添加规则：
   - 协议：TCP
   - 端口：80
   - 策略：允许

---

## ✅ 访问测试

浏览器打开：`http://122.152.220.116`

默认账号：
- 管理员：`admin` / `admin123`
- 普通用户：`user` / `user123`

---

## 🔧 常用命令

```bash
# 查看后端日志
journalctl -u logistics -f

# 重启服务
systemctl restart logistics

# 重启 Nginx
systemctl restart nginx

# 查看服务状态
systemctl status logistics
systemctl status nginx
```

---

## 📝 注意事项

1. **内存优化**：2G 内存运行，workers 设为 1
2. **数据库**：使用 SQLite，无需额外安装
3. **安全**：建议修改默认密码
4. **备份**：定期备份 `/opt/logistics/backend/data/` 目录

---

## 🆘 遇到问题？

1. 页面打不开 → 检查安全组端口 80 是否开放
2. API 报错 → 查看 `journalctl -u logistics -f`
3. 前端空白 → 检查 `dist` 目录是否正确上传

---

**部署完成后告诉我，我来帮你测试！** 😊