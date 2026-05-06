# 求解器对比功能规格

**变更名称**: add-solver-comparison-feature  
**创建日期**: 2026-04-22

---

## Purpose

为物流路径规划系统提供多求解器性能对比功能，帮助用户选择最适合的求解器。

---

## Requirements

### Requirement: 求解器选择

系统 SHALL 允许用户选择多个求解器进行对比。

#### Scenario: 选择多个求解器

- GIVEN 用户进入对比页面
- WHEN 用户选择 2 个或更多求解器
- THEN 系统显示已选择的求解器列表
- AND 用户可以移除或添加求解器

#### Scenario: 求解器数量限制

- GIVEN 用户已选择 3 个求解器
- WHEN 用户尝试选择第 4 个求解器
- THEN 系统显示警告消息
- AND 禁止继续添加

---

### Requirement: 问题选择

系统 SHALL 允许用户选择要优化的 VRP 问题。

#### Scenario: 选择现有问题

- GIVEN 系统中有已定义的 VRP 问题
- WHEN 用户从下拉列表选择问题
- THEN 系统加载问题详情
- AND 显示问题规模（节点数、车辆数）

#### Scenario: 自定义问题

- GIVEN 用户需要测试自定义问题
- WHEN 用户上传问题文件
- THEN 系统验证文件格式
- AND 显示解析结果

---

### Requirement: 并发执行

系统 SHALL 并发执行多个求解器并收集性能指标。

#### Scenario: 并发执行成功

- GIVEN 用户选择了 3 个求解器和 1 个问题
- WHEN 用户点击"开始对比"
- THEN 系统同时启动 3 个求解器
- AND 实时显示执行进度

#### Scenario: 求解器超时

- GIVEN 用户设置了 60 秒超时
- WHEN 某个求解器超过 60 秒未完成
- THEN 系统终止该求解器
- AND 标记状态为 "timeout"
- AND 继续执行其他求解器

#### Scenario: 求解器错误

- GIVEN 某个求解器执行中发生错误
- WHEN 错误被捕获
- THEN 系统记录错误信息
- AND 标记状态为 "error"
- AND 不影响其他求解器执行

---

### Requirement: 结果展示

系统 SHALL 以表格和图表形式展示对比结果。

#### Scenario: 表格展示

- GIVEN 对比完成
- WHEN 用户查看结果
- THEN 系统显示对比表格
- AND 表格包含求解器名称、求解时间、目标值、状态等列
- AND 表格支持排序

#### Scenario: 雷达图展示

- GIVEN 对比完成
- WHEN 用户切换到雷达图视图
- THEN 系统显示综合性能雷达图
- AND 雷达图维度包括：求解速度、解质量、稳定性、内存效率、收敛速度

#### Scenario: 柱状图展示

- GIVEN 对比完成
- WHEN 用户切换到柱状图视图
- THEN 系统显示单项指标柱状图
- AND 支持切换不同指标（求解时间、目标值等）

---

### Requirement: 报告导出

系统 SHALL 支持导出对比报告为 PDF 格式。

#### Scenario: 导出 PDF

- GIVEN 对比完成
- WHEN 用户点击"导出报告"
- THEN 系统生成 PDF 文件
- AND PDF 包含对比表格、图表和分析总结
- AND 提供下载链接

---

### Requirement: 任务控制

系统 SHALL 支持对比任务的启动、取消和重试。

#### Scenario: 取消对比

- GIVEN 对比正在执行
- WHEN 用户点击"取消"
- THEN 系统终止所有运行中的求解器
- AND 清理临时资源
- AND 显示已取消状态

#### Scenario: 重试对比

- GIVEN 对比已取消或失败
- WHEN 用户点击"重试"
- THEN 系统重新启动对比
- AND 使用相同的求解器和问题配置

---

## Non-functional Requirements

### 性能要求

- 对比启动响应时间 SHALL < 1 秒
- 单个求解器最大执行时间 SHOULD < 300 秒
- 最大并发求解器数量 SHALL = 3

### 可用性要求

- 界面 SHALL 支持中英文
- 错误信息 SHALL 清晰易懂
- 操作 SHALL 支持键盘快捷键

### 兼容性要求

- 系统 SHALL 支持主流浏览器（Chrome、Firefox、Edge）
- API SHALL 遵循 RESTful 规范
