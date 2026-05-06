# 求解器对比功能任务清单

**变更名称**: add-solver-comparison-feature  
**创建日期**: 2026-04-22

---

## 1. 后端开发

### 1.1 数据模型

- [ ] 1.1.1 创建 `backend/app/models/solver_comparison.py`
- [ ] 1.1.2 定义 `ComparisonRequest` 模型
- [ ] 1.1.3 定义 `ComparisonResult` 模型
- [ ] 1.1.4 定义 `PerformanceMetrics` 模型
- [ ] 1.1.5 定义 `ComparisonSummary` 模型

### 1.2 服务层

- [ ] 1.2.1 创建 `backend/app/services/solver_comparison.py`
- [ ] 1.2.2 实现 `SolverComparisonService` 类
- [ ] 1.2.3 实现并发执行求解器方法
- [ ] 1.2.4 实现性能指标收集方法
- [ ] 1.2.5 实现对比摘要生成方法
- [ ] 1.2.6 实现超时处理逻辑
- [ ] 1.2.7 实现并发控制（最大 3 个）

### 1.3 API 接口

- [ ] 1.3.1 创建 `backend/app/api/solver_comparison.py`
- [ ] 1.3.2 实现 `POST /api/solver-comparison/compare` 接口
- [ ] 1.3.3 实现 `GET /api/solver-comparison/result/:id` 接口
- [ ] 1.3.4 实现 `POST /api/solver-comparison/export` 接口
- [ ] 1.3.5 在 `backend/app/api/__init__.py` 注册路由

---

## 2. 前端开发

### 2.1 API 调用

- [ ] 2.1.1 创建 `frontend/src/api/solverComparison.ts`
- [ ] 2.1.2 实现 `compareSolvers` 方法
- [ ] 2.1.3 实现 `getComparisonResult` 方法
- [ ] 2.1.4 实现 `exportReport` 方法

### 2.2 组件开发

- [ ] 2.2.1 创建 `frontend/src/components/SolverSelector.vue`
- [ ] 2.2.2 创建 `frontend/src/components/ComparisonResults.vue`
- [ ] 2.2.3 创建 `frontend/src/components/ComparisonCharts.vue`
- [ ] 2.2.4 实现求解器选择器（多选）
- [ ] 2.2.5 实现结果表格展示
- [ ] 2.2.6 实现雷达图（综合性能）
- [ ] 2.2.7 实现柱状图（单项指标）
- [ ] 2.2.8 实现时间线图表

### 2.3 页面开发

- [ ] 2.3.1 创建 `frontend/src/views/SolverComparison.vue`
- [ ] 2.3.2 集成求解器选择器
- [ ] 2.3.3 集成问题选择器
- [ ] 2.3.4 实现对比控制（启动/取消）
- [ ] 2.3.5 集成结果展示组件
- [ ] 2.3.6 实现导出报告功能
- [ ] 2.3.7 在路由中注册页面

---

## 3. 测试

### 3.1 单元测试

- [ ] 3.1.1 创建 `backend/tests/test_solver_comparison.py`
- [ ] 3.1.2 测试数据模型验证
- [ ] 3.1.3 测试对比摘要生成
- [ ] 3.1.4 测试性能指标归一化

### 3.2 集成测试

- [ ] 3.2.1 测试完整对比流程
- [ ] 3.2.2 测试并发控制
- [ ] 3.2.3 测试超时处理

### 3.3 前端测试

- [ ] 3.3.1 测试求解器选择器交互
- [ ] 3.3.2 测试结果展示
- [ ] 3.3.3 测试图表渲染

---

## 4. 文档和部署

### 4.1 文档

- [ ] 4.1.1 更新 API 文档
- [ ] 4.1.2 更新用户手册
- [ ] 4.1.3 添加功能截图

### 4.2 部署

- [ ] 4.2.1 更新 Docker 配置（如需要）
- [ ] 4.2.2 更新依赖列表
- [ ] 4.2.3 部署到测试环境
- [ ] 4.2.4 部署到生产环境

---

## 验收标准

- [ ] 用户可以选择多个求解器进行对比
- [ ] 对比结果以表格和图表形式展示
- [ ] 对比报告可导出为 PDF
- [ ] 对比任务支持取消和重试
- [ ] 所有测试通过
- [ ] API 文档更新
- [ ] 用户手册更新

---

## 预计时间

| 任务 | 预计时间 |
|------|----------|
| 后端开发 | 2 小时 |
| 前端开发 | 2 小时 |
| 测试 | 1 小时 |
| 文档和部署 | 1 小时 |
| **总计** | **6 小时** |
