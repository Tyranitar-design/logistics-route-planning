# 算法引擎升级设计

**变更名称**: algorithm-engine-upgrade  
**设计日期**: 2026-05-05

---

## 技术方案

### 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                    前端决策可视化层                           │
│  ParetoFrontPage / MultiObjectivePage / SolverCompareView   │
│  - Pareto 散点图                                             │
│  - 平行坐标图                                                │
│  - 求解器性能对比                                             │
│  - 距离精度报告                                               │
└──────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────┐
│                          API 层                              │
│  POST /api/optimization/solve                               │
│  POST /api/optimization/compare                             │
│  POST /api/optimization/evaluate                            │
│  GET  /api/optimization/pareto                              │
│  GET  /api/distance/precision-report                        │
└──────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────┐
│                       统一编排层                              │
│  VRPProblemBuilder                                           │
│  SolverRecommendationEngine                                  │
│  ResultEvaluator                                             │
└──────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────┐
│                       距离数据底座                            │
│  PreciseDistanceProvider                                     │
│  - SQLite 缓存                                               │
│  - 高德批量距离 API                                          │
│  - Haversine × 1.3 兜底                                      │
└──────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────┐
│                       求解器执行层                            │
│  Gurobi / OR-Tools / PyVRP / pymoo / ALNS / GA / ...        │
└──────────────────────────────────────────────────────────────┘
```

---

## 一、后端设计

### 1.1 PreciseDistanceProvider

新增统一距离提供层，避免每个求解器各自决定距离来源。

#### 责任
- 获取节点坐标并构建距离矩阵
- 优先使用高德缓存中的真实道路距离
- 缓存未命中时批量调用高德 API
- API 不可用时使用 Haversine × 1.3 兜底
- 返回精度报告（exact / approx / fallback）

#### 建议文件
- `backend/app/services/precise_distance_provider.py`

#### 结果结构

```python
class DistanceMatrixResult:
    node_ids: List[int]
    distance_matrix_km: List[List[float]]
    duration_matrix_min: List[List[float]]
    precision: Dict[str, int]
    metadata: Dict[str, Any]
```

---

### 1.2 VRPProblemBuilder

统一从订单、车辆、节点等业务对象构建优化问题。

#### 责任
- 根据订单和车辆构建 `OptimizationProblem`
- 自动注入精确距离矩阵
- 自动识别问题类型（CVRP / VRPTW / PDP / 多目标等）
- 统一输出供各求解器使用的数据结构

#### 建议文件
- `backend/app/services/vrp_problem_builder.py`

#### 核心接口

```python
class VRPProblemBuilder:
    def build_from_payload(self, payload: Dict) -> OptimizationProblem:
        ...

    def detect_problem_type(self, payload: Dict) -> ProblemType:
        ...
```

---

### 1.3 SolverRecommendationEngine

建立规则驱动的求解器推荐能力。

#### 推荐逻辑示例

| 条件 | 推荐求解器 |
|------|-----------|
| 小规模 + 需要最优 | Gurobi |
| 中大规模 + 快速响应 | OR-Tools / ALNS |
| 多目标 + 展示 Pareto | pymoo NSGA-II/III |
| VRPTW | OR-Tools / Gurobi VRPTW / PyVRP |
| 工程演示 + 稳定性 | OR-Tools |

#### 建议文件
- `backend/app/services/solver_recommendation_engine.py`

---

### 1.4 ResultEvaluator

为每次求解结果生成统一质量报告。

#### 责任
- 验证可行性（容量/时间窗/重复节点/遗漏节点）
- 计算 gap（若有基准或 Gurobi 最优参考）
- 统计距离精度占比
- 评估 Pareto 前沿质量（HV / Spread / 非支配数量）
- 给出结果摘要和建议

#### 建议文件
- `backend/app/services/result_evaluator.py`

#### 结果结构

```python
class QualityReport:
    feasible: bool
    violations: List[str]
    objective_summary: Dict[str, float]
    gap_to_reference: Optional[float]
    pareto_metrics: Dict[str, float]
    distance_precision_ratio: float
    recommendation: str
```

---

### 1.5 求解器层升级

#### OR-Tools
- 接入统一精确距离矩阵
- 支持更明确的 VRPTW 参数入口
- 参数可配置：初始解、局部搜索、时限、罚项

#### Gurobi
- 保持精确求解主力地位
- 与统一距离矩阵对接
- 输出 gap 和状态信息用于评估

#### PyVRP
- 替换当前欧氏距离模式
- 使用真实道路距离建模 edge
- 校验 PyVRP 数据适配方式

#### pymoo NSGA-II / III
- 不再只使用简单贪心切割解码
- 实现 VRP 路线感知交叉与变异算子
- 引入可行解修复算子

#### ALNS / Genetic
- 调整为使用统一问题数据
- 增加可行解修复和参数自适应

---

## 二、前端设计

### 2.1 页面增强

| 页面/组件 | 增强内容 |
|-----------|----------|
| `MultiObjectivePage.vue` | 增加 Pareto 前沿交互展示 |
| `ParetoFrontPage.vue` | 增加筛选、悬浮详情、方案选择 |
| `ScenarioCompareView.vue` | 增加方案质量评估和推荐说明 |
| `RouteCompareChart.vue` | 扩展为多维指标对比 |

### 2.2 新增组件建议

- `ParetoScatterPlot.vue`
- `ParallelCoordinatesChart.vue`
- `SolverRecommendationCard.vue`
- `DistancePrecisionCard.vue`
- `QualityReportPanel.vue`

### 2.3 前端交互目标

- 用户能看到哪些点是 Pareto 最优
- 用户能理解每个方案在距离/时间/成本/风险上的取舍
- 用户能看到系统推荐为什么推荐某求解器
- 用户能看到本次结果用了多少真实道路距离

---

## 三、API 设计

### 3.1 统一求解入口

```http
POST /api/optimization/solve
```

请求示例：

```json
{
  "problem_type": "vrptw",
  "objective_mode": "multi_objective",
  "solver": "auto",
  "orders": [],
  "vehicles": [],
  "options": {
    "time_limit": 60,
    "use_precise_distance": true
  }
}
```

返回重点：
- 使用了哪个求解器
- 距离矩阵精度报告
- 结果质量报告
- 若是多目标，返回 Pareto 集

### 3.2 求解器对比入口

```http
POST /api/optimization/compare
```

### 3.3 评估入口

```http
POST /api/optimization/evaluate
```

### 3.4 距离精度报告

```http
GET /api/distance/precision-report
```

---

## 四、文件结构建议

```text
backend/app/services/
├── precise_distance_provider.py
├── vrp_problem_builder.py
├── solver_recommendation_engine.py
├── result_evaluator.py
└── optimization_engine/
    └── solvers/
        ├── ortools_solver.py
        ├── gurobi_solver.py
        ├── pyvrp_solver.py
        ├── pymoo_solver.py
        ├── alns_solver.py
        └── genetic_solver.py

frontend/src/components/
├── ParetoScatterPlot.vue
├── ParallelCoordinatesChart.vue
├── SolverRecommendationCard.vue
├── DistancePrecisionCard.vue
└── QualityReportPanel.vue
```

---

## 五、性能与工程约束

| 项目 | 约束 |
|------|------|
| 并发求解器数 | ≤ 3 |
| 高德距离批量请求 | 充分利用缓存，避免重复请求 |
| 求解超时 | 默认 60~300 秒可配 |
| 结果可解释性 | 每次结果都要有质量说明 |
| 精度优先级 | 真实道路距离 > Haversine 修正 > 欧氏距离（禁止再回退到欧氏作为主流程） |

---

## 六、测试策略

### 单元测试
- 距离提供者返回矩阵和精度报告
- 问题构建器输出结构正确
- 推荐引擎规则正确
- 评估器能识别约束违规
- NSGA 自定义算子行为正确

### 集成测试
- 从 API 输入到求解结果完整跑通
- 主力求解器能用同一问题数据对比
- 多目标结果可生成 Pareto 前沿

### 基准测试
- 用运筹优化学习目录中的示例和真实问题做对比
- 小规模问题用 Gurobi 做参考解
- 统计 OR-Tools / ALNS / PyVRP / pymoo 的表现

---

## 七、实施建议

建议按照以下顺序推进：

1. **B1** 先打牢距离底座
2. **B2** 再升级多目标核心算法
3. **B3** 再做智能推荐与评估
4. **B4** 最后把前端展示做强
5. **B5** 用基准与测试证明升级有效

这个顺序最稳，不容易把系统一下子改乱。
