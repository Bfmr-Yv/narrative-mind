# Narrative Mind v4.0 — Rust 核心 + Tauri + Monaco 架构实施计划

## Context

当前 v3.1 是 Flask + React 分析器架构，存在引擎无协同、分析不作用于创作、架构僵化等问题。用户决定中止 Phase 3 增补，全面重构为多 Agent 协作写作 IDE。

**技术选型已确定**：Rust 核心一步到位、Tauri 桌面框架、Monaco 独立编辑器、Python 作为 LLM sidecar。

## 目标

将 Narrative Mind 从"8 引擎分析器"重构为"9 Agent 协作写作 IDE"，保留全部引擎概念（PAD、伏笔、语域等）但改变实现方式和交互形态。

---

## 一、架构概览

```
Tauri Webview (Monaco + React)
    │  Tauri IPC (invoke + events)
Rust Core (crates workspace, ~8 crates)
    │  HTTP localhost:9091
Python Sidecar (FastAPI, LLM + 语料 + prompts)
```

**Rust 管**：Agent 调度、消息传递、状态管理、SQLite 存储、Orchestrator  
**Python 管**：LLM API 调用、17 个 System Prompt 模板、LanceDB 向量检索、Text Embedding

---

## 二、Rust Crate 结构

| Crate | 职责 | 关键类型 |
|-------|------|---------|
| `xmgl-core` | 共享类型、错误、Tier 配置 | `PADState`, `TextRange`, `ProjectMeta`, `Chapter`, 17 task_type |
| `xmgl-agent` | Agent trait、注册表、生命周期、SharedContext | `Agent`, `AgentPosition`, `AgentProbe`, `EditProposal`, `Finding` |
| `xmgl-orchestrator` | 调度中心、复杂度预判、拓扑选择、轮次管理 | `Orchestrator`, `ComplexityJudge`, `RoundManager`, `HcpMadEngine` |
| `xmgl-memory` | 三层记忆：工作/情节/永久 | `WorkingMemory`, `EpisodicMemory`, `PermanentMemory`, `PadHistory` |
| `xmgl-project` | 项目/章节 CRUD、设定管理、旧数据迁移 | `ProjectManager`, `MigrationManager` |
| `xmgl-python-bridge` | Python sidecar HTTP 客户端 | `PythonBridge`, `/v1/llm/call`, `/v1/corpus/search` |
| `xmgl-tauri` | Tauri commands + events（薄层） | `#[tauri::command]`, `AgentProgressEvent`, `ProposalReadyEvent` |

**依赖规则**：
- 只有 `xmgl-orchestrator` 有记忆写入权
- 只有 `xmgl-python-bridge` 做 HTTP
- `xmgl-core` 零外部依赖（仅 serde）
- `xmgl-memory` 不依赖 `xmgl-agent`

---

## 三、Agent 系统

### 3.1 Agent Trait

```rust
#[async_trait]
pub trait Agent: Send + Sync {
    fn id(&self) -> AgentId;               // 9 个枚举值
    fn name(&self) -> &'static str;        // "角色 Agent"
    fn lens(&self) -> AgentLens;           // 分析维度 + 模型级别
    fn model_tier(&self) -> ModelTier;     // Pro | Flash | RuleOnly

    // Hermes Council 5 阶段（具体 Agent 实现 3 个核心方法）
    async fn form_position(&self, ctx, bridge) -> AgentPosition;
    async fn probe_position(&self, ctx, target, bridge) -> AgentProbe;
    async fn reflect(&self, ctx, own, probes, bridge) -> AgentPosition;
    async fn produce_proposals(&self, ctx, position, bridge) -> Vec<EditProposal>;
}
```

### 3.2 9 个 Agent 实例

```
agents/
  character_agent.rs       PAD 三维 + 行为模式，ModelTier::Pro
  world_agent.rs           规则校验 + 空间一致，ModelTier::Flash
  narrative_agent.rs       伏笔 + 因果链 + 节奏，ModelTier::Pro
  prose_agent.rs           句长/语域/修辞/对话，ModelTier::Flash
  theme_agent.rs           主题提取 + 强度追踪，ModelTier::Pro
  economy_agent.rs         资源流动校验，ModelTier::Flash
  reader_expectation_agent.rs  信息差建模，ModelTier::Flash
  conception_agent.rs      意象注册 + 演变，ModelTier::Flash
  editor_in_chief.rs       冲突裁决 + 优先级排序，ModelTier::Pro
```

每个 Agent 是一个 struct 实现 `Agent` trait。注册方式：
```rust
registry.register(Box::new(CharacterAgent::new(pad_history)));
```
单行注册，不再需要 5 文件同步。

### 3.3 核心消息类型

- `AgentPosition` — Agent 的分析结论（findings, confidence, reasoning, assumptions, uncertainties）
- `AgentProbe` — Agent 之间的交叉审问（Challenge/Question/Endorse/Refine/Escalate）
- `EditProposal` — 最终输出：原文位置 + 替换文本 + 理由 + 支持/反对的 Agent 列表
- `Finding` — 单条发现（category, severity, location, original_text, suggested_text, explanation）
- `AssumptionMap` — 分歧根因地图（当 Agent 无法达成共识时）

### 3.4 Agent 生命周期

```
Idle → Analyzing → Proposing → Probing → Reflecting → Producing → Done
                              → Endorsing  → Done
                              → Escalating → EditorInChief
```

每阶段有 30s 超时，超时后标记为 TimedOut，继续处理其他 Agent 的结果。

---

## 四、Orchestrator（调度中心）

### 4.1 复杂度预判

根据触发类型 + 文本长度 + 文本特征信号（角色数、地点数、对话比、冲突关键词）→ 判定为 5 级复杂度之一：

| 级别 | 文本量 | Agent 数 | 协作轮次 |
|------|--------|---------|---------|
| Trivial | <100字 | 0（本地规则） | 0 |
| Simple | <500字 | 1 | 1 |
| Moderate | 500-2000字 | 2-3 | 1-2 |
| Complex | 2000-4000字 | 4+ | 2-3 |
| FullScene | 全章 | 9 | 3-5 |

### 4.2 拓扑选择

- **Parallel**：Agent 独立分析，无交叉 → Simple/Moderate
- **Sequential**：Agent 链式接力 → 续写场景
- **Hierarchical**：并行→交叉审问→总编裁决 → Complex/FullScene

### 4.3 Hermes Council 五阶段映射

| 阶段 | 方法 | 每个 Agent 做什么 | LLM 调用 |
|------|------|-----------------|---------|
| 1. Premortem | `stage_premortem()` | "如果这次分析失败，最可能原因是什么？" | N 次并行 |
| 2. Position | `stage_positions()` | 产出 `AgentPosition`（findings + reasoning） | N 次并行 |
| 3. Probe | `stage_probe()` | 读其他 Agent 的 Position → 追问推理过程 | N 次并行 |
| 4. Reflect | `stage_reflect()` | 收到 Probe 后修正自己的 Position | N 次并行 |
| 5. AssumptionMap | `stage_assumption_map()` | 总编产出分歧根因地图 | 0-1 次 |

### 4.4 HCP-MAD 渐进升级

```
阶段1 共识验证: 2 Agent 独立判断 → 一致 → 完成
                               → 不一致 ↓
阶段2 配对辩论: Agent 互相审问 → 达成共识 → 完成
                               → 僵局 ↓
阶段3 集体投票: 全部 Agent 投票 + 总编裁决 → 暴露分歧地图给作家
```

---

## 五、SharedContext

所有 Agent 共享的只读上下文，使用 `RwLock` 按字段分锁（不是一把大锁）：

```rust
pub struct SharedContext {
    pub current_chapter_text: RwLock<String>,
    pub character_sheets: RwLock<HashMap<String, CharacterSheet>>,
    pub active_pad_states: RwLock<HashMap<String, PADState>>,
    pub world_rules: RwLock<Vec<WorldRule>>,
    pub style_baseline: RwLock<Option<StyleBaseline>>,
    pub unresolved_foreshadowings: RwLock<Vec<Foreshadowing>>,
    pub imagery_catalog: RwLock<Vec<ImageryItem>>,
    pub known_themes: RwLock<Vec<ThemeRecord>>,
    pub analysis_span: RwLock<Option<TextRange>>,
    pub active_proposals: RwLock<Vec<EditProposal>>,
    pub current_positions: RwLock<HashMap<AgentId, AgentPosition>>,
}
```

Agent 只能 `.read()`。只有 Orchestrator 通过 `MemoryWriteGuard` 写入。上下文变更通过 `tokio::broadcast` 通知 Agent 失效缓存。

---

## 六、Python Sidecar

### 6.1 保留在 Python 的部分

- 17 个 System Prompt 模板 + 17 个 format 函数
- OpenAI SDK 调用（`openai` Python 包）
- LanceDB 向量数据库
- Text Embedding（sentence-transformers）
- 语料锚定层全栈（slice_manager, retriever, enricher, refiner）

### 6.2 HTTP API 设计

```
POST /v1/llm/call          单次 LLM 调用
POST /v1/llm/call_batch    批量 LLM 调用（N 个 prompt 并行）
POST /v1/llm/call_stream   SSE 流式 LLM 调用
GET  /v1/llm/health        健康检查 + 成本状态
POST /v1/corpus/search     向量检索
POST /v1/corpus/embed      文本 → 向量
POST /v1/prompts/render    渲染 prompt 模板
```

### 6.3 通信协议

- Rust 启动时 spawn `python src-python/main.py` 作为子进程
- 每 5s 健康检查，30s 不可达则重启
- 所有调用 HTTP POST JSON，超时 30s
- 流式输出使用 SSE（`text/event-stream`）

---

## 七、Tauri 集成

### 7.1 Command 映射

旧 Flask 路由 → Tauri commands：
- `/api/projects` → `list_projects`, `create_project`, `delete_project`
- `/api/projects/:id/chapters` → `list_chapters`, `create_chapter`, `save_chapter`
- `/api/orchestrator/execute` → `run_analysis`（核心入口）
- `/api/guardian/check` → 内聚在 Orchestrator 内部，不单独暴露

### 7.2 实时事件流

Rust → 前端推送（Tauri event system）：
- `agent:progress` — Agent 开始/完成某阶段
- `proposal:ready` — 新修改建议就绪 → 前端渲染黄点
- `analysis:complete` — 分析完成，成本+耗时汇总

### 7.3 Monaco 装饰映射

- **黄点** → `GlyphMarginDecoration` + `glyphMarginClassName: 'proposal-dot-yellow'`
- **建议文本** → `ContentWidget`（双击替换、右键退回、Ctrl+左键 Tips）
- **详细 Tips** → `HoverProvider`（展示完整 Agent 讨论折叠面板）

---

## 八、前端

### 8.1 组件树

```
App
├── TitleBar
├── MainLayout
│   ├── LeftSidebar (280px, 可折叠)
│   │   ├── ProjectTree (章节列表)
│   │   ├── CharacterList
│   │   └── AgentStatusBar
│   ├── EditorArea (flex-grow)
│   │   ├── EditorToolbar (模式切换、分析按钮、字数统计、Tier 指示器)
│   │   ├── MonacoEditor
│   │   └── StatusBar
│   └── RightPanel (320px, 可折叠)
│       ├── ProposalList (所有活跃建议)
│       ├── AgentDiscussion (选中建议的完整讨论)
│       └── AnalysisHistory
├── ProjectSettingsModal
├── CostDashboardModal
└── ShortcutHelpModal
```

### 8.2 状态管理

用 Zustand 替代旧 `useReducer` + `AppContext`，零样板代码。关键 actions：
- `runAnalysis(triggerType)` → `invoke('run_analysis', ...)`
- `applyProposal(id)` / `dismissProposal(id)` → `invoke('apply_proposal', ...)`
- Tauri 事件自动 dispatch 到 store

---

## 九、数据存储

全部 SQLite（rusqlite），一张 `xmgl.db`：

- `projects` / `project_settings` / `chapters`（旧 JSON 迁移）
- `episodic_memory` / `causality_graph` / `foreshadowing_registry`（旧 episodic.db 迁移）
- `pad_history`（新增，PAD 时间序列表）
- `permanent_memory`（旧 permanent.db 迁移）
- `analysis_history`（旧 analysis_store JSON 迁移）
- `cost_log` / `monthly_budget`（旧 cost-log.json 迁移）

首次启动自动检测旧 JSON 文件并迁移，写入 `.xmgl_migrated_v4` 标记文件，不删除旧数据。

---

## 十、目录结构（最终形态）

**新项目位置**：`C:\Users\userf\Desktop\narrative-mind\`（与旧 `xmgl_xs\` 完全隔离，旧代码保留不动）

```
Desktop/
├── xmgl_xs/               # v3.1 旧架构（冻结，仅作参考）
└── narrative-mind/        # v4.0 新架构
    ├── README.md
    ├── LICENSE
    ├── .gitignore
    │
    ├── src-tauri/          # Rust workspace (8 crates, ~7000 lines)
    │   ├── Cargo.toml
    │   ├── tauri.conf.json
    │   ├── main.rs
    │   └── crates/
    │       ├── xmgl-core/        # 共享类型、Tier 配置
    │       ├── xmgl-agent/       # Agent trait + 注册表 + 9 个 Agent 实现
    │       ├── xmgl-orchestrator/# 调度中心 + Hermes Council + HCP-MAD
    │       ├── xmgl-memory/      # 三层记忆 (SQLite)
    │       ├── xmgl-project/     # 项目/章节 CRUD + 旧数据迁移
    │       ├── xmgl-python-bridge/ # Python sidecar HTTP 客户端
    │       └── xmgl-tauri/       # Tauri commands + events
    │
    ├── src-python/          # Python sidecar (FastAPI)
    │   ├── main.py
    │   ├── requirements.txt
    │   ├── prompts/         # 17 个 System Prompt + format 函数
    │   ├── llm/             # OpenAI SDK 封装
    │   └── corpus/          # 语料锚定层（LanceDB + embedder）
    │
    ├── src-frontend/        # React + Vite + Monaco + Zustand
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── src/
    │       ├── components/  # TitleBar, LeftSidebar, EditorArea, RightPanel
    │       ├── monaco/      # decorations, widgets, hoverProvider
    │       ├── store/       # Zustand
    │       └── types/       # TypeScript 类型（镜像 Rust serde）
    │
    ├── prompts/             # Agent system prompts（人类可读参考）
    ├── docs/                # 设计文档
    └── config/              # 运行时配置
```

---

## 十一、实施路线图（12 周）

| 阶段 | 周次 | 内容 | 可验证产出 |
|------|------|------|-----------|
| A: 脚手架 | 1-2 | Cargo workspace + Tauri 空壳 + Vite/React/Monaco + Python sidecar 骨架 | Rust ↔ Python 健康检查通过 |
| B: 数据层 | 2-3 | xmgl-core 类型 + xmgl-memory SQLite + xmgl-project CRUD + 旧数据迁移 | 项目/章节 CRUD 通过 Tauri command 可用 |
| C: Agent 基础 | 3-5 | Agent trait + Registry + SharedContext + CharacterAgent + WorldAgent + Python bridge | 2 个 Agent 通过 Python sidecar 调 LLM 产出结果 |
| D: 编排器 | 5-7 | ComplexityJudge + TopologySelector + RoundManager + HCP-MAD | 3+ Agent 并行 → 交叉审问 → 综合输出 |
| E: 前端集成 | 7-9 | Monaco 装饰系统 + 事件流 + RightPanel + LeftSidebar | 黄点显示、点击展开建议、双击替换 |
| F: 剩余 Agent | 9-11 | 全部 9 Agent + 17 prompt 移植 + corpus API | 全功能 9 Agent 协作可用 |
| G: 打磨 | 11-12 | 快捷键 + 被动模式 + 成本面板 + 测试 + PyInstaller 打包 | 可分发安装包 |

---

## 十二、可复用旧代码清单

| 旧文件 | 复用方式 | 去向 |
|--------|---------|------|
| `src/llm/prompts.py` (749行) | 所有 System Prompt + format 函数直接移植 | `src-python/prompts/templates.py` |
| `src/llm/client.py` (166行) | OpenAI SDK 封装逻辑移植 | `src-python/llm/client.py` |
| `src/llm/config.py` Tier 配置 | 重写为 Rust const | `xmgl-core/src/tier.rs` |
| `src/corpus_anchor/` (1527行) | 全部保留在 sidecar | `src-python/corpus/` |
| `src/memory/` SQL schema | 移植为 rusqlite migration | `xmgl-memory/src/*.rs` |
| `src/engines/character.py` PAD 模型 | 概念移植，PAD 状态机用 Rust 重写 | `xmgl-agent/src/agents/character_agent.rs` |
| `src/frontend/src/types/index.ts` | TypeScript 类型定义用作 Rust serde 参考 | `xmgl-core/src/types.rs` |
| `src/project_manager.py` | CRUD 逻辑移植为 SQLite | `xmgl-project/src/project_manager.rs` |

---

## 十三、验证方式

1. **Phase A 验证**：Rust → Python `GET /v1/llm/health` → 返回 `{"status": "ok"}`
2. **Phase B 验证**：Tauri command `list_projects` → 返回迁移后的项目列表
3. **Phase C 验证**：CharacterAgent.form_position() → 返回包含 PAD 值的 AgentPosition
4. **Phase D 验证**：3 Agent 并行分析一段文本 → 交叉审问日志可见 → 产出合并后的 EditProposal 列表
5. **Phase E 验证**：Monaco 编辑器中出现黄点 → 点击展开建议文本 → 双击替换生效
6. **Phase F 验证**：全部 9 Agent 协作 → FullScene 分析 → 黄点 + 建议 + 讨论历史完整
7. **Phase G 验证**：写够 500 字被动触发 → 安装包在全新 Windows 机器上正常运行
