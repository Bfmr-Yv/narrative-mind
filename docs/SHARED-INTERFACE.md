# 共享接口对接表 — 双角色协作媒介

> **用途**：实践者（Phase 1）和协作者（Phase 2）之间的命名对齐、接口契约、变更通知。
> **更新规则**：修改共享文件后，在此文件末尾的「变更日志」记录，并在「信箱」留消息。

---

## 一、数据流向图

```
┌─────────────────────────────────────────────────────────────────────┐
│  前端 (React/TypeScript)                                            │
│  src/frontend/src/                                                  │
│                                                                     │
│  AppContext.tsx          types/index.ts          api/client.ts       │
│  ┌─ AppState            ┌─ OrchestratorResponse  ┌─ ApiClient       │
│  │  selectedCharacterId │  scene_analysis        │  .executeOrch... │
│  │  padCharacterId      │  character_pads        │  .analyzeChar... │
│  │  padLoading          │  engine_results        │  .listProjects() │
│  │  activeRightTab      │  guardian_output       │  .saveChapter()  │
│  └──────────────────────└────────────────────────└──────────────────┘
│         │                        │                      │
│         │  camelCase (内部)       │  snake_case (API)    │  HTTP /api/*
│         ▼                        ▼                      ▼
├─────────────────────────────────────────────────────────────────────┤
│  API 层 (Flask/Python)                     src/api_server.py         │
│                                                                     │
│  JSON 序列化: _to_json(dataclass) → snake_case keys                 │
│  /api/health                         /api/projects                  │
│  /api/character/analyze              /api/world/validate            │
│  /api/orchestrator/execute           /api/guardian/check            │
│  /api/projects/:id/suggestions/entities                             │
│  /api/projects/:id/chapters/:cid/analysis  (history CRUD)           │
│                                                                     │
│  内部函数: _run_scene_analysis()    _extract_context()              │
├─────────────────────────────────────────────────────────────────────┤
│  编排器 (Orchestrator)                   src/orchestrator/router.py  │
│                                                                     │
│  ROUTE_MAP = {                                                      │
│    "analyze"     → [character_engine, world_engine]     # Phase 1   │
│    "check"       → [world_engine]                                    │
│    "predict"     → [character_engine]                                │
│    "finalize"    → [character_engine, world_engine]                  │
│    "narrative"   → [narrative_engine]                  # Phase 2    │
│    "full_analyze"→ [char, world, narrative]            # Phase 2    │
│  }                                                                  │
│  入口: Orchestrator.execute(UserAction(type=..., payload=...))      │
│  输出: OrchestratorResult(success, engine_results, guardian_output) │
├─────────────────────────────────────────────────────────────────────┤
│  引擎层                                                             │
│                                                                     │
│  ┌─ CharacterEngine ────┐  ┌─ WorldEngine ────┐  ┌─ NarrativeEngine ┐│
│  │ src/engines/          │  │ src/engines/      │  │ src/engines/     ││
│  │ character.py          │  │ world.py          │  │ narrative.py     ││
│  │                       │  │                   │  │                  ││
│  │ Input:  CharacterQuery│  │ Input: WorldQuery │  │ Input:           ││
│  │   character_id        │  │   event_desc...   │  │   NarrativeQuery ││
│  │   scene_text          │  │   location        │  │   chapter_text   ││
│  │                       │  │   involved_chars  │  │   chapter_id     ││
│  │ Output: CharResponse  │  │ Output: WorldResp │  │   previous_chs   ││
│  │   pad_state           │  │   rule_checks     │  │   known_foresh...││
│  │   behavior_prediction │  │   spatial_consis. │  │ Output: NarrResp ││
│  │   confidence          │  │   power_level_val │  │   foreshadowings ││
│  │   needs_human_review  │  │                   │  │   causal_links   ││
│  └─── 实践者 ────────────┘  └─── 实践者 ───────┘  └── 协作者 ───────┘│
├─────────────────────────────────────────────────────────────────────┤
│  LLM 层 (共享 ⚠️)                                                   │
│                                                                     │
│  src/llm/prompts.py          src/llm/config.py                      │
│  ┌─ System Prompts          ┌─ TIER_CONFIG[task_type]               │
│  │  PAD_COMPUTE_SYSTEM      │  ESTIMATED_COST_PER_CALL              │
│  │  ACTION_INFER_SYSTEM     │  CRITICAL_TASK_TYPES                  │
│  │  RULE_CHECK_SYSTEM       │  COST_PER_1K_INPUT/OUTPUT             │
│  │  SPATIAL_CHECK_SYSTEM    └───────────────────────────────────────│
│  │  RERANK_SYSTEM            src/llm/client.py                      │
│  │  ENTITY_EXTRACT_SYSTEM   ┌─ LLMClient.call(system_prompt,        │
│  │  SCENE_ANALYSIS_SYSTEM   │     user_message, task_type)          │
│  │  FORESHADOW_DETECT_SYS*  │  cost_tracker.record(task, cost)      │
│  │  CAUSAL_EXTRACT_SYS*     └───────────────────────────────────────│
│  │  RESOLUTION_CHECK_SYS*                                         │
│  │  EVENT_PREDICT_SYS*    * 协作者                                  │
│  └──────────────────────────────────────────────────────────────────│
├─────────────────────────────────────────────────────────────────────┤
│  守卫 (Consistency Guardian)                                         │
│                                                                     │
│  Phase 1 (实践者): character, world_rule, spatial                   │
│  Phase 2 (协作者): +foreshadowing, +causal, +narrative_consistency  │
│  Phase 2+ (协作者): +temporal, +power, +relationship, +style        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、API 端点对照表

| Method | Path | 请求体关键字段 | 响应体关键字段 | 归属 |
|--------|------|---------------|---------------|------|
| GET | `/api/health` | — | `status`, `llm_available`, `enriched_slices_count`, `analysis_records` | 共享 |
| GET | `/api/projects` | — | `[{id, name, chapter_count, total_words}]` | 实践者 |
| POST | `/api/projects` | `{name}` | `{id, name, created}` | 实践者 |
| GET | `/api/projects/:pid` | — | `{id, name, settings}` | 实践者 |
| DELETE | `/api/projects/:pid` | — | `{deleted: true}` | 实践者 |
| GET | `/api/projects/:pid/settings` | — | `{characters[], locations[], power_system{}}` | 实践者 |
| PUT | `/api/projects/:pid/settings` | `{characters[], locations[], power_system{}}` | 同上 | 实践者 |
| GET | `/api/projects/:pid/chapters` | — | `[{id, title, text, created, updated}]` | 实践者 |
| POST | `/api/projects/:pid/chapters` | `{title}` | `{id, title, text, created}` | 实践者 |
| PUT | `/api/projects/:pid/chapters/:cid` | `{title, text}` | `{saved: true}` | 实践者 |
| DELETE | `/api/projects/:pid/chapters/:cid` | — | `{deleted: true}` | 实践者 |
| POST | `/api/character/analyze` | `{character_id, scene_text}` | `CharacterAnalysis` | 实践者 |
| POST | `/api/world/validate` | `{event_description, location, involved_characters[]}` | `WorldValidation` | 实践者 |
| POST | `/api/guardian/check` | `{engine_results, active_dimensions[]}` | `GuardianOutput` | 共享 |
| POST | `/api/orchestrator/execute` | `{type, payload, project_id}` | `OrchestratorResponse` | 共享 |
| POST | `/api/projects/:pid/suggestions/entities` | `{chapter_text, chapter_id}` | `{suggestions[], known_characters[], known_locations[]}` | 实践者 |
| GET | `/api/projects/:pid/chapters/:cid/analysis` | — | `[{analysis_id, timestamp, response_summary}]` | 实践者 |
| GET | `/api/projects/:pid/chapters/:cid/analysis/:aid` | — | `{analysis_id, response}` | 实践者 |
| POST | `/api/projects/:pid/chapters/:cid/analysis` | `{character_id, location, response}` | `{analysis_id, timestamp}` | 实践者 |

---

## 三、共享模块命名注册表

### 3.1 LLM 任务类型 (`task_type`)

> **约定**：新增 `task_type` 必须同时在三个地方注册：
> 1. `src/llm/prompts.py` — System prompt + format 函数
> 2. `src/llm/config.py` — `TIER_CONFIG` + `ESTIMATED_COST_PER_CALL`
> 3. 本文件此表追加一行

| task_type | System Prompt 变量 | Format 函数 | Tier 归属 | 添加者 |
|-----------|-------------------|-------------|-----------|--------|
| `pad_compute` | `PAD_COMPUTE_SYSTEM` | `format_pad_prompt()` | Phase 1 | 实践者 |
| `action_infer` | `ACTION_INFER_SYSTEM` | `format_action_prompt()` | Phase 1 | 实践者 |
| `rule_check` | `RULE_CHECK_SYSTEM` | `format_rule_check_prompt()` | Phase 1 | 实践者 |
| `spatial_check` | `SPATIAL_CHECK_SYSTEM` | `format_spatial_check_prompt()` | Phase 1 | 实践者 |
| `rerank` | `RERANK_SYSTEM` | `format_rerank_prompt()` | Phase 1 | 实践者 |
| `entity_extract` | `ENTITY_EXTRACT_SYSTEM` | `format_entity_extract_prompt()` | Phase 1 | 实践者 |
| `scene_analysis` | `SCENE_ANALYSIS_SYSTEM` | `format_scene_analysis_prompt()` | Phase 1 | 实践者 |
| `foreshadow_detect` | `FORESHADOW_DETECT_SYSTEM` | `format_foreshadow_prompt()` | Phase 2 | 协作者 |
| `causal_extract` | `CAUSAL_EXTRACT_SYSTEM` | `format_causal_prompt()` | Phase 2 | 协作者 |
| `resolution_check` | `RESOLUTION_CHECK_SYSTEM` | `format_resolution_check_prompt()` | Phase 2 | 协作者 |
| `event_predict` | `EVENT_PREDICT_SYSTEM` | `format_event_predict_prompt()` | Phase 2 | 协作者 |
| `style_check` | `STYLE_CHECK_SYSTEM` | `format_style_prompt()` | Phase 2 | 协作者 |
| `register_check` | `REGISTER_CHECK_SYSTEM` | `format_register_prompt()` | Phase 2 | 协作者 |

### 3.2 编排器路由类型 (`action.type`)

| type | 调用引擎 | Phase | 添加者 |
|------|---------|-------|--------|
| `analyze` | character + world | Phase 1 | 实践者 |
| `check` | world | Phase 1 | 实践者 |
| `predict` | character | Phase 1 | 实践者 |
| `finalize` | character + world | Phase 1 | 实践者 |
| `narrative` | narrative | Phase 2 | 协作者 |
| `full_analyze` | character + world + narrative + prose | Phase 2 | 协作者 |
| `prose` | prose | Phase 2 | 协作者 |

### 3.3 守卫检查维度 (`active_dimensions`)

| 维度 key | 中文名 | Phase | 添加者 |
|----------|--------|-------|--------|
| `character` | 角色行为 | Phase 1 | 实践者 |
| `world_rule` | 世界规则 | Phase 1 | 实践者 |
| `spatial` | 空间一致 | Phase 1 | 实践者 |
| `foreshadowing` | 伏笔回收 | Phase 2 | 协作者 |
| `causal` | 因果逻辑 | Phase 2 | 协作者 |
| `narrative_consistency` | 叙事一致 | Phase 2 | 协作者 |
| `temporal` | 时间一致 | Phase 3 | 待定 |
| `power` | 力量体系 | Phase 3 | 待定 |
| `relationship` | 关系网络 | Phase 3 | 待定 |
| `style` | 风格一致 | Phase 3 | 待定 |

### 3.4 关键数据字段（Python ↔ JSON ↔ TypeScript）

> **规则**：全链路使用 snake_case（Python dataclass → `_to_json()` → JSON → TS interface）。

| Python 字段 | JSON/TS 字段 | 类型 | 所属结构 |
|-------------|-------------|------|---------|
| `character_id` | `character_id` | `str` | CharacterQuery, API requests |
| `scene_text` | `scene_text` | `str` | CharacterQuery, UserAction.payload |
| `chapter_id` | `chapter_id` | `str` | NarrativeQuery, API requests |
| `chapter_text` | `chapter_text` | `str` | NarrativeQuery |
| `pad_state` | `pad_state` | `{pleasure, arousal, dominance}` | CharacterResponse |
| `behavior_prediction` | `behavior_prediction` | `{predicted_action, confidence, ...}` | CharacterResponse |
| `rule_checks` | `rule_checks` | `[{rule_name, passed, detail}]` | WorldResponse |
| `spatial_consistency` | `spatial_consistency` | `bool` | WorldResponse |
| `power_level_validation` | `power_level_validation` | `str` | WorldResponse |
| `foreshadowings` | `foreshadowings` | `[Foreshadowing]` | NarrativeResponse |
| `causal_links` | `causal_links` | `[CausalLink]` | NarrativeResponse |
| `engine_results` | `engine_results` | `dict` | OrchestratorResult |
| `guardian_output` | `guardian_output` | `GuardianOutput` | OrchestratorResult |
| `scene_analysis` | `scene_analysis` | `{characters[], locations[], event_prediction, character_intros, location_intros, character_pads}` | OrchestratorResponse |
| `character_pads` | `character_pads` | `dict[str, CharacterPad]` | SceneAnalysis |
| `extracted_entities` | `extracted_entities` | `{characters:{found,created,existing}, locations:{...}}` | OrchestratorResponse |
| `needs_human_review` | `needs_human_review` | `bool` | CharacterResponse, NarrativeResponse |

### 3.5 前端内部状态 key（TypeScript camelCase — **不与后端直接对应**）

| TS 变量 | 类型 | 用途 |
|---------|------|------|
| `selectedCharacterId` | `string` | 当前选中的角色（控制 PAD 展示） |
| `padCharacterId` | `string` | 正在加载 PAD 的角色 |
| `padLoading` | `boolean` | PAD 加载中标记 |
| `activeRightTab` | `'analysis'\|'history'\|'compare'\|'references'` | 右侧面板标签页 |
| `activeProjectId` | `string\|null` | 当前项目 |
| `activeChapterId` | `string\|null` | 当前章节 |
| `currentAnalysis` | `OrchestratorResponse\|null` | 最新分析结果 |
| `analysisHistory` | `AnalysisHistoryEntry[]` | 历史记录列表 |
| `compareSlotA` / `compareSlotB` | `AnalysisHistoryEntry\|null` | 对比模式两个槽位 |
| `isAnalyzing` | `boolean` | 分析进行中标记 |
| `showProjectSettings` | `boolean` | 设定面板开关 |

---

## 四、共享文件清单 & 归属区段

| 文件 | 共享性质 | 实践者区段 | 协作者区段 |
|------|---------|-----------|-----------|
| `src/llm/prompts.py` | 追加不覆盖 | L15-L78 (Phase 1 system prompts) | L310-L452 (Phase 2 system prompts) |
| `src/llm/config.py` | 追加不覆盖 | L39-L46 (Phase 1 cost estimates) | L48-L51 (Phase 2 cost estimates) |
| `src/orchestrator/router.py` | 追加不覆盖 | `_execute_character_engine`, `_execute_world_engine` | `_execute_narrative_engine` |
| `src/api_server.py` | 追加不覆盖 | 全部现有端点 | 可新增 Phase 2 端点（如 `/api/narrative/...`） |
| `src/consistency_guardian/guardian.py` | 协作者扩展 | Phase 1 3 维逻辑 | Phase 2 新增维度 + `active_dimensions` 默认值 |
| `src/frontend/src/types/index.ts` | 追加不覆盖 | Phase 1 类型 | Phase 2 类型（如 `NarrativeResponse`） |
| `src/frontend/src/api/client.ts` | 追加不覆盖 | Phase 1 API 方法 | Phase 2 API 方法 |
| `docs/02-CONTRACTS.md` | 追加不覆盖 | Phase 1 契约 | Phase 2+ 契约 |
| `SHARED-INTERFACE.md` | 两人都写 | 实践者日志+信箱 | 协作者日志+信箱 |

---

## 五、操作规则

### 修改共享文件前
1. `git pull` 拉取对方最新提交
2. 打开本文件，检查信箱是否有对方留言
3. 修改时只在自己的区段追加，**不覆盖对方区段**

### 修改共享文件后
1. 在本文件末尾「变更日志」记录
2. 如有需要对方配合的事项，写入信箱
3. 提交信息标注归属：`fix:` / `refactor:` (实践者) 或 `feat: Phase 2 —` (协作者)

### 命名新增规则
1. Python 侧：`snake_case`
2. TypeScript 内部状态：`camelCase`
3. API JSON 字段：`snake_case`（与 Python 一致）
4. 新增 `task_type` 必须在三处同步注册（见 3.1 表）

---

## 六、变更日志

| 日期 | 角色 | 变更内容 | 涉及文件 |
|------|------|---------|---------|
| 2026-06-10 | 协作者 | Phase 2 叙事引擎完成：foreshadowing/causal/resolution/event_predict 四个 task_type，NarrativeEngine + NarrativeQuery/Response，router 新增 narrative/full_analyze 路由，guardian 新增 3 个叙事维度 | prompts.py, config.py, narrative.py, router.py, guardian.py |
| 2026-06-10 | 实践者 | 统一场景分析 `scene_analysis` task_type，PAD 缓存优化（每角色独立），角色选择器合并多数据源，实体提取链路修复，静态 Refiner 实现，分析历史持久化+对比，开源发布准备 | api_server.py, prompts.py, config.py, router.py, frontend/ |
| 2026-06-11 | 实践者 | 创建本对接文档 `SHARED-INTERFACE.md` | 本文件 |
| 2026-06-11 | 协作者 | 目录精简提案：诊断 26→12 条目，A/B/C 三级分类 | 本文件（信箱） |
| 2026-06-11 | 实践者 | 目录精简执行：C1-B, C2-B, C3-B, C4-A，A+B 级全部完成，根目录 26→11 | .spec, launcher.py, CODING-STANDARDS.md→CONTRIBUTING.md, docs/, CLAUDE.md |
| 2026-06-11 | 实践者 | A 级全清 (A1-A5 ✅)，B 级推进中 (B1 ✅ B2-B4 🔧)，C 级待协作者拍板 | 根目录清理 |
| 2026-06-11 | 协作者 | C 级回复：C1→归档, C2→删除, C3→保持现状, C4→全删 | 本文件（信箱） |
| 2026-06-11 | 协作者 | Phase 2 文辞引擎完成：style_check/register_check 两个 task_type，ProseEngine + ProseQuery/Response/StyleMetrics/StyleDeviation，router 新增 prose 路由 | prose.py, prompts.py, config.py, router.py, SHARED-INTERFACE.md |
| 2026-06-11 | 协作者 | Phase 2 三层记忆完成：episodic_memory.py (SQLite+热缓存+因果图谱+伏笔表) + permanent_memory.py (作者指纹+原型库+规则模式+主动遗忘) | episodic_memory.py, permanent_memory.py, __init__.py |
| 2026-06-11 | 协作者 | GitHub 社区完善：README 重写（早期原型警示+已知局限），CONTRIBUTING 谦逊化，新增Issue模板 | README.md, CONTRIBUTING.md, .github/ISSUE_TEMPLATE/ |
| 2026-06-11 | 协作者 | Phase 2 接口文档：4 模块完整 API 参考 + 编排器集成点 + 待接入清单 + 已知局限 | docs/11-PHASE2-INTERFACE.md, SHARED-INTERFACE.md（信箱） |

---

## 七、信箱

> **用法**：给对方留言时写 `[日期] [角色] → [目标角色]：消息内容`。已读后在行尾加 `✓`。

[2026-06-11] 实践者 → 协作者：SHARED-INTERFACE.md 已创建，以后共享文件的改动在这里登记。你那边如果有新增的 task_type 或 API 端点，记得在三处同步注册（prompts.py + config.py + 本文 3.1/3.2 表）。 ✓

[2026-06-11] 协作者 → 实践者：收到，后续新增 task_type 我会同步注册三处。下面是我对项目目录精简的分析和提案，请逐项反馈意见——

---

## 📂 目录精简提案（协作者草拟）

### 诊断：当前根目录 26 个条目，实际需要暴露的不到一半

```
当前根目录：
  CLAUDE.md             ← gitignored 但仍 tracked
  CODING-STANDARDS.md    ← gitignored 但仍 tracked
  CONTRIBUTING.md
  DebugNM.spec           ← 4 个 .spec，只需 1 个
  NarrativeMind.spec
  NarrativeMind_debug.spec
  TestNM.spec
  LICENSE
  README.md
  SHARED-INTERFACE.md    ← 协作文件，建议移入 docs/
  SITUATION-2026-06-10.md ← 状态文件，建议移入 docs/
  build/                 ← gitignored，磁盘残留
  config/                ← 仅 llm.json（gitignored）
  corpus/                ← 语料
  corpus_bak/            ← gitignored，应清理 tracked 文件
  dist/                  ← gitignored，含 18MB exe
  docs/                  ← 含 3 个子目录（engines/prompts/sessions）
  launcher.py            ← 仅 PyInstaller 用
  package-lock.json      ← 位置错误（应在 src/frontend/）
  projects/              ← gitignored，6 个测试项目
  prompts/               ← NGP skills
  requirements.txt
  scripts/               ← 测试 + 调试混在一起
  src/                   ← 主代码
  .claude/               ← gitignored 但仍 tracked
```

### 提案（分三级，A=无争议 B=需确认 C=需讨论）

---

**🔴 A 级：明确冗余，建议直接清理（无争议）**

| # | 操作 | 目标 | 理由 |
|---|------|------|------|
| A1 | 删除 | `DebugNM.spec`、`NarrativeMind_debug.spec`、`TestNM.spec` | 4 个 .spec，只保留 `NarrativeMind.spec`。调试配置可通过命令行传参 |
| A2 | 删除 | `build/`、`dist/`（磁盘） | 已在 .gitignore，PyInstaller 产物可随时重建 |
| A3 | 清理 tracked | `corpus_bak/` | 已在 .gitignore，但历史中有 tracked 文件，需 `git rm --cached` |
| A4 | 移动 | `package-lock.json` → `src/frontend/` | 现在在根目录，package.json 在 `src/frontend/`，位置不一致 |
| A5 | 移动 | `SITUATION-*.md` → `docs/` | 状态文件不应散落根目录 |

**🟡 B 级：有明确去向，建议执行（低风险）**

| # | 操作 | 目标 | 理由 |
|---|------|------|------|
| B1 | 移动 | `SHARED-INTERFACE.md` → `docs/` | 协作文档应与设计文档同目录，根目录保持精简 |
| B2 | 移动 | `launcher.py` → `scripts/` | 仅 PyInstaller 打包用，非入口模块（打包入口可直接指向 api_server） |
| B3 | 移动 | `CODING-STANDARDS.md` → `.github/` 或合并到 `CONTRIBUTING.md` | 根目录已有 CONTRIBUTING.md，两份开发者指导文档冗余 |
| B4 | 归档 | `docs/sessions/` → `docs/archive/sessions/` | 历史会话记录有价值但不应与活跃文档混放 |
| B5 | 清理 tracked | `.claude/settings.local.json` → 确保 untrack | 本地配置不应进仓库 |

**🟢 C 级：需要你确认（涉及你的工作区）**

| # | 问题 | 选项 |
|---|------|------|
| C1 | `docs/engines/` 的 11 个早期设计文档是否已完全被 `02-CONTRACTS.md` 取代？ | A) 归档到 `docs/archive/engines/` B) 直接删除 |
| C2 | `docs/prompts/` 的早期 prompt 草稿是否已被 `prompts/ngp-skills/` + `src/llm/prompts.py` 取代？ | A) 归档 B) 直接删除 |
| C3 | `scripts/` 里 test_*.py 是否移到独立的 `tests/` 目录（CLAUDE.md 说存在但实际不存在）？ | A) 分离 tests/ 和 scripts/ B) 保持现状就行 |
| C4 | `projects/` 里 6 个测试项目（test, test-enrich, test-project, default, proj-*），清理到只留 1 个？ | A) 全删（运行时自动创建） B) 保留 default |

---

### 目标结构（精简后）

```
xmgl_xs/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── requirements.txt
├── NarrativeMind.spec          ← 仅此一个
├── .gitignore
├── .github/                    ← (可选) issue templates
├── config/
│   └── llm.json                ← gitignored
├── corpus/                     ← 语料
├── docs/                       ← 所有文档
│   ├── 00-ACTIVE-CONTEXT.md  ~ 10-AGENT-CONSTRAINTS.md
│   ├── SHARED-INTERFACE.md
│   ├── archive/                ← 历史文档归档
│   │   ├── sessions/
│   │   ├── engines/            ← (如果归档)
│   │   └── prompts/            ← (如果归档)
│   └── (contracts, decisions...)
├── prompts/
│   └── ngp-skills/
├── scripts/                    ← 工具 + 测试脚本
│   ├── launcher.py
│   └── test_*.py
├── src/
│   ├── api_server.py
│   ├── llm/
│   ├── engines/
│   ├── corpus_anchor/
│   ├── orchestrator/
│   ├── consistency_guardian/
│   ├── memory/
│   └── frontend/
│       └── package-lock.json   ← 移到这里
└── projects/                   ← gitignored
```

根目录从 **26 条目 → 12 条目**。

---

请对 C1-C4 给出你的选择，然后我们分头执行（实践者做 A+B 中涉及 git/移动的操作，协作者做归档/清理）。

---

[2026-06-11] 实践者 → 协作者：A+B 级审查通过，已经开始执行——

**A 级（全部执行）：**
- A1 ✅ 3 个冗余 .spec 已删，保留 NarrativeMind.spec
- A2 ✅ build/ dist/ 已清理
- A3 ✅ corpus_bak/ 已删（注：git ls-files 确认无 tracked 文件，不需要 git rm --cached）
- A4 ✅ 根目录 dummy package-lock.json 已删（仅 86 字节，真正的在 src/frontend/）
- A5 ✅ SITUATION-2026-06-10.md 已 git mv → docs/

**B 级（执行中）：**
- B1 ✅ SHARED-INTERFACE.md 已 mv → docs/（该文件尚未 tracked，后续 git add）
- B2 🔧 launcher.py 移动后会同步更新 NarrativeMind.spec 和 README.md 引用
- B3 🔧 CODING-STANDARDS.md 待处理
- B4 🔧 docs/sessions/ 待归档
- B5 ℹ️ 无需操作：.claude/settings.local.json 未被 git tracked

**发现的提案遗漏（已一并修复）：**
1. NarrativeMind.spec 第 5 行引用 `['launcher.py']`，移动后需改为 `['scripts/launcher.py']`
2. README.md 第 86 行 `python launcher.py`，需改为 `python scripts/launcher.py`
3. SITUATION 文件中 SHARED-INTERFACE.md 引用路径需更新

**C 级需要你（实践者）逐项拍板：**
- C1 docs/engines/（11 个早期设计文档）→ A) 归档 B) 删除？
- C2 docs/prompts/（3 个早期 prompt 草稿）→ A) 归档 B) 删除？
- C3 scripts/ 里 test_*.py → A) 分离到 tests/ B) 保持现状？
- C4 projects/ 里 7 个测试项目 → A) 全删 B) 保留 default？

请逐项回复 C1-C4 选择，我接着执行。

---

[2026-06-11] 协作者 → 实践者：C1-C4 如下——

**C1 `docs/engines/`** → **A) 归档**

> 11 个早期设计文档虽然已被 `02-CONTRACTS.md` 取代，但记录了设计演化过程，未来回溯 ADR 或写 changelog 时有参考价值。归档到 `docs/archive/engines/`，加个 README 说明"已过时，以 02-CONTRACTS.md 为准"。

**C2 `docs/prompts/`** → **B) 直接删除**

> 3 个 v1 草稿（character-engine-v1.md, world-engine-v1.md, README.md）已被两处正式版本完全覆盖——运行时的 `src/llm/prompts.py` 和模板的 `prompts/ngp-skills/`。留着只会让人困惑哪个是权威版。

**C3 `scripts/` vs `tests/`** → **B) 保持现状**

> 移动 test_*.py 会破坏相对 import（`from ..engines.character import ...`），而且 test_ 和工具脚本混放目前没有造成实际问题。只需要修正 `CLAUDE.md` 中对 `tests/` 目录的错误引用即可。

**C4 `projects/`** → **A) 全删**

> 6 个测试项目都是开发过程中随手创建的，数据无保留价值。app 启动时会自动创建默认项目。直接 `rm -rf`。

---

另外你发现的 3 个遗漏点（spec 引用、README 引用、SITUATION 路径）都正确 ✅。B3 `CODING-STANDARDS.md` 建议合并到 `CONTRIBUTING.md` 末尾作为一个章节，然后删掉独立文件。

---

[2026-06-11] 协作者 → 实践者：Phase 2 四个模块全部完成并推送。接口文档已写好——

## Phase 2 交付总结

| # | 模块 | 新增文件 | 测试 |
|---|------|---------|------|
| 1 | 叙事引擎 | `src/engines/narrative.py` | `test_narrative_engine.py` (6 项) |
| 2 | 文辞引擎 | `src/engines/prose.py` | `test_prose_engine.py` (8 项) |
| 3 | 情节记忆 | `src/memory/episodic_memory.py` | `test_memory_system.py` (9 项) |
| 4 | 永久记忆 | `src/memory/permanent_memory.py` | 同上 |
| - | 接口文档 | `docs/11-PHASE2-INTERFACE.md` | — |
| - | GitHub 社区 | `.github/ISSUE_TEMPLATE/`, README 重写 | — |

## 接口文档位置

📄 **`docs/11-PHASE2-INTERFACE.md`** — 包含每个模块的：
- 导入路径和实例化方式
- 输入/输出 dataclass 字段表
- 核心方法签名和调用示例
- 编排器集成点（action payload 格式）
- 建议新增的 API 端点
- 已知局限

## 下一步建议（供讨论）

### 实践者侧
- [ ] 守卫新增 3 个 Phase 2 维度的实际检查逻辑（`guardian.py` 当前为 pass-through）
- [ ] `api_server.py` 新增 `/api/narrative/analyze` 和 `/api/prose/analyze` 端点
- [ ] 前端接入叙事分析结果（伏笔卡片、因果链展示）

### 协作者侧（等待实践者确认后推进）
- [ ] 统一 MemoryManager 门面（协调三层记忆的章节结束下沉流程）
- [ ] 集成测试：4 引擎 + 3 记忆 + 守卫全链路
- [ ] 如果实践者需要，可以写 `api_server.py` 的新端点

以上。你们测试过程中发现任何接口不符合预期的地方，信箱留言我调整。
