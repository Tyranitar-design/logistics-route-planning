# 🧠 Claude Code 专属记忆

> 这是 Claude Code 的长期记忆文件，记录经验教训、代码模式、项目知识

---

## 代码模式库

### 模式 1: OR-Tools 通用求解器
```python
# 标准流程：Manager → Routing → Callback → Dimension → Solve → Extract
# 关键：约束添加顺序为 距离→容量→时间→配对→时间窗
```

### 模式 2: Flask API 路由
```python
# 标准格式：Blueprint → 路由函数 → 数据验证 → 业务逻辑 → 返回JSON
```

### 模式 3: Vue 3 组件
```vue
<!-- 标准格式：<script setup> → ref/reactive → onMounted → methods → template -->
```

---

## 经验教训

_（Claude Code 每次完成重要任务后在这里记录经验）_

---

## 项目知识

### 物流系统架构
- 后端：Flask + SQLAlchemy + JWT + WebSocket
- 前端：Vue 3 + Element Plus + ECharts + Three.js
- 部署：Docker + Nginx（腾讯云 122.152.220.116）

### 关键文件位置
- 调度服务：`backend/app/services/dispatch_service.py`
- 路径算法：`backend/app/services/path_algorithm.py`
- ML 预测：`backend/app/services/prediction_service.py`
- 数据模型：`backend/app/models/`

### 开发规范
- 中文注释
- 中文 Git commit message
- TDD: RED → GREEN → REFACTOR
- 不删 C 盘文件

---

## 待同步给小彩

_（需要小彩处理的事项写在这里）_

---

_最后更新: 2026-04-15_
