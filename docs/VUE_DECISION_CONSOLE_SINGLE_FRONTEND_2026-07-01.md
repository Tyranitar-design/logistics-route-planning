# Vue 单前端决策中枢修复记录（2026-07-01）

## 背景

双前端模式（`frontend` + `frontend-next`）在登录态、端口占用、跨运行时跳转和后端并发请求上带来了额外不稳定性。当前项目运行底座回到 Vue 3 + Vite 的 `frontend/`，AI 增强能力作为 Vue 原生页面挂载在同一个登录态、同一个路由和同一个 HTTP API 体系里。

`frontend-next/` 保留为历史参考和迁移材料，但普通本地运行、登录、导航、AI 决策控制台访问不再依赖 Next.js，也不需要启动 `5174` 端口。

## 当前入口

- Vue 生产/开发前端：`frontend/`
- AI 决策中枢路由：`/decision-console`
- 页面文件：`frontend/src/views/DecisionConsoleView.vue`
- 路由挂载：`frontend/src/router/index.js`
- 侧边栏入口：`frontend/src/views/Layout.vue`，菜单项为「智能决策中枢」

## 关键修复

- 将 AI 决策中枢合并到 Vue 路由，避免 Vue 登录后再跳 Next 导致登录态超时。
- 移除 Vue 侧对 `VITE_NEXT_CONSOLE_URL` 的运行依赖。
- `frontend/.env.development` 只保留 Vue 单前端所需 WebSocket 配置。
- Vite 开发代理固定指向 `http://127.0.0.1:5000`，和推荐后端启动地址一致。
- `frontend/src/main.js` 不再在登录页提前连接 WebSocket，只暴露 `window.wsService`。
- `frontend/src/services/websocket.js` 改为幂等连接，支持 `VITE_WS_DISABLED`、`VITE_WS_URL`、`VITE_WS_TRANSPORTS`，开发环境默认 polling，失败只做温和提示。
- `backend/run.py` 新增 `DISABLE_KAFKA_CONSUMER` 开关，本地核心链路启动可避免未启动 Kafka 时刷 `NoBrokersAvailable`。
- `backend/config.py` 默认关闭 SQL echo，避免真实数据接口把日志放大到影响排障。
- 修复 `/api/ai-prediction/scorecard` 在时间序列 backtest 数据不足时可能 500 的问题。

## 推荐启动方式

后端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
$env:DISABLE_ML_ROUTES='1'
$env:DISABLE_KAFKA_CONSUMER='1'
$env:FLASK_HOST='127.0.0.1'
$env:FLASK_PORT='5000'
$env:FLASK_DEBUG='False'
$env:SQLALCHEMY_ECHO='0'
.\.venv\Scripts\python.exe run.py
```

前端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：

```text
http://127.0.0.1:5173/decision-console
```

## 验证记录

2026-07-01 本地验证：

- `frontend npm run build` 通过。
- `backend .\.venv\Scripts\python.exe -m pytest tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`20 passed`。
- 本机 HTTP 烟测：
  - `http://127.0.0.1:5000/api/health` 返回 200。
  - `http://127.0.0.1:5173/decision-console` 返回 200。
- 已知构建提示仍存在：
  - glyphicons 字体路径未解析提示。
  - 旧 CSS `*zoom` minify warning。
  - 部分 bundle 大于 500 kB 的 Vite chunk warning。

这些提示是旧前端依赖/构建体积问题，不阻断本次 Vue 单前端修复。

## 后续建议

- 若继续演进 AI 专家决策系统，优先在 Vue `DecisionConsoleView.vue` 拆分业务组件和 API 适配层，而不是恢复双前端跳转。
- 可把决策中枢的聚合数据进一步收敛成后端 `/api/control-tower/scorecard`，减少前端并发请求数量。
- `frontend-next/` 后续只作为参考代码或迁移素材；正式运行说明、部署文档和用户入口以 Vue 为准。
