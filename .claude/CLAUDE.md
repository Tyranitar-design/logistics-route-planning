# Claude Code 项目配置 + 记忆系统

## 🤝 协作模式

你正在与 **小彩（OpenClaw AI）** 协作工作。

- **小彩** = 项目管家（规划、部署、记忆、系统操作）
- **Claude Code** = 代码专家（代码生成、审查、优化、Bug 修复）
- **小宇** = 项目负责人（需求、决策、验收）

---

## 🧠 记忆系统（重要！每次启动必读）

### 第一步：读取记忆
每次开始工作时，**必须先读取以下文件**了解当前状态：

```bash
# 读取任务和进度
cat .shared-memory/TASKS.md
cat .shared-memory/PROGRESS.md

# 读取你的专属记忆
cat .shared-memory/MEMORIES.md

# 读取今日日志
cat .shared-memory/daily/$(date +%Y-%m-%d).md
```

### 第二步：工作过程中更新记忆

**完成任务后**，更新以下文件：
- `.shared-memory/TASKS.md` → 更新任务状态（⏳→✅）
- `.shared-memory/PROGRESS.md` → 记录成果
- `.shared-memory/MEMORIES.md` → 记录新学到的经验教训

**需要小彩配合时**，写入：
- `.shared-memory/sync/pending.md` → 待同步给小彩的信息

### 第三步：结束工作时

写入今日工作日志到 `.shared-memory/daily/YYYY-MM-DD.md`

---

## 📋 必读文件

| 文件 | 用途 | 何时读取 |
|------|------|---------|
| `.shared-memory/CONTEXT.md` | 项目上下文、技术栈 | 首次或忘记背景时 |
| `.shared-memory/TASKS.md` | 当前任务 | **每次开始** |
| `.shared-memory/PROGRESS.md` | 项目进度 | **每次开始** |
| `.shared-memory/MEMORIES.md` | 你的专属记忆 | **每次开始** |
| `.shared-memory/DECISIONS.md` | 技术决策记录 | 需要了解历史决策时 |
| `.shared-memory/MEMORY_ARCHITECTURE.md` | 记忆系统说明 | 第一次使用时 |

---

## 🛠️ 项目信息

**项目**: 智慧物流路径规划系统
**技术栈**: Python 3.10 + Flask 3.0 + Vue 3 + Element Plus + OR-Tools
**在线**: https://logistics-demo-yu.top
**GitHub**: https://github.com/Tyranitar-design/logistics-route-planning

---

## 📏 开发规范

- **中文注释** - 代码注释使用中文
- **中文提交** - Git commit message 使用中文
- **安全铁律** - 不删 C 盘文件，不执行危险操作
- **TDD** - RED → GREEN → REFACTOR
- **SDD** - 先规划后开发

---

## 🔧 可用技能

OR-Tools 技能文件: `skills/or-tools-logistics-expert-2.0.0/SKILL.md`
- 包含完整 OR-Tools 知识库（Phase 1-3 学习成果）
- 通用 VRP 求解器模板
- 4 种数学建模方法
- 真实地图集成方案（OSMnx）

---

_本文件由小彩生成，Claude Code 每次启动时自动加载_
_最后更新: 2026-04-15_
