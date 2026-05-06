# 算法引擎升级任务清单

**变更名称**: algorithm-engine-upgrade  
**创建日期**: 2026-05-05

---

## B1 距离数据统一

### 1.1 距离提供层
- [ ] 1.1.1 创建 `backend/app/services/precise_distance_provider.py`
- [ ] 1.1.2 封装统一距离矩阵返回结构
- [ ] 1.1.3 接入 `distance_cache_service.py`
- [ ] 1.1.4 增加精度统计（exact / approx / total）
- [ ] 1.1.5 增加求解器适配输出格式

### 1.2 问题数据层
- [ ] 1.2.1 改造 `optimization_engine/problems.py` 支持显式注入精确距离矩阵
- [ ] 1.2.2 评估并补充 `duration_matrix` / 精度元数据承载能力
- [ ] 1.2.3 保留旧欧氏自动构造作为兼容 fallback

### 1.3 求解器接入
- [ ] 1.3.1 升级 `ortools_solver.py` 使用统一精确距离矩阵
- [ ] 1.3.2 升级 `gurobi_solver.py` 使用统一精确距离矩阵
- [ ] 1.3.3 升级 `pyvrp_solver.py` 使用统一精确距离矩阵
- [ ] 1.3.4 升级 `pymoo_solver.py` 使用统一精确距离矩阵
- [ ] 1.3.5 升级 `alns_solver.py` 使用统一问题数据
- [ ] 1.3.6 升级 `genetic_solver.py` 使用统一问题数据

### 1.4 API 与验证
- [ ] 1.4.1 升级 `/api/optimization/solve` 显式使用精确距离构建
- [ ] 1.4.2 升级 `/api/optimization/compare` 显式使用精确距离构建
- [ ] 1.4.3 创建距离精度报告接口
- [ ] 1.4.4 增加距离矩阵构建测试
- [ ] 1.4.5 增加求解器距离接入测试
- [ ] 1.4.6 完成离线 + 在线验证

---

## B2 多目标优化精度提升

### 2.1 结构搭建
- [ ] 2.1.1 创建 `backend/app/services/optimization_engine/operators/vrp_crossover.py`
- [ ] 2.1.2 创建 `backend/app/services/optimization_engine/operators/vrp_mutation.py`
- [ ] 2.1.3 创建 `backend/app/services/optimization_engine/operators/vrp_repair.py`
- [ ] 2.1.4 创建 `backend/app/services/optimization_engine/metrics/pareto_metrics.py`

### 2.2 VRP 专用算子
- [ ] 2.2.1 实现 OX 交叉算子
- [ ] 2.2.2 实现 PMX 交叉算子
- [ ] 2.2.3 实现 Swap 变异算子
- [ ] 2.2.4 实现 2-opt 变异算子
- [ ] 2.2.5 实现 Relocation / Or-opt 最小版

### 2.3 可行解机制
- [ ] 2.3.1 实现容量约束修复器
- [ ] 2.3.2 保证 repair 后无重复客户
- [ ] 2.3.3 保证 repair 后无遗漏客户
- [ ] 2.3.4 保证 repair 后无超载

### 2.4 pymoo 求解器升级
- [ ] 2.4.1 重构 `pymoo_solver.py` 的编码/解码逻辑
- [ ] 2.4.2 为 NSGA-II 接入自定义算子
- [ ] 2.4.3 为 NSGA-III 接入自定义算子
- [ ] 2.4.4 保留 B1 距离精度元数据透传

### 2.5 多目标结果增强
- [ ] 2.5.1 增强 `multi_objective.py` 推荐输出
- [ ] 2.5.2 实现 Pareto 解数量统计
- [ ] 2.5.3 实现目标范围 / spread 等基础指标
- [ ] 2.5.4 评估是否加入 ε-约束法（仅评估，不强制本轮实现）

### 2.6 测试与验证
- [ ] 2.6.1 创建 `backend/tests/test_vrp_multiobjective_operators.py`
- [ ] 2.6.2 创建 `backend/tests/test_pymoo_solver_b2.py`
- [ ] 2.6.3 完成最小多目标样例验证
- [ ] 2.6.4 完成 B2 验证补记

---

## B3 求解器智能化

### 3.1 问题构建
- [ ] 3.1.1 创建 `backend/app/services/vrp_problem_builder.py`
- [ ] 3.1.2 统一构建 CVRP / MULTI_OBJECTIVE 问题
- [ ] 3.1.3 接入 B1 `PreciseDistanceProvider`
- [ ] 3.1.4 输出 `build_metadata`

### 3.2 推荐引擎
- [ ] 3.2.1 创建 `backend/app/services/solver_recommendation_engine.py`
- [ ] 3.2.2 编写规则推荐逻辑
- [ ] 3.2.3 输出推荐原因和备选项

### 3.3 结果评估
- [ ] 3.3.1 创建 `backend/app/services/result_evaluator.py`
- [ ] 3.3.2 增加重复/遗漏/超载校验
- [ ] 3.3.3 统一 gap / 距离精度 / Pareto 摘要输出
- [ ] 3.3.4 生成 `quality_report`

### 3.4 统一接口
- [ ] 3.4.1 增强 `/api/optimization/solve` 支持 `solver=auto`
- [ ] 3.4.2 增强 `/api/optimization/compare` 使用统一 builder/evaluator
- [ ] 3.4.3 保持兼容旧字段，新增 `quality_report` / `build_metadata`

### 3.5 测试与验证
- [ ] 3.5.1 创建 `backend/tests/test_vrp_problem_builder.py`
- [ ] 3.5.2 创建 `backend/tests/test_solver_recommendation_engine.py`
- [ ] 3.5.3 创建 `backend/tests/test_result_evaluator.py`
- [ ] 3.5.4 完成 B3 验证补记

---

## B4 前端可视化增强

### 4.1 新增组件
- [ ] 4.1.1 创建 `ParetoScatterPlot.vue`
- [ ] 4.1.2 创建 `ParallelCoordinatesChart.vue`
- [ ] 4.1.3 创建 `SolverRecommendationCard.vue`
- [ ] 4.1.4 创建 `DistancePrecisionCard.vue`
- [ ] 4.1.5 创建 `QualityReportPanel.vue`

### 4.2 页面集成
- [ ] 4.2.1 升级 `MultiObjectivePage.vue`
- [ ] 4.2.2 升级 `ParetoFrontPage.vue`
- [ ] 4.2.3 升级 `ScenarioCompareView.vue`
- [ ] 4.2.4 升级 `RouteCompareChart.vue`

### 4.3 可视化能力
- [ ] 4.3.1 展示 Pareto 散点图
- [ ] 4.3.2 展示平行坐标图
- [ ] 4.3.3 展示求解器推荐说明
- [ ] 4.3.4 展示距离精度和结果质量报告

---

## B5 集成测试与验收

### 5.1 后端测试
- [ ] 5.1.1 编写距离提供层单元测试
- [ ] 5.1.2 编写问题构建器单元测试
- [ ] 5.1.3 编写推荐引擎单元测试
- [ ] 5.1.4 编写评估器单元测试
- [ ] 5.1.5 编写主力求解器集成测试

### 5.2 基准验证
- [ ] 5.2.1 使用小规模问题对比 Gurobi 最优解
- [ ] 5.2.2 对比 OR-Tools / ALNS / PyVRP / pymoo 解质量
- [ ] 5.2.3 验证多目标 Pareto 前沿质量
- [ ] 5.2.4 验证真实道路距离覆盖率

### 5.3 前端验收
- [ ] 5.3.1 验证 Pareto 交互展示
- [ ] 5.3.2 验证推荐说明展示
- [ ] 5.3.3 验证质量报告展示

---

## 验收标准

- [ ] 所有主力求解器使用统一精确距离数据
- [ ] 多目标优化具备可解释的 Pareto 前沿
- [ ] 系统可自动推荐求解器并说明原因
- [ ] 每次求解可输出质量评估
- [ ] 前端可以有效展示决策信息
- [ ] 核心测试通过
