# 算法引擎升级规格

**变更名称**: algorithm-engine-upgrade  
**创建日期**: 2026-05-05

---

## Purpose

为物流路径规划系统建立工程级优化能力：统一真实距离底座、提升多目标优化精度、增加求解器推荐与质量评估能力，并增强前端决策可视化。

---

## Requirements

### Requirement: 统一精确距离矩阵

系统 SHALL 为主力求解器提供统一的精确距离矩阵，并优先使用高德缓存的真实道路距离。

#### Scenario: 命中真实道路距离缓存
- GIVEN 系统已有节点间距离缓存
- WHEN 构建 VRP 问题距离矩阵
- THEN 系统优先使用缓存中的真实道路距离
- AND 返回精度统计信息

#### Scenario: 缓存未命中时调用高德 API
- GIVEN 距离缓存未命中
- WHEN 系统构建距离矩阵
- THEN 系统批量调用高德距离 API
- AND 将结果写入缓存

#### Scenario: 外部距离服务不可用
- GIVEN 高德 API 不可用
- WHEN 系统仍需构建距离矩阵
- THEN 系统使用 Haversine × 修正系数兜底
- AND 标记该部分为近似距离

---

### Requirement: 主力求解器共享统一问题数据

系统 SHALL 让 OR-Tools、Gurobi、PyVRP、pymoo、ALNS、遗传算法等主力求解器使用统一问题数据结构。

#### Scenario: 同一问题交给不同求解器
- GIVEN 用户提交同一组订单和车辆数据
- WHEN 系统分别调用多个求解器
- THEN 所有求解器使用同一份构建后的问题数据
- AND 使用同一份距离矩阵

---

### Requirement: 多目标优化输出真实 Pareto 前沿

系统 SHALL 提供比简单加权求和和基础排序更高质量的多目标优化结果。

#### Scenario: 运行 NSGA-II 多目标优化
- GIVEN 用户请求多目标优化
- WHEN 系统使用 NSGA-II 求解
- THEN 系统使用适用于 VRP 的交叉和变异算子
- AND 输出非支配解集
- AND 返回 Pareto 前沿信息

#### Scenario: 运行 NSGA-III 多目标优化
- GIVEN 用户请求高维多目标优化
- WHEN 系统使用 NSGA-III 求解
- THEN 系统输出多样化的非支配解
- AND 返回前沿质量指标

---

### Requirement: 求解结果质量评估

系统 SHALL 为每次求解输出统一的质量评估信息。

#### Scenario: 评估单目标求解结果
- GIVEN 求解器完成一次优化
- WHEN 系统生成结果
- THEN 系统校验解的可行性
- AND 返回目标值、时间、gap、约束违规等信息

#### Scenario: 评估多目标求解结果
- GIVEN 系统生成一组 Pareto 解
- WHEN 系统评估结果质量
- THEN 系统返回 Pareto 数量、非支配层信息、质量指标
- AND 返回距离精度占比

---

### Requirement: 求解器推荐

系统 SHALL 能基于问题类型、规模和目标推荐合适求解器。

#### Scenario: 小规模精确求解推荐
- GIVEN 问题规模较小且用户需要高精度结果
- WHEN 用户选择自动求解器
- THEN 系统推荐 Gurobi 或等效精确求解器
- AND 给出推荐原因

#### Scenario: 中大规模快速求解推荐
- GIVEN 问题规模较大且用户需要快速返回
- WHEN 用户选择自动求解器
- THEN 系统推荐 OR-Tools、ALNS 或其他启发式求解器
- AND 给出推荐原因

#### Scenario: 多目标求解推荐
- GIVEN 用户目标为多目标折中分析
- WHEN 用户选择自动求解器
- THEN 系统推荐 NSGA-II/III 或等价多目标方法
- AND 给出推荐原因

---

### Requirement: 前端展示 Pareto 与质量信息

系统 SHALL 在前端展示可帮助决策的多目标信息，而不仅是简单数值列表。

#### Scenario: 展示 Pareto 散点图
- GIVEN 系统返回多目标结果
- WHEN 用户打开多目标页面
- THEN 系统展示 Pareto 散点图
- AND 用户可以查看各解详情

#### Scenario: 展示平行坐标图
- GIVEN 系统返回多个目标维度
- WHEN 用户切换视图
- THEN 系统展示平行坐标图
- AND 用户可以对比不同方案的取舍

#### Scenario: 展示质量与精度报告
- GIVEN 系统已完成求解
- WHEN 用户查看结果详情
- THEN 系统展示质量报告
- AND 展示真实距离占比与近似距离占比

---

## Non-functional Requirements

### 性能要求
- 系统 SHOULD 优先使用缓存减少重复距离请求
- 单个求解任务默认超时 SHOULD 可配置
- 求解器并发数量 SHALL 受控，避免资源争抢

### 可解释性要求
- 系统 SHALL 说明推荐求解器的原因
- 系统 SHALL 标注距离数据精度来源
- 系统 SHALL 输出质量评估摘要

### 工程一致性要求
- 所有主力求解器 SHALL 使用统一问题构建入口
- 新增算法升级 SHALL 支持测试验证
- 前后端展示 SHALL 与后端评估字段保持一致
