# CLAUDE.md — Narrative Mind v4.0

> **项目**: Narrative Mind v4.0 — AI 辅助小说创作 IDE
> **架构**: Rust 核心 + Tauri 桌面框架 + Monaco 编辑器 + Python LLM Sidecar
> **Phase**: Phase A — 项目脚手架
> **最后更新**: 2026-06-16

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
