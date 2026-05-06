# 求解器对比功能设计

**变更名称**: add-solver-comparison-feature  
**设计日期**: 2026-04-22

---

## 技术方案

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     前端层                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  SolverComparisonPanel.vue                      │   │
│  │  - 求解器选择器                                  │   │
│  │  - 对比结果展示                                  │   │
│  │  - 图表可视化                                    │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ComparisonCharts.vue                           │   │
│  │  - 雷达图（综合性能）                            │   │
│  │  - 柱状图（单项指标）                            │   │
│  │  - 时间线（执行过程）                            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                     API 层                              │
│  POST /api/solver-comparison/compare                   │
│  GET  /api/solver-comparison/result/:id                │
│  POST /api/solver-comparison/export                    │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                   服务层                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  SolverComparisonService                        │   │
│  │  - 并发执行多个求解器                            │   │
│  │  - 收集性能指标                                  │   │
│  │  - 生成对比报告                                  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                   求解器层                              │
│  OR-Tools Solver | Gurobi Solver | GA Solver | ...    │
└─────────────────────────────────────────────────────────┘
```

---

## 数据模型

### 对比请求

```python
class ComparisonRequest:
    problem_id: str           # 问题 ID
    solvers: List[str]        # 求解器列表
    options: Dict             # 求解器选项
    timeout: int = 300        # 超时时间（秒）
```

### 对比结果

```python
class ComparisonResult:
    id: str                   # 对比 ID
    problem_id: str           # 问题 ID
    results: List[SolverResult]  # 各求解器结果
    comparison_time: datetime    # 对比时间
    summary: ComparisonSummary   # 对比摘要

class SolverResult:
    solver_name: str          # 求解器名称
    solution: Dict            # 求解结果
    metrics: PerformanceMetrics  # 性能指标
    status: str               # 状态（success/timeout/error）

class PerformanceMetrics:
    solve_time: float         # 求解时间（秒）
    objective_value: float    # 目标函数值
    gap: float                # 最优性间隙
    iterations: int           # 迭代次数
    memory_usage: float       # 内存使用（MB）
```

### 对比摘要

```python
class ComparisonSummary:
    best_solver: str          # 最优求解器
    best_objective: float     # 最优目标值
    fastest_solver: str       # 最快求解器
    fastest_time: float       # 最快时间
    ranking: List[Dict]       # 排名列表
```

---

## API 设计

### 1. 启动对比

```http
POST /api/solver-comparison/compare
Content-Type: application/json

{
  "problem_id": "vrp_001",
  "solvers": ["ortools", "gurobi", "genetic"],
  "options": {
    "ortools": {"time_limit": 60},
    "gurobi": {"mip_gap": 0.01},
    "genetic": {"population": 100, "generations": 50}
  },
  "timeout": 300
}

Response:
{
  "comparison_id": "comp_20260422_001",
  "status": "running",
  "estimated_time": 180
}
```

### 2. 获取对比结果

```http
GET /api/solver-comparison/result/comp_20260422_001

Response:
{
  "id": "comp_20260422_001",
  "status": "completed",
  "results": [
    {
      "solver_name": "ortools",
      "metrics": {
        "solve_time": 12.5,
        "objective_value": 1234.5,
        "gap": 0.0,
        "iterations": 150
      },
      "status": "success"
    },
    ...
  ],
  "summary": {
    "best_solver": "gurobi",
    "best_objective": 1230.2,
    "fastest_solver": "ortools",
    "fastest_time": 12.5
  }
}
```

### 3. 导出报告

```http
POST /api/solver-comparison/export
Content-Type: application/json

{
  "comparison_id": "comp_20260422_001",
  "format": "pdf"
}

Response:
{
  "download_url": "/downloads/comparison_report_20260422_001.pdf"
}
```

---

## 前端设计

### 页面结构

```vue
<template>
  <div class="solver-comparison">
    <!-- 求解器选择 -->
    <SolverSelector 
      :available-solvers="solvers"
      @select="onSolverSelect"
    />
    
    <!-- 问题选择 -->
    <ProblemSelector 
      :problems="problems"
      @select="onProblemSelect"
    />
    
    <!-- 对比控制 -->
    <ComparisonControls 
      @start="startComparison"
      @cancel="cancelComparison"
    />
    
    <!-- 结果展示 -->
    <ComparisonResults 
      v-if="results"
      :results="results"
    />
    
    <!-- 图表可视化 -->
    <ComparisonCharts 
      v-if="results"
      :results="results"
    />
  </div>
</template>
```

### 图表设计

#### 雷达图（综合性能）

```javascript
const radarChartConfig = {
  dimensions: [
    '求解速度',
    '解质量',
    '稳定性',
    '内存效率',
    '收敛速度'
  ],
  series: results.map(r => ({
    name: r.solver_name,
    values: normalizeMetrics(r.metrics)
  }))
}
```

#### 柱状图（单项指标）

```javascript
const barChartConfig = {
  xAxis: '求解器',
  yAxis: '求解时间（秒）',
  data: results.map(r => ({
    name: r.solver_name,
    value: r.metrics.solve_time
  }))
}
```

---

## 性能优化

### 并发控制

```python
class SolverComparisonService:
    MAX_CONCURRENT = 3  # 最大并发数
    
    async def compare_solvers(self, request: ComparisonRequest):
        # 限制并发数量
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        
        tasks = [
            self._run_solver_with_limit(semaphore, solver, request)
            for solver in request.solvers
        ]
        
        results = await asyncio.gather(*tasks)
        return self._generate_summary(results)
```

### 超时处理

```python
async def _run_solver_with_timeout(self, solver, request):
    try:
        result = await asyncio.wait_for(
            solver.solve(request.problem_id),
            timeout=request.timeout
        )
        return result
    except asyncio.TimeoutError:
        return SolverResult(
            solver_name=solver.name,
            status="timeout"
        )
```

---

## 技术选型

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| 前端框架 | Vue 3 + TypeScript | 与现有项目一致 |
| 图表库 | ECharts | 支持雷达图、柱状图 |
| 后端框架 | FastAPI | 与现有项目一致 |
| 异步处理 | asyncio | 并发执行求解器 |
| 报告生成 | ReportLab | PDF 导出 |

---

## 文件结构

```
frontend/
├── src/
│   ├── views/
│   │   └── SolverComparison.vue       # 对比页面
│   ├── components/
│   │   ├── SolverSelector.vue         # 求解器选择器
│   │   ├── ComparisonResults.vue      # 结果展示
│   │   └── ComparisonCharts.vue       # 图表可视化
│   └── api/
│       └── solverComparison.ts        # API 调用

backend/
├── app/
│   ├── api/
│   │   └── solver_comparison.py       # API 路由
│   ├── services/
│   │   └── solver_comparison.py       # 对比服务
│   └── models/
│       └── solver_comparison.py       # 数据模型
```

---

## 依赖关系

| 依赖 | 说明 |
|------|------|
| 现有智能调度 API | 复用求解器调用逻辑 |
| 现有可视化组件 | 参考 MultiObjectivePanel |
| ECharts | 图表渲染 |
| ReportLab | PDF 生成 |

---

## 测试策略

### 单元测试

- 求解器结果收集测试
- 对比摘要生成测试
- 性能指标归一化测试

### 集成测试

- 完整对比流程测试
- 并发控制测试
- 超时处理测试

### E2E 测试

- 用户选择求解器 → 启动对比 → 查看结果
- 导出报告功能测试
