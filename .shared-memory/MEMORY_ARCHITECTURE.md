# 🧠 Claude Code 持久化记忆系统

## 架构设计

```
CLAUDE.md（启动自动加载）
  ├── 协作规范（静态）
  └── 记忆索引（动态更新）
        ↓ 指向
  .shared-memory/
  ├── CONTEXT.md         ← 项目上下文（长期记忆）
  ├── PROGRESS.md        ← 项目进度（长期记忆）
  ├── TASKS.md           ← 任务看板（工作记忆）
  ├── DECISIONS.md       ← 技术决策（长期记忆）
  ├── MEMORIES.md        ← Claude Code 专属记忆（长期记忆）
  ├── daily/
  │   ├── YYYY-MM-DD.md  ← 每日日志
  │   └── YYYY-MM-DD-learning.md ← 学习笔记
  └── sync/
      ├── pending.md     ← 待同步给小彩的信息
      └── received.md    ← 从小彩收到的信息
```

## 记忆类型

| 类型 | 文件 | 生命周期 | 更新频率 |
|------|------|---------|---------|
| **静态记忆** | CLAUDE.md | 永久 | 很少 |
| **长期记忆** | MEMORIES.md, DECISIONS.md | 永久 | 有变化时 |
| **工作记忆** | TASKS.md, PROGRESS.md | 项目周期 | 每天 |
| **短期记忆** | daily/*.md | 30天 | 每天 |
| **同步记忆** | sync/*.md | 即时 | 每次交互 |

## 记忆操作指令

在 Claude Code 中使用以下指令管理记忆：

### 读取记忆
```
# 开始工作时
请先读取以下文件了解当前状态：
1. .shared-memory/TASKS.md
2. .shared-memory/PROGRESS.md
3. .shared-memory/MEMORIES.md
4. .shared-memory/daily/今天的日期.md
```

### 写入记忆
```
# 完成任务后
请更新以下文件：
1. .shared-memory/TASKS.md - 更新任务状态
2. .shared-memory/PROGRESS.md - 记录成果
3. .shared-memory/MEMORIES.md - 记录学到的经验教训
4. .shared-memory/daily/今天的日期.md - 记录今日工作
```

### 同步记忆
```
# 需要小彩配合时
请将需要小彩处理的事项写入 .shared-memory/sync/pending.md
小彩会定期读取并处理
```

## 记忆衰减机制

- daily/ 日志保留 30 天
- 超过 30 天的日志自动归档到 monthly/ 目录
- DECISIONS.md 只保留最近 50 条决策
- MEMORIES.md 定期去重合并

## 小彩的同步职责

小彩在每次会话开始时：
1. 读取 `.shared-memory/sync/pending.md`（Claude Code 留的信息）
2. 处理后移动到 `.shared-memory/sync/received.md`
3. 将重要信息同步到自己的 `MEMORY.md`
