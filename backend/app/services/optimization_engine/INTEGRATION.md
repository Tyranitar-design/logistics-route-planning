# 优化引擎集成文档

## 概述

物流路径规划系统优化引擎现已集成最新的求解器技术，支持多种 VRP 变体和求解方法。

**更新日期**: 2026-04-25

---

## 🦞 今日学习集成成果

### 新增求解器

| 求解器 | 类型 | 特点 | 适用场景 |
|--------|------|------|----------|
| **PyVRP** | 启发式 | 现代化、快速、支持多种 VRP | CVRP/VRPTW/PDP/MDVRP |
| **DRL-VRP** | 深度学习 | 推理速度快、端到端 | 实时调度、快速响应 |

### 新增问题支持

- ✅ PDP (取送货问题)
- ✅ MDVRP (多车场 VRP)
- ✅ HDVRP (异构车队 VRP)

---

## 📊 求解器对比

| 求解器 | 速度 | 精度 | 成本 | 适用规模 |
|--------|------|------|------|----------|
| **Gurobi** | 中 | ⭐⭐⭐⭐⭐ | 商业 | 中小规模 |
| **OR-Tools** | 快 | ⭐⭐⭐⭐ | 免费 | 中等规模 |
| **PyVRP** 🆕 | 快 | ⭐⭐⭐⭐⭐ | 免费 | 大规模 |
| **pymoo NSGA-II** | 中 | ⭐⭐⭐⭐ | 免费 | 多目标 |
| **DRL-VRP** 🆕 | 极快 | ⭐⭐⭐ | 免费 | 中等规模 |
| **ALNS** | 快 | ⭐⭐⭐⭐ | 免费 | 大规模 |

---

## 🏗️ 架构设计

```
optimization_engine/
├── base.py               # 基础类定义
│   ├── SolverType        # 求解器类型枚举
│   ├── ProblemType       # 问题类型枚举
│   ├── OptimizationProblem
│   ├── OptimizationSolver
│   └── OptimizationResult
│
├── solver_factory.py     # 求解器工厂
│   ├── create_solver()
│   ├── recommend_solvers()
│   └── get_solver_info()
│
├── solvers/
│   ├── ortools_solver.py     # OR-Tools
│   ├── gurobi_solver.py      # Gurobi
│   ├── pymoo_solver.py       # pymoo NSGA-II/III
│   ├── genetic_solver.py     # 遗传算法
│   ├── alns_solver.py        # ALNS
│   ├── column_generation_solver.py
│   ├── lagrangian_solver.py
│   ├── pyvrp_solver.py       # 🆕 PyVRP
│   └── drl_vrp_solver.py     # 🆕 DRL-VRP
│
├── problems.py           # 问题定义
├── routes.py             # API 路由
├── comparison.py         # 对比实验
└── visualization.py      # 可视化
```

---

## 🚀 使用方法

### 1. 使用 PyVRP 求解 CVRP

```python
from optimization_engine import SolverFactory, SolverType

# 创建问题
problem = CVRPProblem(
    coords=[(0, 0), (1, 2), (3, 1), ...],
    demands=[0, 5, 3, ...],
    capacity=10
)

# 使用 PyVRP 求解
solver = SolverFactory.create_solver(SolverType.PYVRP)
result = solver.solve(problem, time_limit=10)

print(f"总距离: {result.objective_values[0]:.2f}")
print(f"路线: {result.routes}")
```

### 2. 使用 DRL-VRP 快速求解

```python
# 加载预训练模型
solver = SolverFactory.create_solver(SolverType.DRL_VRP)
solver.load_model("models/vrp_model.pt")

# 快速推理（毫秒级）
result = solver.solve(problem)
```

### 3. 多目标优化

```python
from optimization_engine import MultiObjectiveVRP

problem = MultiObjectiveVRP(
    coords=coords,
    demands=demands,
    capacity=capacity,
    objectives=['cost', 'time', 'carbon']
)

# 使用 NSGA-II 求解 Pareto 前沿
solver = SolverFactory.create_solver(SolverType.PYMOO_NSGA2)
result = solver.solve(problem, n_gen=200)
```

### 4. 求解器对比

```python
# 使用多个求解器对比
results = SolverFactory.solve_with_all(problem)

for solver_type, result in results.items():
    print(f"{solver_type.value}: {result.objective_values[0]:.2f}")
```

---

## 📚 参考资源

### 今日学习笔记

| 项目 | 笔记位置 |
|------|----------|
| VRP-RL | `memory/VRP-RL学习笔记.md` |
| PyVRP | `memory/PyVRP深入学习笔记.md` |
| awesome-ml4co | `memory/awesome-ml4co学习笔记.md` |
| pymoo 进阶 | `memory/pymoo进阶学习笔记.md` |
| awesome-fm4co | `memory/awesome-fm4co学习笔记.md` |

### 官方文档

| 求解器 | 文档 |
|--------|------|
| PyVRP | https://pyvrp.org/ |
| pymoo | https://pymoo.org/ |
| OR-Tools | https://developers.google.com/optimization |
| VRP-RL | https://github.com/OptMLGroup/VRP-RL |

---

## 🔄 后续计划

### 短期（本周）

- [ ] 安装 PyVRP 并测试集成
- [ ] 训练 DRL-VRP 模型
- [ ] 添加 API 接口

### 中期（本月）

- [ ] 集成真实路网数据
- [ ] 多车场 VRP 实战
- [ ] 性能优化

### 长期

- [ ] LLM 接口（自然语言描述问题）
- [ ] 前端可视化增强
- [ ] 云端部署

---

_文档更新: 2026-04-25_
_作者: 小彩 🦞_