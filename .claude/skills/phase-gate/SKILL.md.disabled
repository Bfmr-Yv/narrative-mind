---
name: phase-gate
description: Phase 边界检查 — 验证新增功能/引用不超出当前 Phase 范围。当用户提到"Phase"、"新增引擎"、"守卫维度"、"边界"时触发。
---

# Phase 边界门控

## 当前 Phase 状态（2026-06-15）

| 范围 | 状态 |
|------|------|
| **Phase 1** | ✅ 全部完成 |
| **Phase 2** | ✅ 全部完成 |
| **Phase 3** | 🔄 主题引擎完成，其余待开发 |

## 允许的操作

### Phase 3 当前可开发

| 可开发 | 文件位置 |
|--------|---------|
| Economy Engine | `src/engines/economy.py`（新建） |
| Reader Expectation Engine | `src/engines/reader_expectation.py`（新建） |
| Conception Engine | `src/engines/conception.py`（新建） |
| 守卫 temporal/power/relationship/style 维度 | `src/consistency_guardian/guardian.py`（扩展） |
| 级联修正器完整版 | `src/corpus_anchor/cascade_fixer.py`（升级） |

### ❌ 禁止的操作

- 引用尚未实现的引擎（Economy/ReaderExpectation/Conception）
- 使用 Phase 3 守卫维度名（temporal/power/relationship/style）作为已激活维度
- 在 `ROUTE_MAP` 中注册未实现引擎的路由
- 在 `active_dimensions` 默认值中包含 Phase 3 维度

## 新增引擎检查清单

1. [ ] 命名与 CLAUDE.md 冻结表一致
2. [ ] `docs/02-CONTRACTS.md` 添加输入/输出契约
3. [ ] `src/engines/<name>.py` 创建引擎文件
4. [ ] `src/llm/prompts.py` 添加 task_type system prompt（如需 LLM）
5. [ ] `src/llm/config.py` 注册 TIER_CONFIG + ESTIMATED_COST
6. [ ] `docs/SHARED-INTERFACE.md` §3.1 注册 task_type
7. [ ] `src/orchestrator/router.py` ROUTE_MAP 添加路由
8. [ ] `docs/00-ACTIVE-CONTEXT.md` 更新活跃模块表
9. [ ] 编写测试 `scripts/test_<name>_engine.py`
10. [ ] 运行全链路集成测试

## 跨 Phase 引用检测

```bash
# 检查是否引用了未实现的 Phase 3 引擎
git diff --name-only | xargs grep -n "EconomyEngine\|ReaderExpectationEngine\|ConceptionEngine" 2>/dev/null

# 检查是否使用了废弃名称
git diff --name-only | xargs grep -n "Style Engine\|Impact Radar" 2>/dev/null
```
