# 项目代码结构

> 本文档定义 Narrative Mind v3.1 的完整文件/目录布局。
> Phase 1 仅实现标有 `[Phase 1]` 的目录和文件。

---

## 项目根目录

```
xmgl_xs/                          ← 项目根
├── docs/                         ← 设计文档（真相源）
│   ├── 00-PROJECT-BRIEF.md
│   ├── 01-ARCHITECTURE.md
│   ├── 02-CONTRACTS.md
│   ├── 03-DECISIONS.md
│   ├── 04-COST-BUDGET.md
│   ├── 05-MEMORY-SYSTEM.md
│   ├── 06-CONSISTENCY-GUARDIAN.md
│   ├── 07-PROJECT-STRUCTURE.md
│   ├── 08-MVP-ROADMAP.md
│   ├── 09-RESUME-POSITIONING.md
│   ├── engines/                  ← 引擎设计卡片
│   │   ├── character-engine.md
│   │   ├── world-engine.md
│   │   ├── corpus-anchor.md
│   │   ├── cascade-fixer.md
│   │   ├── orchestrator.md
│   │   ├── narrative-engine.md
│   │   ├── prose-engine.md
│   │   ├── theme-engine.md
│   │   ├── economy-engine.md
│   │   ├── reader-expectation-engine.md
│   │   └── conception-engine.md
│   ├── prompts/                  ← Prompt 模板
│   │   ├── README.md
│   │   ├── character-engine-v1.md
│   │   └── world-engine-v1.md
│   └── sessions/                 ← 对话日志
│       ├── 2026-05-29-documentation-setup.md
│       └── 2026-06-02-v3.1-restructure.md
│
├── src/                          ← 源代码 [Phase 1]
│   ├── engines/                  ← 引擎实现
│   │   ├── __init__.py
│   │   ├── base.py               ← BaseEngine 抽象类
│   │   ├── character_engine/     ← [Phase 1]
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── pad.py            ← PAD 情感模型
│   │   │   ├── behavior.py       ← 行为模式匹配
│   │   │   └── prompts.py        ← Prompt 模板加载
│   │   ├── world_engine/         ← [Phase 1]
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── rules.py          ← 规则引擎
│   │   │   └── settings_loader.py ← 设定库加载
│   │   ├── narrative_engine/     ← [Phase 2+]
│   │   ├── prose_engine/         ← [Phase 2+]
│   │   ├── theme_engine/         ← [Phase 3+]
│   │   ├── economy_engine/       ← [Phase 3+]
│   │   ├── reader_expectation_engine/ ← [Phase 3+]
│   │   └── conception_engine/    ← [Phase 3+]
│   │
│   ├── orchestrator/             ← 编排器 [Phase 1]
│   │   ├── __init__.py
│   │   ├── router.py             ← 事件路由
│   │   ├── scheduler.py          ← 引擎调度
│   │   └── fallback.py           ← 降级策略
│   │
│   ├── memory/                   ← 记忆系统 [Phase 1 简化版]
│   │   ├── __init__.py
│   │   ├── working_memory.py     ← 工作记忆
│   │   ├── episodic_memory.py    ← 情节记忆
│   │   └── models.py             ← 数据模型
│   │
│   ├── consistency_guardian/     ← 一致性守卫 [Phase 1 简化版]
│   │   ├── __init__.py
│   │   ├── guardian.py           ← 守卫主逻辑
│   │   └── dimensions.py         ← 检查维度定义
│   │
│   ├── corpus_anchor/            ← 语料锚定层 [Phase 1]
│   │   ├── __init__.py
│   │   ├── retriever.py          ← 向量检索
│   │   ├── embedder.py           ← 文本向量化
│   │   └── slice_manager.py      ← 切片管理
│   │
│   ├── infrastructure/           ← 基础设施 [Phase 2+]
│   │   ├── genre_profile/
│   │   ├── author_fingerprint/
│   │   ├── version_control/
│   │   └── feedback_learning/
│   │
│   ├── frontend/                 ← 前端 [Phase 1]
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── api/                  ← 与 Python 后端的 API 桥接
│   │
│   └── shared/                   ← 共享工具
│       ├── __init__.py
│       ├── config.py             ← 配置加载
│       ├── cost_tracker.py       ← 成本追踪
│       └── logger.py             ← 日志
│
├── corpus/                       ← 语料数据
│   ├── public-domain/            ← 公共域语料（JSON 切片）
│   │   └── hong-lou-meng/        ← 红楼梦切片
│   └── user/                     ← 用户自有语料
│
├── prompts/                      ← Prompt YAML 注册表
│   ├── registry.yaml
│   └── templates/
│       ├── character_engine.j2
│       └── world_engine.j2
│
├── config/                       ← 配置文件
│   ├── genre-profile.json        ← 类型特征
│   ├── cost-budget.json          ← 成本预算
│   └── settings.yaml             ← 全局设置
│
└── tests/                        ← 测试
    ├── unit/
    │   ├── test_character_engine/
    │   ├── test_world_engine/
    │   ├── test_corpus_anchor/
    │   └── test_guardian/
    ├── integration/
    │   └── test_orchestrator_flow.py
    └── fixtures/                  ← 测试数据
```

---

## Python 包命名约定

- 引擎包：snake_case（`character_engine`、`world_engine`）
- 类名：PascalCase（`CharacterEngine`、`WorldEngine`）
- 数据类：PascalCase（`CharacterQuery`、`WorldResponse`）
- 私有模块：`_` 前缀（`_internal.py`）

---

## 文档 ↔ 代码映射

| 文档 | 对应代码模块 |
|------|------------|
| `engines/character-engine.md` | `src/engines/character_engine/` |
| `engines/world-engine.md` | `src/engines/world_engine/` |
| `engines/corpus-anchor.md` | `src/corpus_anchor/` |
| `engines/cascade-fixer.md` | `src/engines/cascade_fixer/`（Phase 2+） |
| `engines/orchestrator.md` | `src/orchestrator/` |
| `05-MEMORY-SYSTEM.md` | `src/memory/` |
| `06-CONSISTENCY-GUARDIAN.md` | `src/consistency_guardian/` |
| `04-COST-BUDGET.md` | `src/shared/cost_tracker.py` |

---

## 数据目录布局（用户项目）

用户使用本系统时，在小说项目目录下创建：

```
MyNovel.narrative/
├── manuscript/          ← Markdown 正文（不被系统锁定）
│   ├── vol1/
│   │   ├── ch001.md
│   │   └── ch002.md
│   └── vol2/
├── corpus/              ← 该作品的语料库
│   └── slices/
├── memory/              ← 该作品的记忆数据
│   ├── narrative.db     ← SQLite
│   └── vectors/         ← LanceDB
└── config/
    └── world-settings.yaml
```
