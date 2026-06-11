# 活跃上下文

> **最后更新**: 2026-06-11  
> **状态**: Phase 2 完成 — 5 引擎 + 3 层记忆 + 6 维守卫 + Phase 3 主题引擎就绪

## 当前焦点

**Phase 2 交付完毕**：叙事引擎、文辞引擎、情节记忆、永久记忆、守卫扩展 6 维、统一记忆管理器、全链路集成测试通过。**Phase 3 主题引擎已启动**。

## 阻塞项

无

## 已完成项

### Phase 1（实践者）
1. ~~目录骨架搭建~~ ✅
2. ~~语料切片（20 片）~~ ✅
3. ~~角色引擎 + 世界引擎~~ ✅
4. ~~编排器 + 一致性守卫~~ ✅
5. ~~工作记忆~~ ✅
6. ~~React 前端 + Flask API~~ ✅
7. ~~M6: LLM 集成 + 语料自扩充回路~~ ✅ (2026-06-09)
8. ~~Items 1-4: Refiner / 实体提取 / 多分析对比 / 历史持久化~~ ✅

### Phase 2（协作者）
9. ~~叙事引擎（伏笔 + 因果链 + 情节推演）~~ ✅ (2026-06-10)
10. ~~文辞引擎（风格指标 + 语域一致 + 角色用语）~~ ✅ (2026-06-11)
11. ~~情节记忆（SQLite + 热缓存 + 因果图谱 + 伏笔表）~~ ✅ (2026-06-11)
12. ~~永久记忆（作者指纹 + 原型库 + 规则模式 + 主动遗忘）~~ ✅ (2026-06-11)
13. ~~统一记忆管理器（三层协调 + 章节下沉 + 跨书积累）~~ ✅ (2026-06-11)
14. ~~守卫 3→6 维（伏笔/因果/叙事一致 实际检查逻辑）~~ ✅ (2026-06-11)
15. ~~目录精简（26→12 条目）~~ ✅ (2026-06-11)
16. ~~GitHub 社区（README 重写 + Issue 模板）~~ ✅ (2026-06-11)
17. ~~Phase 2 全链路集成测试（8/8）~~ ✅ (2026-06-11)

### Phase 3（协作者）
18. ~~主题引擎（主题提取 + 演变追踪 + 一致性告警）~~ ✅ (2026-06-11)

## 待办队列

### 实践者侧
- [ ] 守卫 Phase 2 维度接入 API 端点
- [ ] `api_server.py` 新增 narrative / prose / theme 端点
- [ ] 前端接入新引擎分析结果
- [ ] 前端 UX 打磨（loading 状态、错误提示）

### 协作者侧
- [ ] Phase 3 经济引擎
- [ ] Phase 3 读者预期引擎
- [ ] Phase 3 构思引擎
- [ ] 守卫 Phase 3 维度（temporal / power / relationship / style）

## 最后操作

- **2026-06-11**: Phase 3 主题引擎就绪，5 引擎全链路集成测试通过
- **2026-06-11**: 守卫 6 维实际检查逻辑实现
- **2026-06-11**: 统一 MemoryManager 门面完成
- **2026-06-11**: 目录精简 26→12，GitHub 社区文档完善
- **2026-06-11**: Phase 2 文辞引擎 + 三层记忆完成
- **2026-06-10**: Phase 2 叙事引擎完成
- **2026-06-09**: M6 LLM 集成完成

## 会话历史

- **2026-06-02**: 文档闭环（27 文件冻结）
- **2026-06-03**: NGP 搭建完成 + src/ 目录骨架
- **2026-06-08**: M2-M5 完成（语料、引擎、编排、前端）
- **2026-06-09**: M6 LLM 集成完成
- **2026-06-10**: Phase 2 叙事引擎 + 目录精简
- **2026-06-11**: Phase 2 全部完成 + Phase 3 主题引擎启动

## 活跃模块

| 模块 | 状态 | 文件 |
|------|------|------|
| LLM 集成层 | ✅ | `src/llm/` |
| **角色引擎** | ✅ Phase 1 | `src/engines/character.py` |
| **世界引擎** | ✅ Phase 1 | `src/engines/world.py` |
| **叙事引擎** | ✅ Phase 2 | `src/engines/narrative.py` |
| **文辞引擎** | ✅ Phase 2 | `src/engines/prose.py` |
| **主题引擎** | ✅ Phase 3 | `src/engines/theme.py` |
| 语料锚定层 | ✅ | `src/corpus_anchor/` |
| 语料自扩充器 | ✅ | `src/corpus_anchor/enricher.py` |
| 一致性守卫 | ✅ 6 维 | `src/consistency_guardian/guardian.py` |
| 编排器 | ✅ 5 引擎路由 | `src/orchestrator/router.py` |
| 工作记忆 | ✅ Phase 1 | `src/memory/working_memory.py` |
| 情节记忆 | ✅ Phase 2 | `src/memory/episodic_memory.py` |
| 永久记忆 | ✅ Phase 2 | `src/memory/permanent_memory.py` |
| 统一记忆管理 | ✅ Phase 2 | `src/memory/manager.py` |
| API 服务器 | ✅ | `src/api_server.py` |
| 前端 | ✅ | `src/frontend/` |

## 命名冻结

| 中文名 | 英文名 | 状态 |
|--------|--------|------|
| 角色引擎 | Character Engine | ✅ Phase 1 |
| 世界引擎 | World Engine | ✅ Phase 1 |
| 语料锚定层 | Corpus Anchor | ✅ Phase 1 |
| 语料自扩充器 | Enricher | ✅ Phase 1 M6 |
| 级联修正器 | Cascade Fixer | ✅ Phase 1 |
| 编排器 | Orchestrator | ✅ Phase 1 |
| 叙事引擎 | Narrative Engine | ✅ Phase 2 |
| 文辞引擎 | Prose Engine | ✅ Phase 2 |
| 主题引擎 | Theme Engine | ✅ Phase 3 |
| 情节记忆 | Episodic Memory | ✅ Phase 2 |
| 永久记忆 | Permanent Memory | ✅ Phase 2 |
| 经济引擎 | Economy Engine | Phase 3+ |
| 读者预期引擎 | Reader Expectation Engine | Phase 3+ |
| 构思引擎 | Conception Engine | Phase 3+ |

## LLM 配置

| 项目 | 值 |
|------|-----|
| Provider | 小米 MiMo TokenPlan |
| Model | mimo-v2.5-pro |
| API Endpoint | https://token-plan-cn.xiaomimimo.com/v1 |
| 配置文件 | `config/llm.json`（gitignored） |
| 月度预算 | $20（三层熔断：50%/80%/95%） |

## 冻结决策

- ADR-001: PAD 情感模型
- ADR-003: 禁用自动修正
- ADR-007: Phase 1 范围裁剪
- ADR-008: 人类决策优先
- ADR-009: Tier 0-4 分级定价
- ADR-011: Phase 1 仅激活 2 引擎（已扩展至 5 引擎）
- ADR-012: 本地 7B → MiMo 云 API（已修订）
- ADR-015: MiMo API 替代本地模型 + 成本追踪

## Phase 2 排除项（已部分解除）

- ❌ 叙事引擎 → ✅ 已实现
- ❌ 文辞引擎 → ✅ 已实现
- ❌ 永久记忆 → ✅ 已实现
- ❌ 情节记忆 → ✅ 已实现
- ❌ 守卫扩展 → ✅ 已实现 6 维
- ❌ 主题引擎 → ✅ Phase 3 已启动
- ❌ 经济/读者预期/构思引擎 → 仍排除
- ❌ 级联修正器的因果推理
- ❌ 意图标记系统
- ❌ 章节级快照
- ❌ 复杂 Dashboard

## 成本约束

- **实际使用**: MiMo TokenPlan
- **月度上限**: $20（硬性熔断）
- **禁止改动**: `04-COST-BUDGET.md`

## LLM 任务类型（全量）

| task_type | Phase | 状态 |
|-----------|-------|------|
| `pad_compute` | Phase 1 | ✅ 实践者 |
| `action_infer` | Phase 1 | ✅ 实践者 |
| `rule_check` | Phase 1 | ✅ 实践者 |
| `spatial_check` | Phase 1 | ✅ 实践者 |
| `rerank` | Phase 1 | ✅ 实践者 |
| `entity_extract` | Phase 1 | ✅ 实践者 |
| `scene_analysis` | Phase 1 | ✅ 实践者 |
| `foreshadow_detect` | Phase 2 | ✅ 协作者 |
| `causal_extract` | Phase 2 | ✅ 协作者 |
| `resolution_check` | Phase 2 | ✅ 协作者 |
| `event_predict` | Phase 2 | ✅ 协作者 |
| `style_check` | Phase 2 | ✅ 协作者 |
| `register_check` | Phase 2 | ✅ 协作者 |
| `theme_extract` | Phase 3 | ✅ 协作者 |
