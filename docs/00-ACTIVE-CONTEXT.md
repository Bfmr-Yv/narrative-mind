# 活跃上下文

> **最后更新**: 2026-06-03  
> **状态**: Phase 1 Engineering Preparation

## 当前焦点

**Phase 1 Engineering Preparation**: NGP 插件框架已就绪

## 阻塞项

无

## 待办队列

1. ~~`src/` 目录骨架搭建~~ ✅ 完成（2026-06-03）
2. 创建 `CODING-STANDARDS.md`
3. ~~运行 NGP 守卫脚本测试（`naming_phase_guard.py` 拦截 Style Engine）~~ ✅ 通过（2026-06-03）

## 最后操作

- **2026-06-03**: 类型注解修正（naming_phase_guard.py + post_edit_validator.py 添加 `from __future__ import annotations` + `-> None`）

## 会话历史

- **2026-06-02**: 文档闭环（27 文件冻结）
- **2026-06-03**: NGP 搭建完成（Step 1-3）
- **2026-06-03**: src/ 目录骨架搭建完成（engines/memory/cli 包 + consistency_guardian/orchestrator 的 __init__.py）

## 活跃模块

| 模块 | 状态 | 文件 |
|------|------|------|
| 角色引擎 | 骨架已创建 | `src/engines/character.py` |
| 世界引擎 | 骨架已创建 | `src/engines/world.py` |
| 语料锚定层 | 待开发 | `src/corpus_anchor/` |
| 一致性守卫 | 已创建 | `src/consistency_guardian/naming_phase_guard.py` |
| 编排器 | 已创建 | `src/orchestrator/post_edit_validator.py` |
| 记忆系统 | 骨架已创建 | `src/memory/working_memory.py` |
| CLI | 骨架已创建 | `src/cli/main.py` |

## NGP Skills

| Skill | 文件 | 状态 |
|-------|------|------|
| 编排器 | `prompts/ngp-skills/orchestrator.md` | ✅ 已创建 |
| 角色引擎 | `prompts/ngp-skills/character-engine.md` | ✅ 已创建 |
| 世界引擎 | `prompts/ngp-skills/world-engine.md` | ✅ 已创建 |

## 冻结决策

- ADR-001: PAD 情感模型
- ADR-003: 禁用自动修正
- ADR-007: Phase 1 范围裁剪
- ADR-008: 人类决策优先
- ADR-009: Tier 0-4 分级定价
- ADR-011: Phase 1 仅激活 2 引擎

## 命名冻结

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

## Phase 1 排除项

- ❌ 叙事/文辞/主题/经济/读者预期/构思引擎
- ❌ 永久记忆
- ❌ 级联修正器的因果推理
- ❌ 意图标记系统
- ❌ 章节级快照
- ❌ 复杂 Dashboard

## 成本约束

- **Tier 1**: $0（本地 Qwen2.5-7B）
- **月度上限**: $20
- **禁止改动**: `04-COST-BUDGET.md`
