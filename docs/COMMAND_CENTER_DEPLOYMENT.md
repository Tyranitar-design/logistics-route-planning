# 物流指挥中枢部署说明

本文档对应当前主项目目录：

```text
C:\tmp\logistics-route-command-center-layout-dashboard-shell
```

系统当前以“物流指挥中枢 / Logistics Command Center”为主界面，核心运行链路为：

- 前端：Vue 3 + Vite + Element Plus + ECharts/Leaflet/Three.js
- 后端：Flask + SQLAlchemy + JWT + SocketIO
- 数据库：PostgreSQL/PostGIS
- 缓存：Redis
- 生产编排：`docker-compose.prod.yml`

## 数据库口径

当前生产数据使用 PostgreSQL/PostGIS，不再以 SQLite 演示库作为主数据源。

已验证的数据规模：

```text
shipment_facts                  50000
raw_logistics_shipment_records  50000
nodes                           21
routes                          306
vehicles                        2
```

大数据平台目录仍保留在仓库中，但当前腾讯云核心部署只启动 PostgreSQL、Redis、后端、前端四个核心服务。

## 本地启动

后端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
$env:POSTGRES_DATABASE_URL="postgresql://postgres@localhost:5432/logistics_route_system"
$env:DISABLE_ML_ROUTES="1"
D:\物流路径规划系统项目\backend\venv\Scripts\python.exe run.py
```

前端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm install
npm run dev -- --host 127.0.0.1
```

## 生产部署

1. 在服务器上准备 `.env.production`：

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

2. 填入真实密钥和数据库密码：

```dotenv
POSTGRES_DB=logistics_route_system
POSTGRES_USER=logistics
POSTGRES_PASSWORD=<strong-password>
SECRET_KEY=<strong-secret>
JWT_SECRET_KEY=<strong-jwt-secret>
AMAP_WEB_KEY=<amap-web-key>
AMAP_SERVICE_KEY=<amap-service-key>
```

3. 启动核心服务：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

4. 验证：

```bash
curl http://127.0.0.1:5000/api/health
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

## 高德地图与天气

后端会优先调用高德真实服务。若云服务器 DNS、IPv6 或高德服务临时不可用，系统会返回带有 `provider_status=degraded` 的降级结果，前端显示“高德降级估算”，避免地图页中断。

生产 compose 中配置了：

```yaml
extra_hosts:
  - "restapi.amap.com:${AMAP_RESTAPI_IPV4:-59.82.14.114}"
```

如果高德 CDN IPv4 后续变化，可在 `.env.production` 中更新：

```dotenv
AMAP_RESTAPI_IPV4=<new-amap-ipv4>
```

注意：实时路况接口还需要高德控制台开通相应服务权限。如果未开通，接口会返回友好降级状态，而不是页面错误。

## 部署脚本

仓库提供腾讯云部署辅助脚本：

```powershell
python scripts\deploy_tencent_cloud_command_center.py --skip-dump
```

常用参数：

- `--skip-dump`：只更新代码和容器，不重新导入数据库。
- `--verify`：只执行远程健康检查。
- `--check-only`：只检查远程主机环境。

脚本会保留远端已有 `.env.production`。请不要把真实 `.env.production`、SSH 密码、数据库密码或 API Key 提交到 GitHub。
