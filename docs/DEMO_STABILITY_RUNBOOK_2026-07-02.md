# 物流平台演示稳定运行手册（2026-07-02）

## 目标

把当前 Vue 单前端、Flask 后端、PostgreSQL/PostGIS、GIS Provider、Agent Gateway 和 Decision 场景接口收束成可启动、可冒烟、可解释、可演示的运行态。

## 推荐启动

后端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
$env:POSTGRES_DATABASE_URL="<your-postgresql-url>"
$env:DATABASE_URL=$env:POSTGRES_DATABASE_URL
$env:DISABLE_ML_ROUTES="1"
$env:DISABLE_KAFKA_CONSUMER="1"
$env:FLASK_HOST="127.0.0.1"
$env:FLASK_PORT="5000"
$env:FLASK_DEBUG="False"
.\.venv\Scripts\python.exe run.py
```

前端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

MiniMax-M3 Agent 可选启用：

```powershell
$env:MINIMAX_BASE_URL="https://vsllm.com/v1"
$env:MINIMAX_MODEL="MiniMax-M3"
$env:MINIMAX_API_KEY="<your-rotated-key>"
```

不要把 API key、数据库密码、SSH 密钥、license 内容写入仓库、前端、文档或记忆文件。

## 冒烟命令

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
.\.venv\Scripts\python.exe scripts\enterprise_smoke_harness.py --base-url http://127.0.0.1:5000
```

如果需要覆盖登录态接口：

```powershell
$env:LOGISTICS_AUTH_TOKEN="<jwt-access-token>"
.\.venv\Scripts\python.exe scripts\enterprise_smoke_harness.py --base-url http://127.0.0.1:5000 --token $env:LOGISTICS_AUTH_TOKEN
```

脚本会区分：

- `ok`: 接口成功返回。
- `auth_required`: 路由存在，但需要登录或权限。
- `route_missing`: 404，通常是旧后端进程或当前源码未注册蓝图。
- `server_error`: 路由存在但后端内部错误，需要看 Flask 日志。

## 关键接口期望

`GET /api/ready` 应至少看到：

- `status=ready`
- `database=connected`
- `database_runtime.backend=postgresql`
- `database_runtime.shipment_facts=50000`
- `registered_capabilities.missing=[]`

`GET /api/runtime/capabilities?solver_probe=0` 应至少看到：

- `interpreter.using_project_venv=true`
- `registered_capabilities.missing=[]`
- `demo_readiness.status=ready|watch`
- `demo_readiness.blocking_issues=[]`
- `security.api_keys_returned=false`

## 常见排查

### 404 或页面提示“接口不存在”

优先怀疑 5000 端口还跑着旧 `run.py` 进程。检查：

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen
```

停止旧进程后，用 `backend\.venv\Scripts\python.exe run.py` 从当前仓库重新启动。

### 401 或 403

这通常表示路由存在，但需要登录。先在 Vue 前端重新登录，或给 smoke harness 传入 JWT token。

### Agent 降级

`MINIMAX_API_KEY_MISSING` 表示后端没有读取到 MiniMax key。Agent 仍可显示工具预演和 dry-run 草稿，但不会调用 LLM。

### GIS 降级

高德、天地图、PostGIS、本地图算法分别承担不同角色。页面和接口必须展示 `distance_source`、`path_source`、`authenticity_level`、`fallback_reason`，不能把本地 Haversine 或 OD 聚合说成真实导航路径。

## 页面验收

登录后逐页打开：

- 指挥总览
- 地图视图
- 智能调度
- 智能决策中枢
- AI 预测
- 异常检测
- 网络设计
- 优化引擎

智能决策中枢首屏应显示演示健康条；专家 Agent 抽屉默认不调用 LLM，只有点击“获取建议”才请求 `/api/agent/chat`。
