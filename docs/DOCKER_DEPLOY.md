# 🐳 Docker 部署指南

> 物流路径规划系统 v2.0 | 43 项功能完整版

---

## 📋 前置条件

### 必需软件
- **Docker Desktop** 20.10+ 
- **Docker Compose** 2.0+
- 至少 **4GB** 可用内存
- 至少 **10GB** 磁盘空间

### 验证安装
```bash
docker --version
docker-compose --version
```

---

## 🚀 快速部署（推荐）

### 方式一：一键部署脚本

**Windows PowerShell**:
```powershell
cd D:\物流路径规划系统项目
.\start-docker.ps1
```

脚本会自动完成：
1. ✅ 检查 Docker 状态
2. ✅ 停止旧容器
3. ✅ 清理构建缓存
4. ✅ 创建数据目录
5. ✅ 构建 Docker 镜像
6. ✅ 启动服务
7. ✅ 健康检查

---

### 方式二：手动部署

#### 1. 创建数据目录
```bash
mkdir data logs database
```

#### 2. 构建镜像
```bash
docker-compose build --no-cache
```

#### 3. 启动服务
```bash
docker-compose -p logistics up -d
```

#### 4. 查看日志
```bash
docker-compose logs -f
```

#### 5. 健康检查
```bash
curl http://localhost:5000/api/health
```

---

## 📊 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端页面** | http://localhost:8080 | Vue 3 应用 |
| **后端 API** | http://localhost:5000 | Flask RESTful |
| **API 文档** | http://localhost:5000/api/docs | 接口列表 |
| **健康检查** | http://localhost:5000/api/health | 服务状态 |

---

## 👤 登录账号

| 角色 | 账号 | 密码 | 权限 |
|------|------|------|------|
| 管理员 | `admin` | `admin123` | 全功能访问 |
| 普通用户 | `user` | `user123` | 只读权限 |
| 司机 | `driver` | `driver123` | 小程序账号 |

---

## 🛠️ 常用命令

### 服务管理
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看后端日志
docker logs logistics-backend -f

# 查看前端日志
docker logs logistics-frontend -f
```

### 镜像管理
```bash
# 重新构建
docker-compose build --no-cache

# 删除旧镜像
docker image prune -f

# 查看镜像
docker images | grep logistics
```

### 数据管理
```bash
# 进入后端容器
docker exec -it logistics-backend bash

# 进入数据库目录
docker exec -it logistics-backend ls /app/data

# 备份数据库
docker cp logistics-backend:/app/data/logistics.db ./backup/

# 恢复数据库
docker cp ./backup/logistics.db logistics-backend:/app/data/
```

---

## 🔧 配置说明

### 环境变量

在 `docker-compose.yml` 中配置：

```yaml
environment:
  # Flask 配置
  - FLASK_CONFIG=docker
  - FLASK_ENV=production
  
  # 安全密钥（⚠️ 生产环境必须修改！）
  - SECRET_KEY=your-secret-key-here
  - JWT_SECRET_KEY=your-jwt-secret-here
  
  # API Keys
  - AMAP_KEY=e471e7d99965ef1f1a0d4113f580f5db
  - TIANAPI_KEY=e2c7bbdbce2502c8460aa05ad0d57fe1
```

### 数据持久化

数据目录映射：
```yaml
volumes:
  - ./data:/app/data          # 数据库文件
  - ./logs:/app/logs          # 日志文件
  - ./database:/app/database  # 备份数据
```

---

## 🔒 生产环境加固

### 1. 修改默认密钥
```yaml
environment:
  - SECRET_KEY=<生成一个强密码>
  - JWT_SECRET_KEY=<生成另一个强密码>
```

生成方式：
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. 修改默认密码
首次登录后立即修改 admin 密码！

### 3. 配置 HTTPS（推荐使用 Nginx 反向代理）

创建 `nginx-ssl.conf`：
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
    }
}
```

### 4. 防火墙配置
```bash
# 只开放必要端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## 🐛 常见问题

### Q1: 端口被占用
**错误**: `port is already allocated`

**解决**:
```bash
# 查看端口占用
netstat -ano | findstr :5000
netstat -ano | findstr :8080

# 修改 docker-compose.yml 中的端口映射
ports:
  - "5001:5000"  # 改用其他端口
```

### Q2: 镜像构建失败
**原因**: 网络问题或依赖下载失败

**解决**:
```bash
# 使用国内镜像源（已配置）
# 或手动重试
docker-compose build --no-cache --progress=plain
```

### Q3: 数据库为空
**原因**: 首次启动需要初始化

**解决**:
```bash
# 进入容器初始化
docker exec -it logistics-backend python scripts/init_db.py

# 或生成测试数据
docker exec -it logistics-backend python add_test_data.py
```

### Q4: WebSocket 连接失败
**原因**: Nginx 代理配置问题

**解决**: 检查 `nginx.conf` 中的 WebSocket 配置：
```nginx
location /socket.io/ {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Q5: 内存不足
**错误**: `OOMKilled`

**解决**:
```yaml
# 在 docker-compose.yml 中增加内存限制
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

---

## 📈 性能优化

### 1. 调整 Worker 数量
```dockerfile
# backend/Dockerfile
CMD ["gunicorn", "--workers", "2", ...]
```

### 2. 启用 Nginx 缓存
```nginx
# nginx.conf
proxy_cache_path /tmp/cache levels=1:2 keys_zone=api_cache:10m;

location /api/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
}
```

### 3. 数据库优化
```python
# 添加索引
db.Index('idx_order_status', Order.status)
db.Index('idx_vehicle_status', Vehicle.status)
```

---

## 📦 升级指南

### 从旧版本升级

```bash
# 1. 备份数据
docker cp logistics-backend:/app/data ./backup

# 2. 停止旧服务
docker-compose down

# 3. 拉取新代码
git pull

# 4. 重新构建
docker-compose build --no-cache

# 5. 启动新服务
docker-compose up -d

# 6. 恢复数据（如需要）
docker cp ./backup/data logistics-backend:/app/
```

---

## 📞 技术支持

- **项目文档**: `README.md`
- **演示文档**: `memory/Logistics_Project_Presentation_Document_Detailed.md`
- **开发者**: 小彩 (AI 开发助手)
- **项目负责人**: 小宇

---

**最后更新**: 2026-03-30  
**版本**: v2.0  
**维护者**: 小彩 💫
