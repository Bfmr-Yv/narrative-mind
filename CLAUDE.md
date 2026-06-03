# CLAUDE.md - 项目操作指南

> **项目**: Narrative Mind v3.1  
> **Phase**: 1 (Engineering Preparation)  
> **最后更新**: 2026-06-03

## 项目身份

Narrative Mind 是一个 AI 辅助小说创作系统，基于语料锚定和多引擎协作架构。当前处于 Phase 1 工程准备阶段，NGP 插件框架已就绪。

## 五大硬边界

### 1. 语料边界

- Phase 1 语料规模：20 片（红楼 10 + 自有 10）
- 切片标准：500 字场景级（ADR-013）
- 语料库位置：`corpus/`

### 2. 成本边界

- Tier 1 = $0（本地 Qwen2.5-7B）
- 月度上限 $20（硬性熔断）
- 禁止改动 `04-COST-BUDGET.md`

### 3. 版本边界

- 文档版本以 `docs/` 目录为准
- 代码版本以 `src/` 目录为准
- 变更必须记录在 `03-DECISIONS.md`

### 4. 类型边界

- Phase 1 仅支持通用 Profile
- 不支持修仙/奇幻等类型专用 Profile
- GenreProfile 统计规则待定（Phase 2+）

### 5. 人类优先

- AI 只生成建议和报告
- 所有修改操作需人类确认
- 规则冲突时返回 `conflict` 状态，由人类决定

## 命名冻结表

| 中文名 | 英文名 | 状态 |
|--------|--------|------|
| 角色引擎 | Character Engine | ✅ Phase 1 |
| 世界引擎 | World Engine | ✅ Phase 1 |
| 语料锚定层 | Corpus Anchor | ✅ Phase 1 |
| 级联修正器 | Cascade Fixer | ✅ Phase 1 |
| 编排器 | Orchestrator | ✅ Phase 1 |
| 叙事引擎 | Narrative Engine | Phase 2+ |
| 文辞引擎 | Prose Engine | Phase 2+ |
| 主题引擎 | Theme Engine | Phase 3+ |
| 经济引擎 | Economy Engine | Phase 3+ |
| 读者预期引擎 | Reader Expectation Engine | Phase 3+ |
| 构思引擎 | Conception Engine | Phase 3+ |

**废弃名称**（禁止使用）：
- ~~Style Engine~~ → **Prose Engine**
- ~~Impact Radar~~ → **Cascade Fixer**

## L1-L4 协议

### L1: 记忆层（写入前）

- 检查连续重复行（`uniq -d`）
- 日期格式为 YYYY-MM-DD
- 成本数字与 `04-COST-BUDGET.md` 一致

### L2: 扩展层（模块引用）

- 命名与 `02-CONTRACTS.md` 对齐
- 无废弃名称
- 引用的引擎在当前 Phase 激活

### L3: 集成层（跨模块）

- Phase 标记正确
- 一致性守卫维度匹配
- 成本数字自洽

### L4: 编程层（代码实现）

- 仅使用 Python 标准库
- 无外部依赖引入
- 代码风格与现有模块一致

## NGP Skills 引用

- 编排器：`prompts/ngp-skills/orchestrator.md`
- 角色引擎：`prompts/ngp-skills/character-engine.md`
- 世界引擎：`prompts/ngp-skills/world-engine.md`

## 活跃上下文

详见 `docs/00-ACTIVE-CONTEXT.md`

## 文档真相源

| 文档 | 用途 |
|------|------|
| `00-PROJECT-BRIEF.md` | 项目概述 |
| `01-ARCHITECTURE.md` | 架构设计 |
| `02-CONTRACTS.md` | 接口契约 |
| `03-DECISIONS.md` | 架构决策 |
| `04-COST-BUDGET.md` | 成本预算 |
| `05-MEMORY-SYSTEM.md` | 记忆系统 |
| `06-CONSISTENCY-GUARDIAN.md` | 一致性守卫 |
| `07-PROJECT-STRUCTURE.md` | 项目结构 |
| `08-MVP-ROADMAP.md` | MVP 路线图 |
| `09-RESUME-POSITIONING.md` | 简历定位 |
| `10-AGENT-CONSTRAINTS.md` | Agent 约束 |

## 目录结构

```
xmgl_xs/
├── CLAUDE.md            # 项目操作指南（本文件）
├── docs/                # 设计文档（真相源）
├── src/                 # 源代码
├── corpus/              # 语料数据
├── prompts/             # Prompt 模板
│   └── ngp-skills/      # NGP Skills
├── config/              # 配置文件
└── tests/               # 测试
```

## 开发流程

1. 修改前先读取相关文档
2. 遵循命名冻结和 Phase 边界
3. 写入前执行 L1-L4 检查
4. 成本数字与 `04-COST-BUDGET.md` 交叉核对

## 自检清单

- [ ] `uniq -d` 无输出（连续重复行检测）
- [ ] 命名与 `02-CONTRACTS.md` 对齐
- [ ] Phase 标记正确
- [ ] 成本数字自洽
- [ ] 无废弃名称使用
- [ ] 引用的引擎在当前 Phase 激活
