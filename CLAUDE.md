# CLAUDE.md — Narrative Mind v4.0

> **项目**: Narrative Mind v4.0 — AI 辅助小说创作 IDE
> **架构**: Rust 核心 + Tauri 桌面框架 + Monaco 编辑器 + Python LLM Sidecar
> **Phase**: Phase A — 项目脚手架
> **最后更新**: 2026-06-16

## 双角色模式

本项目的 Claude Code 助手运行在两种角色下，通过环境变量 `NARRATIVE_MIND_ROLE` 切换。
**建议开两个终端窗口，一个维护者一个开发者，各自身份固定。**

### 维护者模式（默认）

```bash
# 窗口 1 — 维护者（讨论架构、规划、审查）
cd narrative-mind
claude
```

| 允许 | 禁止 |
|------|------|
| 讨论架构设计、技术选型、crate 拆分 | 不直接写代码（不 Edit/Write .rs .py .ts .tsx） |
| 审查代码变更、检查五大硬边界合规 | 不绕过计划直接实现功能 |
| 输出设计文档、进入 EnterPlanMode | |
| 回答项目架构、命名约定、技术约束问题 | |
| 使用 Agent/Workflow 做多文件探索调研 | |

### 开发者模式

```bash
# 窗口 2 — 开发者（写代码、修 bug、跑测试）
cd narrative-mind
NARRATIVE_MIND_ROLE=developer claude
```

| 允许 | 禁止 |
|------|------|
| 按已批准 plan 实现代码 | 不推翻架构决策（crate 拆分、trait 签名、数据流） |
| 修复 bug、运行测试、cargo check | 不自行新增 crate 或修改 Agent trait |
| 在已有 crate 结构内新增文件 | 不自作主张改变依赖关系 |
| 编写/更新文档（docs/） | |
| ⚠️ 发现架构问题 → 标记并提醒切到维护者窗口 | |

**Git 责任**：开发者负责 commit，维护者负责 push。

- 每完成一个独立任务 → `git add -A && git commit -m "feat: <任务描述>"`
- 收到维护者"收工"指令 → 完成当前最小任务，commit，告知维护者
- **不自行 push** — push 由维护者 `/收工` 统一执行
- commit message 格式：`<type>: <中文描述>`（type: feat/fix/chore/docs）

### 共享上下文

两种角色共享：CLAUDE.md（本文件）、项目记忆、Skills、MCP 服务器、权限设置。

### ⛔ 操作铁律：禁止单会话双角色

**两个角色必须跑在两个独立的终端窗口中，各自启动独立的 Claude 进程。**

单会话内切换角色会导致：CWD 污染、文件读取缓存混乱、shell 状态残留。已验证的教训见 `memory/session-handoff-2026-06-16-evening.md`。

| 违规行为 | 正确做法 |
|----------|---------|
| 同一窗口切换 `NARRATIVE_MIND_ROLE` | 开第二个终端窗口 |
| 维护者直接 Edit/Write 代码 | 切到开发者窗口 |
| 开发者推翻架构决策 | 标记问题，通知维护者窗口 |

**明天开工后第一件事**：确认两个窗口已开启，各自身份固定，上下文不互通。

### 协作流程

```
维护者窗口                    开发者窗口
   │                             │
   │ 讨论架构，输出 plan           │
   │──────────────────────────→   │
   │                             │ 按 plan 实现
   │                             │ 发现问题 → 标记
   │  ←────────────────────────  │
   │ 审查代码，调整架构            │
   │──────────────────────────→   │
   │                             │ 继续实现
   │                             │
```

## 项目身份

Narrative Mind 是一个 AI 辅助小说创作系统，v4.0 从 Flask+React 分析器架构全面重构为多 Agent 协作写作 IDE。基于 Tauri + Rust 构建桌面应用，内嵌 Monaco 编辑器，通过 Python sidecar 调用 LLM。

旧项目（v3.1）位于 `../xmgl_xs/`，已冻结保留。

## 五大硬边界

### 1. 语料边界
- 语料库位置：`corpus/`
- 切片标准：500 字场景级
- 语料自扩充由 Python sidecar 处理

### 2. 成本边界
- 月度上限 $20（硬性熔断，三层：50%/80%/95%）
- LLM 调用全部通过 Python sidecar 的 `/v1/llm/call`
- 成本追踪在 Rust 端（`xmgl-memory` crate 的 `cost_log` 表）

### 3. 版本边界
- 文档版本以 `docs/` 目录为准
- 代码版本以 `src-tauri/`、`src-python/`、`src-frontend/` 为准

### 4. 类型边界
- 通用文学创作 Profile
- 不支持特定类型专用 Profile（如修仙、奇幻）

### 5. 人类优先
- AI Agent 只生成建议，所有修改需人类确认
- Agent 间冲突暴露给作家裁决
- 作家是最终裁决者（Director-in-the-Loop）

## 架构一览

```
Tauri Webview (Monaco + React + Zustand)
    │  Tauri IPC (invoke + events)
Rust Core (8 crates)
    │  HTTP localhost:9091
Python Sidecar (FastAPI, LLM + 语料 + prompts)
```

### Rust Crates

| Crate | 职责 |
|-------|------|
| `xmgl-core` | 共享类型、错误、Tier 配置 |
| `xmgl-agent` | Agent trait、注册表、生命周期、SharedContext、9 个 Agent 实现 |
| `xmgl-orchestrator` | 调度中心、复杂度预判、拓扑选择、Hermes Council 协议 |
| `xmgl-memory` | 三层记忆（工作/情节/永久）+ SQLite |
| `xmgl-project` | 项目/章节 CRUD + 旧数据迁移 |
| `xmgl-python-bridge` | Python sidecar HTTP 客户端 |
| `xmgl-tauri` | Tauri commands + events |

### 9 个 Agent

| Agent | 模型级别 | 分析镜头 |
|-------|---------|---------|
| 角色 Agent | Pro | PAD三维情感、行为模式一致性 |
| 世界 Agent | Flash | 规则校验、空间一致性、力量体系 |
| 叙事 Agent | Pro | 伏笔生命周期、因果链、情节节奏 |
| 文辞 Agent | Flash | 句长/语域/修辞、角色对话风格 |
| 主题 Agent | Pro | 主题提取+强度追踪 |
| 经济 Agent | Flash | 资源流动校验 |
| 预期 Agent | Flash | 读者信息差建模 |
| 构思 Agent | Flash | 意象注册+演变追踪 |
| 总编 Agent | Pro | 冲突裁决、优先级排序 |

## 目录结构

```
narrative-mind/
├── CLAUDE.md                # 本文件
├── README.md
├── .gitignore
├── src-tauri/               # Rust 核心 (Cargo workspace)
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── main.rs
│   └── crates/
│       ├── xmgl-core/
│       ├── xmgl-agent/
│       ├── xmgl-orchestrator/
│       ├── xmgl-memory/
│       ├── xmgl-project/
│       ├── xmgl-python-bridge/
│       └── xmgl-tauri/
├── src-python/              # Python sidecar
│   ├── main.py              # FastAPI 入口 (port 9091)
│   ├── requirements.txt
│   ├── prompts/             # 17 个 System Prompt
│   ├── llm/                 # OpenAI SDK 封装
│   └── corpus/              # 语料锚定层
├── src-frontend/            # React + Vite + Monaco + Zustand
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── components/      # UI 组件
│       ├── monaco/          # Monaco 装饰系统
│       ├── store/           # Zustand 状态管理
│       └── types/           # TypeScript 类型
├── prompts/                 # Agent system prompts (可读参考)
├── docs/                    # 设计文档
│   ├── DESIGN-DISCUSSION-2026-06-16.md
│   └── ARCHITECTURE-2026-06-16.md
├── corpus/                  # 语料数据
└── config/                  # 运行时配置
    ├── llm.json             # (gitignored)
    └── world-settings.json
```

## 开发和运行

### 前置条件
- Rust (stable, Edition 2024)
- Node.js ≥ 18
- Python ≥ 3.11
- Tauri CLI: `cargo install tauri-cli`

### 启动
```bash
# 1. Python sidecar
cd src-python
pip install -r requirements.txt
python main.py  # → localhost:9091

# 2. 前端（开发模式）
cd src-frontend
npm install
npm run dev  # → localhost:1420

# 3. Tauri 桌面应用
cd src-tauri
cargo tauri dev
```

## 技术约束

- Rust 核心引擎仅使用标准库 + tokio + rusqlite + reqwest + serde
- Python sidecar 仅处理 LLM 调用和语料检索
- 前端不直接调 LLM API，全部通过 Tauri IPC
- Agent 间通信通过 Orchestrator 的 SharedContext，不直接互相调用
- 只有 xmgl-orchestrator 有记忆写入权

## 命名约定

- Rust: `snake_case` (模块/函数/变量), `PascalCase` (类型/trait)
- Python: `snake_case`
- TypeScript: `camelCase` (变量/函数), `PascalCase` (组件/接口)
- API JSON: `snake_case`
- Agent ID: `PascalCase` 枚举 (`AgentId::Character`)
