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

## 智能调度口径

当前智能调度已经切换为统一调度引擎：

- 默认 `data_source=auto`，优先读取 PostgreSQL `shipment_facts` 真实物流明细；仅在无可用事实数据或显式选择时回退旧 `orders` 表。
- 5 万明细不直接一次性求解，前端与 API 通过 dispatch wave 控制波次数量与筛选条件。
- `/api/dispatch/preview` 只生成预览，不修改原始物流明细。
- `/api/dispatch/apply` 确认执行后写入 `dispatch_scenarios` / `dispatch_assignments`，用于回放、审计和后续 AI 训练样本。
- AI/DQL/DQN 当前为 shadow mode，只提供风险、ETA、策略评分元数据；容量、车辆、唯一分配等硬约束仍由调度引擎保底。

后端启动时会使用 `checkfirst=True` 自动确保以下增量表存在，不会改写 `shipment_facts`：

```text
dispatch_scenarios
dispatch_assignments
```

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

登录后建议继续验证调度链路：

```bash
TOKEN=<login-access-token>
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/dispatch/health
curl -X POST http://127.0.0.1:5000/api/dispatch/preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit":20,"data_source":"auto","algorithm":"balanced","use_precise_distance":false}'
```

预期响应应包含 `plans`、`unassigned_orders`、`diagnostics`、`solver`、`data_source`、`distance_source`、`provider_status`、`authenticity_level`。如果车辆只有少量运营运力，未分配原因应出现在 `diagnostics.reason_counts` 或 `unassigned_orders[].reason` 中，而不是无解释的 0 单结果。

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
python scripts\deploy_tencent_cloud_command_center.py --identity-file <local-ssh-private-key> --skip-dump
```

常用参数：

- `--skip-dump`：只更新代码和容器，不重新导入数据库。
- `--identity-file`：使用本地 SSH 私钥登录服务器；使用该模式时远程用户需要具备免密 sudo。
- `--verify`：只执行远程健康检查。
- `--check-only`：只检查远程主机环境。

脚本会保留远端已有 `.env.production`。请不要把真实 `.env.production`、SSH 密码、数据库密码或 API Key 提交到 GitHub。

食品供应链案例需要随 release 包一起发布。生产 compose 会将 `./案例一：食品供应链仓配优化(1)` 只读挂载到后端容器 `/app/cases/food-supply`，并通过 `FOOD_SUPPLY_CASE_DIR` 指定读取路径，避免案例 Excel 与生产 `shipment_facts` 混用。
