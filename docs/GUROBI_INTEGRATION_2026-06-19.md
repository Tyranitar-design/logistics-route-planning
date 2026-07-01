# Gurobi 高级优化接入说明（2026-06-19）

## 背景

项目第二阶段需要把 Gurobi 纳入高级优化底座，用于小规模精确 VRP、车辆分配、网络设计 MILP、容量约束选址等问题。

本次先完成安全能力探测与接口治理，避免继续用“能 import gurobipy”这种过弱信号判断生产可用性。

## 后端变化

- 新增 `backend/app/services/gurobi_capability_service.py`。
- 新增安全健康接口：
  - `GET /api/optimization/gurobi/health`
  - `GET /api/optimization/gurobi/health?smoke=1`
  - `POST /api/optimization/gurobi/smoke`
- 新增小规模车辆分配接口：
  - `POST /api/optimization/gurobi/vehicle-assignment`
  - `GET /api/optimization/gurobi/vehicle-assignment-demo`
- 新增小规模 CVRP 路径精确求解接口：
  - `POST /api/optimization/gurobi/vrp`
  - `GET /api/optimization/gurobi/vrp-demo`
- 新增小规模网络设计 / 容量受限设施选址接口：
  - `POST /api/optimization/gurobi/network-design`
  - `GET /api/optimization/gurobi/network-design-demo`
- 新增小规模 CVRP 求解器对比接口：
  - `POST /api/optimization/solver-benchmark`
  - `GET /api/optimization/solver-benchmark-demo`
  - `POST /api/optimization/gurobi/compare-small-vrp`
  - `GET /api/optimization/gurobi/compare-small-vrp-demo`
- `/api/optimization/solvers` 中 Gurobi / Gurobi-VRPTW 会附带：
  - `provider_status`
  - `fallback_reason`
  - `authenticity_level`
  - `checks`
- `GurobiSolver.is_available()` 和 `GurobiVRPTWSolver.is_available()` 现在统一走能力探测服务。
- 修正 `GurobiVRPTWSolver` 的 solver type 标识为 `gurobi_vrptw`。

## 车辆分配 MILP Demo

接口：

```http
POST /api/optimization/gurobi/vehicle-assignment
```

示例 payload：

```json
{
  "solver": "auto",
  "max_orders_per_vehicle": 3,
  "orders": [
    {"id": "O-1001", "weight_tons": 2.0, "volume_m3": 7.0, "priority": "urgent", "freight": 1800}
  ],
  "vehicles": [
    {"id": "V-01", "plate_number": "粤A-Demo01", "capacity_weight_tons": 6.0, "capacity_volume_m3": 18.0}
  ]
}
```

求解语义：

- Gurobi 可用时，构建二进制 MILP：
  - 每个订单只能分配给一辆车或进入未分配集合。
  - 车辆重量容量、体积容量、单车最大订单数是硬约束。
  - 目标函数优先分配高优先级 / 高运费价值订单。
- Gurobi 不可用时，自动降级为 `greedy_capacity_fallback`，并返回具体 `fallback_reason`。
- 用户显式选择 `solver=greedy` 时，返回 `greedy_capacity`，不把它伪装成 Gurobi 降级。

响应会包含：

- `summary.assigned_orders`
- `summary.unassigned_orders`
- `assignments`
- `unassigned_orders[].unassigned_reason`
- `diagnostics.hard_constraints`
- `distance_source = not_required_for_assignment`
- `path_source = vehicle_order_assignment_milp`
- `provider_status`
- `fallback_reason`
- `authenticity_level`

## 小规模 CVRP / VRP Demo

接口：

```http
POST /api/optimization/gurobi/vrp
```

示例 payload：

```json
{
  "solver": "auto",
  "n_vehicles": 2,
  "vehicle_capacity": 7,
  "node_labels": ["广州仓", "佛山客户", "东莞客户", "深圳客户", "珠海客户"],
  "demands": [2, 3, 4, 2],
  "distance_matrix": [
    [0, 18, 45, 110, 95],
    [18, 0, 55, 120, 80],
    [45, 55, 0, 70, 115],
    [110, 120, 70, 0, 140],
    [95, 80, 115, 140, 0]
  ],
  "distance_source": "payload_distance_matrix",
  "data_source": "payload_demo"
}
```

求解语义：

- Gurobi 可用时，构建小规模 CVRP MILP。
- 当前精确求解上限为 `MAX_EXACT_CUSTOMERS = 8`，避免把生产 5 万单误送入精确模型。
- 硬约束：
  - 每个客户最多被一辆车服务，或进入未分配集合。
  - 每辆车总需求不超过 `vehicle_capacity`。
  - 车辆从 depot 出发和返回 depot 保持平衡。
  - 使用 MTZ 约束消除客户子回路。
- 目标函数：
  - 最小化路线总距离。
  - 对未分配客户加入大惩罚，避免无声丢单。
- Gurobi 不可用时，自动降级到 `nearest_neighbor_capacity_fallback`。
- 用户显式选择 `solver=greedy` 时，返回 `nearest_neighbor_capacity`，不报告为 Gurobi 降级。

响应会包含：

- `summary.assigned_customers`
- `summary.unassigned_customers`
- `summary.total_distance`
- `routes[].node_sequence`
- `routes[].node_labels`
- `routes[].load`
- `routes[].capacity_utilization`
- `unassigned_customers[].unassigned_reason`
- `distance_source`
- `path_source = solver_node_sequence`
- `provider_status`
- `fallback_reason`
- `solver_quality`

## 小规模求解器 Benchmark

接口：

```http
POST /api/optimization/solver-benchmark
```

兼容别名：

```http
POST /api/optimization/gurobi/compare-small-vrp
```

示例 payload：

```json
{
  "solvers": ["gurobi", "ortools", "alns", "greedy"],
  "time_limit": 5,
  "alns_iterations": 120,
  "n_vehicles": 2,
  "vehicle_capacity": 7,
  "node_labels": ["广州仓", "佛山客户", "东莞客户", "深圳客户", "珠海客户"],
  "demands": [2, 3, 4, 2],
  "distance_matrix": [
    [0, 18, 45, 110, 95],
    [18, 0, 55, 120, 80],
    [45, 55, 0, 70, 115],
    [110, 120, 70, 0, 140],
    [95, 80, 115, 140, 0]
  ],
  "distance_source": "payload_distance_matrix",
  "data_source": "payload_demo"
}
```

对比语义：

- 同一份 bounded CVRP 输入固定不变，再分别跑：
  - `gurobi`: 小规模 CVRP MILP；不可用时返回失败行，不伪装成启发式。
  - `ortools`: 现有 OR-Tools optimization engine。
  - `alns`: 现有 ALNS optimization engine。
  - `greedy`: `nearest_neighbor_capacity` 贪心容量基线。
- 排名只纳入 `success=true` 且硬约束校验通过的结果。
- 对每个结果校验：
  - 每个客户是否只服务一次。
  - 是否缺客户或重复客户。
  - 是否超过车辆数。
  - 是否超过车辆容量。
- 如果只传 `solvers` 或调用 demo 接口，服务会自动使用内置 CVRP demo 数据。

响应会包含：

- `benchmark_type = small_cvrp_solver_comparison`
- `summary.best_solver`
- `summary.feasible_solvers`
- `results[].solver`
- `results[].solver_quality`
- `results[].objective_value`
- `results[].total_distance`
- `results[].solve_time_seconds`
- `results[].feasible`
- `results[].hard_constraint_violations`
- `rankings`
- `data_source`
- `distance_source`
- `path_source = solver_node_sequence+optimization_engine_routes`
- `provider_status`
- `fallback_reason`
- `authenticity_level`

## 网络设计 / CFLP Demo

接口：

```http
POST /api/optimization/gurobi/network-design
```

示例 payload：

```json
{
  "solver": "auto",
  "transport_cost_per_km": 2.4,
  "max_facilities": 2,
  "customers": [
    {"id": "C-GZ", "name": "广州需求", "demand": 120, "lat": 23.1291, "lon": 113.2644}
  ],
  "candidates": [
    {"id": "F-GZ", "name": "广州中心仓", "capacity": 260, "fixed_cost": 46000, "lat": 23.1291, "lon": 113.2644}
  ]
}
```

求解语义：

- Gurobi 可用时，构建容量受限设施选址 MILP。
- 当前 demo 上限：
  - `MAX_NETWORK_CUSTOMERS = 12`
  - `MAX_NETWORK_CANDIDATES = 8`
- 硬约束：
  - 客户需求必须被分配给一个开放设施，或进入未满足集合。
  - 客户只能分配给已开放设施。
  - 开放设施承载需求不能超过容量。
  - 可选 `max_facilities` 控制最多开仓数量。
- 目标函数：
  - 最小化固定开仓成本 + 运输成本。
  - 对未满足需求加入大惩罚，避免无声丢需求。
- Gurobi 不可用时，降级到 `greedy_facility_capacity_fallback`。
- 用户显式选择 `solver=greedy` 时，返回 `greedy_facility_capacity`。

数据库小样本：

```json
{
  "use_database": true,
  "customer_limit": 6,
  "candidate_limit": 4,
  "max_facilities": 2
}
```

该路径从 `shipment_facts` 聚合：

- destination city -> demand customer
- origin city -> candidate facility
- weight_kg -> tons demand / historical capacity proxy
- distance_source = `haversine_corrected`

响应会包含：

- `summary.selected_facilities`
- `summary.demand_coverage_rate`
- `selected_facilities[].used_capacity`
- `selected_facilities[].utilization`
- `assignments[].distance_km`
- `assignments[].transport_cost`
- `unassigned_customers[].unassigned_reason`
- `distance_source`
- `path_source = facility_customer_assignment`
- `provider_status`
- `fallback_reason`
- `solver_quality`

## 环境变量

开发环境示例：`backend/.env.example`

```env
GUROBI_HOME=D:\Gurobi1300
GRB_LICENSE_FILE=D:\Gurobi1300\win64\bin\gurobi.lic
```

生产环境示例：`.env.production.example`

```env
GUROBI_HOME=/opt/gurobi
GRB_LICENSE_FILE=/opt/gurobi/gurobi.lic
```

注意：只配置 license 文件路径，不读取、不打印、不提交 `gurobi.lic` 内容。

## 响应语义

健康检查响应包含：

- `available`: Gurobi 是否可作为 Python 求解器使用。
- `provider_status`: `ok` 或 `degraded`。
- `fallback_solver`: 不可用时建议回退到 `ortools`。
- `fallback_reason`: 例如：
  - `GUROBI_PYTHON_API_UNAVAILABLE`
  - `GUROBI_LICENSE_FILE_MISSING`
  - `GUROBI_SMOKE_SOLVE_FAILED`
- `checks`: 安装目录、CLI、license 文件、Python API、smoke 状态。
- `security`: 明确标记不返回 license 内容或 secret 值。

## 当前边界

- 默认 health 只做轻量检查，不运行模型。
- `?smoke=1` 或 `/smoke` 会运行一个 1 变量微型模型，用于验证 Python API、license 和 runtime 是否真的可求解。
- 如果本机未安装 `gurobipy`，但 `D:\Gurobi1300` 和 license 文件存在，接口会返回明确降级，而不是把 Gurobi 误报为可用。
- 当前已实现车辆分配 MILP demo、小规模 CVRP/VRP 精确求解 demo、网络设计 CFLP MILP demo，以及 OR-Tools/ALNS/Gurobi/greedy 小规模 CVRP benchmark。
- 这些接口仍是阶段二的 bounded demo / benchmark，不应把生产 5 万单直接送入小规模精确模型；生产路径应先切波次，再进入调度/求解器编排。

## 验证

- `python -m py_compile backend/app/services/gurobi_capability_service.py backend/app/services/optimization_engine/solvers/gurobi_solver.py backend/app/routes/optimization.py backend/tests/test_gurobi_capability_service.py`
- `python -m py_compile backend/tests/test_gurobi_capability_service.py backend/tests/test_solver_recommendation_engine.py`
- `python -m pytest backend/tests/test_gurobi_capability_service.py backend/tests/test_solver_recommendation_engine.py -q`
- `python -m pytest backend/tests/test_gurobi_assignment_service.py backend/tests/test_gurobi_capability_service.py backend/tests/test_solver_recommendation_engine.py -q`
  - result: `11 passed`
- `python -m pytest backend/tests/test_gurobi_vrp_service.py backend/tests/test_gurobi_assignment_service.py backend/tests/test_gurobi_capability_service.py backend/tests/test_solver_recommendation_engine.py -q`
  - result: `16 passed`
- `python -m pytest backend/tests/test_gurobi_network_design_service.py backend/tests/test_gurobi_vrp_service.py backend/tests/test_gurobi_assignment_service.py backend/tests/test_gurobi_capability_service.py backend/tests/test_solver_recommendation_engine.py -q`
  - result: `21 passed`
- `python -m py_compile backend/app/services/solver_benchmark_service.py backend/app/services/gurobi_vrp_service.py backend/app/routes/optimization.py backend/tests/test_solver_benchmark_service.py`
- `python -m pytest backend/tests/test_solver_benchmark_service.py -q`
  - result: `3 passed`
- `python -m pytest backend/tests/test_solver_benchmark_service.py backend/tests/test_gurobi_network_design_service.py backend/tests/test_gurobi_vrp_service.py backend/tests/test_gurobi_assignment_service.py backend/tests/test_gurobi_capability_service.py backend/tests/test_solver_recommendation_engine.py -q`
  - result: `24 passed`

本轮受控执行环境拦截了直接 `python -c` 和直接运行 `gurobi_cl.exe --version` 的命令，因此未在会话内做真实本机 smoke。真实环境可通过：

```http
GET /api/optimization/gurobi/health?smoke=1
```

来验证 Gurobi Python API + license 是否可实际求解。
