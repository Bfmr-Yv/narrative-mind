# Narrative Mind v4.0 — API 接口文档

> **版本**: beta 0.0
> **日期**: 2026-07-02
> **架构**: Tauri (Rust) → IPC ← React Frontend | Python Sidecar (HTTP, port 9091)

---

## 目录

1. [架构概览](#1-架构概览)
2. [Tauri IPC 命令](#2-tauri-ipc-命令)
3. [Python Sidecar REST API](#3-python-sidecar-rest-api)
4. [事件系统](#4-事件系统)
5. [核心数据类型](#5-核心数据类型)
6. [LLM 配置](#6-llm-配置)
7. [Prompt 注册表](#7-prompt-注册表)

---

## 1. 架构概览

```
┌────────────────────────────────────────────────────┐
│  Tauri Webview (React + Monaco + Zustand)          │
│                                                    │
│  前端通过 invoke() 调用 Rust IPC Commands            │
│  Rust 通过 emit() 推送事件给前端                      │
│                                                    │
│  src-frontend/src/api/  ← API 调用封装               │
└──────────────┬──────────────────┬──────────────────┘
               │ Tauri IPC        │ Tauri Events
               ▼                  ▼
┌────────────────────────────────────────────────────┐
│  Rust Core (7 crates)                              │
│                                                    │
│  xmgl-tauri     → Tauri Commands + Events          │
│  xmgl-agent     → Agent trait, 注册表, 9 Agents     │
│  xmgl-orchestrator → 调度中心, Hermes Council       │
│  xmgl-memory    → SQLite 三层记忆 + 成本追踪         │
│  xmgl-project   → 项目/章节 CRUD                    │
│  xmgl-python-bridge → Python Sidecar HTTP 客户端     │
│  xmgl-core      → 共享类型, 错误类型                 │
└──────────────┬────────────────────────────────────┘
               │ HTTP (localhost:9091)
               ▼
┌────────────────────────────────────────────────────┐
│  Python Sidecar (FastAPI)                          │
│                                                    │
│  /v1/llm/call       → 单次 LLM 调用                 │
│  /v1/llm/call_batch → 批量 LLM 调用                  │
│  /v1/prompts/render → Prompt 模板渲染               │
│  /v1/prompts/list   → 列出所有 Prompt               │
│  /v1/corpus/search  → 语料向量检索                   │
│  /v1/llm/health     → 健康检查                       │
└────────────────────────────────────────────────────┘
```

---

## 2. Tauri IPC 命令

所有命令通过 `@tauri-apps/api/core` 的 `invoke()` 调用。
Rust 实现在 `src-tauri/crates/xmgl-tauri/src/commands.rs`。

### 2.1 项目管理

#### `list_projects`

列出所有项目（按更新时间降序）。

```
前端: import { listProjects } from "@/api"
Rust: invoke("list_projects")
```

| 参数 | 无 |
|------|-----|

| 返回值 | 类型 |
|--------|------|
| 项目列表 | `ProjectMeta[]` |

```typescript
const projects = await listProjects();
// [{ id: "abc123", name: "我的小说", chapter_count: 12, total_words: 35000, ... }]
```

#### `create_project`

创建新项目。

```
前端: import { createProject } from "@/api"
Rust: invoke("create_project", { name })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `string` | 项目名称 |

| 返回值 | 类型 |
|--------|------|
| 新创建的项目 | `ProjectMeta` |

#### `get_project`

获取单个项目详情。

```
Rust: invoke("get_project", { id })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 项目 UUID |

| 返回值 | 类型 |
|--------|------|
| 项目信息或 null | `ProjectMeta \| null` |

#### `delete_project`

删除项目（级联删除其下所有章节）。

```
Rust: invoke("delete_project", { id })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 项目 UUID |

| 返回值 | 类型 |
|--------|------|
| 无 | `void` |

---

### 2.2 章节管理

#### `list_chapters`

列出项目下所有章节（按 sort_order 升序）。

```
前端: import { listChapters } from "@/api"
Rust: invoke("list_chapters", { projectId })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `projectId` | `string` | 项目 UUID |

| 返回值 | 类型 |
|--------|------|
| 章节列表 | `ChapterData[]` |

#### `create_chapter`

创建新章节。自动生成 ID、时间戳、字数统计和 sort_order。

```
前端: import { createChapter } from "@/api"
Rust: invoke("create_chapter", { projectId, title, text })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `projectId` | `string` | 所属项目 UUID |
| `title` | `string` | 章节标题 |
| `text` | `string` | 章节正文 |

| 返回值 | 类型 |
|--------|------|
| 新创建的章节 | `ChapterData` |

#### `get_chapter`

获取单个章节详情。

```
Rust: invoke("get_chapter", { id })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 章节 UUID |

| 返回值 | 类型 |
|--------|------|
| 章节信息或 null | `ChapterData \| null` |

#### `update_chapter`

更新章节。自动刷新 `updated_at`，重新计算 `word_count`。

```
前端: import { updateChapter } from "@/api"
Rust: invoke("update_chapter", { chapter })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `chapter` | `ChapterData` | 完整的章节对象 |

| 返回值 | 类型 |
|--------|------|
| 无 | `void` |

> **注意**: 需传入完整的 `ChapterData` 对象，而非仅修改的字段。

#### `delete_chapter`

删除章节。

```
Rust: invoke("delete_chapter", { id })
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 章节 UUID |

| 返回值 | 类型 |
|--------|------|
| 无 | `void` |

---

### 2.3 健康检查

#### `health_check`

检查 Python Sidecar 健康状态。

```
Rust: invoke("health_check")
```

| 参数 | 无 |
|------|-----|

| 返回值 | 类型 |
|--------|------|
| `(sidecar_available, llm_configured, version)` | `[boolean, boolean, string]` |

```typescript
const [sidecarOk, llmReady, version] = await invoke("health_check");
// sidecarOk: Python 服务是否可达
// llmReady: LLM API key 是否已配置
// version: Python sidecar 版本号
```

---

## 3. Python Sidecar REST API

Base URL: `http://localhost:9091`

所有请求/响应用 JSON，字段名 `snake_case`。

### 3.1 健康检查

**`GET /v1/llm/health`**

```bash
curl http://localhost:9091/v1/llm/health
```

**响应**:
```json
{
  "status": "ok",
  "llm_available": true,
  "model": "deepseek-v4-pro",
  "provider": "https://api.deepseek.com/v1",
  "version": "4.0.0",
  "timestamp": 1719900000.0
}
```

---

### 3.2 单次 LLM 调用

**`POST /v1/llm/call`**

```bash
curl -X POST http://localhost:9091/v1/llm/call \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-001",
    "task_type": "pad_compute",
    "system_prompt_key": "pad_compute",
    "user_message": "角色ID：张三\n场景文本：...",
    "response_format": "json"
  }'
```

**请求体 `LLMCallRequest`**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `request_id` | `string` | 否 | 请求 ID，留空自动生成 |
| `task_type` | `string` | 是 | 17 种任务类型之一 (见 §7) |
| `system_prompt_key` | `string` | 是 | Prompt 注册表 key (见 §7) |
| `user_message` | `string` | 是 | 用户消息/格式化后的 prompt |
| `response_format` | `string` | 否 | `"json"` (默认) 或 `"text"` |
| `temperature_override` | `float` | 否 | 覆盖默认 temperature |
| `max_tokens_override` | `int` | 否 | 覆盖默认 max_tokens |
| `provider_override` | `string` | 否 | 覆盖 provider |

**响应 `LLMCallResponse`**:
```json
{
  "request_id": "req-001",
  "success": true,
  "result": {
    "pleasure": 0.5,
    "arousal": -0.2,
    "dominance": 0.3,
    "rationale": "角色心情不错但有点困"
  },
  "usage": {
    "input_tokens": 320,
    "output_tokens": 85,
    "cost_usd": 0.0002,
    "model": "deepseek-v4-pro",
    "latency_ms": 1200
  },
  "error": null
}
```

---

### 3.3 批量 LLM 调用

**`POST /v1/llm/call_batch`**

```bash
curl -X POST http://localhost:9091/v1/llm/call_batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      { "task_type": "pad_compute", "system_prompt_key": "pad_compute", "user_message": "..." },
      { "task_type": "entity_extract", "system_prompt_key": "entity_extract", "user_message": "..." }
    ],
    "parallel": true,
    "max_concurrency": 4
  }'
```

**请求体 `BatchLLMRequest`**:

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `requests` | `LLMCallRequest[]` | 是 | — | 批量请求列表 |
| `parallel` | `boolean` | 否 | `true` | 是否并发执行 |
| `max_concurrency` | `int` | 否 | `4` | 最大并发数 |

**响应 `BatchLLMResponse`**:
```json
{
  "results": [ { "request_id": "...", "success": true, ... } ],
  "total_cost_usd": 0.0015,
  "total_latency_ms": 3400
}
```

---

### 3.4 Prompt 管理

#### 渲染 Prompt

**`POST /v1/prompts/render`**

```bash
curl -X POST http://localhost:9091/v1/prompts/render \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_key": "pad_compute",
    "variables": {
      "character_id": "zhang_san",
      "scene_text": "张三推开门，看见..."
    }
  }'
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `prompt_key` | `string` | Prompt 注册表 key |
| `variables` | `object` | 模板变量 (各 prompt 不同) |

**响应**:
```json
{
  "prompt_key": "pad_compute",
  "system_prompt": "你是一个文学情感分析专家...",
  "user_message": "角色ID：zhang_san\n\n场景文本：...",
  "task_type": "pad_compute"
}
```

#### 列出所有 Prompt

**`GET /v1/prompts/list`**

```bash
curl http://localhost:9091/v1/prompts/list
```

**响应**:
```json
[
  {
    "key": "pad_compute",
    "task_type": "pad_compute",
    "estimated_tokens_in": 300,
    "estimated_tokens_out": 150
  },
  { "key": "entity_extract", "task_type": "entity_extract", ... }
]
```

---

### 3.5 语料检索

**`POST /v1/corpus/search`**

```bash
curl -X POST http://localhost:9091/v1/corpus/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "角色愤怒的描写",
    "top_k": 5
  }'
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `query_text` | `string` | 是 | — | 查询文本 |
| `top_k` | `int` | 否 | `5` | 返回结果数 |
| `filters` | `object` | 否 | `null` | 过滤条件 (预留) |

**响应**:
```json
{
  "results": [
    {
      "slice_id": "slice_001",
      "text": "他双拳紧握，指甲深深嵌入掌心...",
      "source": "corpus/anger_scenes.txt",
      "similarity": 0.87
    }
  ]
}
```

---

## 4. 事件系统

Rust 端通过 Tauri Event System 向前端推送事件，前端通过 `listen()` 订阅。

> **当前状态**: Phase D 接入 Orchestrator 后才会实际 emit。当前 API 为 ready-to-use 占位。

### 4.1 `agent:progress`

Agent 分析进度更新。

```typescript
import { onAgentProgress } from "@/api/events";

const unlisten = await onAgentProgress((payload) => {
  console.log(payload.agent_id, payload.progress_pct);
});
```

**Payload**:
```typescript
interface AgentProgress {
  agent_id: string;       // Agent 标识符，如 "Character"
  agent_name: string;     // 中文名称，如 "角色 Agent"
  stage: string;          // 当前阶段
  progress_pct: number;   // 进度百分比 0-100
}
```

### 4.2 `proposal:ready`

新的修改建议就绪，前端渲染 Monaco 黄点 (gutter marker)。

```typescript
import { onProposalReady } from "@/api/events";

const unlisten = await onProposalReady((payload) => {
  // 在 Monaco 编辑器中标记 payload.location
});
```

**Payload**:
```typescript
interface ProposalReady {
  proposal_id: string;    // 建议 UUID
  agent_id: string;       // 来源 Agent
  title: string;          // 建议标题
  severity: string;       // "Info" | "Warn" | "Critical"
  location?: {
    start_line: number;
    start_column: number;
    end_line: number;
    end_column: number;
  };
}
```

### 4.3 `analysis:complete`

分析完成，汇总成本与耗时。

```typescript
import { onAnalysisComplete } from "@/api/events";

const unlisten = await onAnalysisComplete((payload) => {
  console.log(`分析完成，花费 $${payload.total_cost}`);
});
```

**Payload**:
```typescript
interface AnalysisComplete {
  total_cost: number;       // 总成本 USD
  total_latency: number;    // 总耗时 ms
  agent_count: number;      // 参与 Agent 数
  findings_count: number;   // 发现的问题数
}
```

---

## 5. 核心数据类型

所有类型在 Rust (`xmgl-core`) 和 TypeScript (`src-frontend/src/types/`) 中同步维护。

### ProjectMeta

```typescript
interface ProjectMeta {
  id: string;             // UUID
  name: string;
  created_at: string;     // ISO 8601
  updated_at: string;
  chapter_count: number;  // 章节数
  total_words: number;    // 总字数
}
```

### ChapterData

```typescript
interface ChapterData {
  id: string;             // UUID
  project_id: string;     // 所属项目 UUID
  title: string;
  text: string;
  word_count: number;
  sort_order: number;     // 排序序号
  created_at: string;
  updated_at: string;
}
```

### PADState

PAD 三维情感坐标（角色 Agent 内部模型）。

```typescript
interface PADState {
  pleasure: number;   // 愉悦度 [-1, 1]
  arousal: number;    // 唤醒度 [-1, 1]
  dominance: number;  // 支配度 [-1, 1]
}
```

### AgentId

9 个 Agent 标识符枚举：

| Rust 值 | 中文名称 | 模型级别 |
|---------|---------|---------|
| `Character` | 角色 Agent | Pro |
| `World` | 世界 Agent | Flash |
| `Narrative` | 叙事 Agent | Pro |
| `Prose` | 文辞 Agent | Flash |
| `Theme` | 主题 Agent | Pro |
| `Economy` | 经济 Agent | Flash |
| `ReaderExpectation` | 预期 Agent | Flash |
| `Conception` | 构思 Agent | Flash |
| `EditorInChief` | 总编 Agent | Pro |

### TaskType

17 种 LLM 任务类型：

| Key | Phase | 说明 |
|-----|-------|------|
| `pad_compute` | 1 | PAD 情感计算 ✅ |
| `action_infer` | 1 | 行为推断 [STUB] |
| `rule_check` | 1 | 规则校验 [STUB] |
| `spatial_check` | 1 | 空间一致性 [STUB] |
| `rerank` | 1 | 重排序 [STUB] |
| `entity_extract` | 1 | 实体提取 ✅ |
| `scene_analysis` | 1 | 场景分析 [STUB] |
| `foreshadow_detect` | 2 | 伏笔检测 [STUB] |
| `causal_extract` | 2 | 因果链提取 [STUB] |
| `resolution_check` | 2 | 伏笔回收 [STUB] |
| `event_predict` | 2 | 事件预测 [STUB] |
| `style_check` | 2 | 风格检查 [STUB] |
| `register_check` | 2 | 语域检查 [STUB] |
| `theme_extract` | 3 | 主题提取 [STUB] |
| `economy_check` | 3 | 经济校验 [STUB] |
| `expectation_analyze` | 3 | 预期分析 [STUB] |
| `imagery_detect` | 3 | 意象检测 [STUB] |

### Severity

```typescript
type Severity = "Info" | "Warn" | "Critical";
```

### TextRange

```typescript
interface TextRange {
  start_line: number;
  start_column: number;
  end_line: number;
  end_column: number;
  start_byte: number;
  end_byte: number;
}
```

### AgentFinding

```typescript
interface AgentFinding {
  agent_id: AgentId;
  severity: Severity;
  title: string;
  description: string;
  location: TextRange | null;
  suggestion: string | null;
  timestamp: string;
}
```

### CoreError

Rust 统一错误类型（通过 Tauri IPC 序列化为字符串）：

| 变体 | 说明 |
|------|------|
| `NotFound(String)` | 资源不存在 |
| `AlreadyExists(String)` | 资源已存在 |
| `InvalidArgument(String)` | 参数无效 |
| `InvalidState(String)` | 状态错误 |
| `Internal(String)` | 内部错误 |

---

## 6. LLM 配置

### 配置优先级

```
函数参数 > 环境变量 > config/llm.json > 默认值
```

### 支持的 Provider

#### DeepSeek V4 (推荐)

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `LLM_PROVIDER=deepseek` | 强指定 provider | 自动检测 |
| `DEEPSEEK_API_KEY` | API 密钥 | — |
| `DEEPSEEK_BASE_URL` | API 端点 | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-v4-pro` |

| 模型 | 用途 | Input $/1K | Output $/1K |
|------|------|-----------|-------------|
| `deepseek-v4-pro` | Pro Tier (5 Agents) | $0.000435 | $0.00087 |
| `deepseek-v4-flash` | Flash Tier (4 Agents) | $0.00014 | $0.00028 |

#### OpenAI (备选)

| 环境变量 | 默认值 |
|----------|--------|
| `LLM_PROVIDER=openai` | 自动检测 |
| `OPENAI_API_KEY` | — |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | `gpt-4o-mini` |

### 成本控制

| 参数 | 值 |
|------|-----|
| 月度预算上限 | `$20.00` |
| 50% 熔断 | ⚠️ 警告 |
| 80% 熔断 | 🔒 仅关键任务 |
| 95% 熔断 | 🚫 全阻断 |
| API 超时 | 25s |
| 最大重试 | 2 次 |

### 配置文件示例 (`config/llm.json`)

```json
{
  "api_key": "sk-...",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-v4-pro"
}
```

---

## 7. Prompt 注册表

### 已实现的 Prompt

#### `pad_compute` (✅)

PAD 三维情感计算。

**模板变量**:
| 变量 | 类型 | 说明 |
|------|------|------|
| `character_id` | `string` | 角色 ID |
| `scene_text` | `string` | 场景文本 (≤3000 字符) |
| `corpus_context` | `string` | 语料参考 (≤800 字符) |
| `emotion_note` | `string` | 情感标记 |

**估计 Token**: In 300, Out 150

**LLM 输出**:
```json
{"pleasure": 0.5, "arousal": -0.2, "dominance": 0.3, "rationale": "分析理由"}
```

#### `entity_extract` (✅)

角色与地点实体提取。

**模板变量**:
| 变量 | 类型 | 说明 |
|------|------|------|
| `chapter_text` | `string` | 章节文本 (≤4000 字符) |

**估计 Token**: In 800, Out 200

**LLM 输出**:
```json
{"characters": ["张三", "李四"], "locations": ["大厅", "花园"]}
```

### Stub Prompt (Phase F 补齐)

以下 15 个 prompt 的 system prompt 和 formatter 均为占位实现：

`action_infer`, `rule_check`, `spatial_check`, `rerank`, `scene_analysis`, `foreshadow_detect`, `causal_extract`, `resolution_check`, `event_predict`, `style_check`, `register_check`, `theme_extract`, `economy_check`, `expectation_analyze`, `imagery_detect`

---

## 8. 项目目录结构

```
narrative-mind/
├── API.md                    # 本文件
├── CLAUDE.md                 # 项目说明 + 开发规范
├── README.md
├── .gitignore
├── src-tauri/                # Rust 核心 (Cargo workspace)
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── main.rs               # Tauri 应用入口
│   └── crates/
│       ├── xmgl-core/        # 共享类型、错误
│       ├── xmgl-agent/       # Agent trait + 注册表
│       ├── xmgl-orchestrator/# 调度中心
│       ├── xmgl-memory/      # SQLite 记忆系统
│       ├── xmgl-project/     # 项目/章节 CRUD
│       ├── xmgl-python-bridge/# Python HTTP 客户端
│       └── xmgl-tauri/       # Tauri Commands + Events
├── src-python/               # Python Sidecar
│   ├── main.py               # FastAPI 入口 (port 9091)
│   ├── requirements.txt
│   ├── llm/                  # LLM SDK 封装
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── config.py
│   ├── corpus/               # 语料锚定层
│   │   ├── __init__.py
│   │   ├── embedder.py
│   │   ├── retriever.py
│   │   └── slice_manager.py
│   └── prompts/              # System Prompts
│       └── registry.py
├── src-frontend/             # React + Vite + Monaco
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── api/              # Tauri IPC 调用封装
│       │   ├── index.ts
│       │   ├── projects.ts
│       │   ├── chapters.ts
│       │   └── events.ts
│       ├── components/       # React 组件
│       │   ├── EditorArea.tsx
│       │   ├── LeftSidebar.tsx
│       │   └── TitleBar.tsx
│       ├── monaco/           # Monaco 装饰系统
│       │   └── index.ts
│       ├── store/            # Zustand 状态管理
│       │   └── index.ts
│       └── types/            # TypeScript 类型定义
│           └── index.ts
├── prompts/                  # Agent system prompts (可读参考)
├── docs/                     # 设计文档
├── corpus/                   # 语料数据
└── config/                   # 运行时配置
    ├── llm.json              # (gitignored) LLM 配置
    └── world-settings.json
```

---

## 9. 开发环境

### 前置条件

- **Rust**: stable, Edition 2024
- **Node.js**: ≥ 18
- **Python**: ≥ 3.11
- **Tauri CLI**: `cargo install tauri-cli`

### 启动顺序

```bash
# 1. Python Sidecar (必须先启动)
cd src-python
pip install -r requirements.txt
python main.py  # → http://localhost:9091

# 2. 前端 Dev Server
cd src-frontend
npm install
npm run dev      # → http://localhost:1420

# 3. Tauri 桌面应用
cd src-tauri
cargo tauri dev
```

### Rust 构建/测试

```bash
cd src-tauri
cargo check                # 编译检查
cargo test --workspace     # 全量测试 (当前 65 passing)
cargo build --release      # 发布构建
```

### Python 依赖

```txt
fastapi>=0.100.0
uvicorn>=0.23.0
openai>=1.0.0
lancedb>=0.4.0
sentence-transformers>=2.2.0
```

### 前端脚本

```bash
cd src-frontend
npm run dev       # 开发服务器
npm run build     # 生产构建
npx tsc --noEmit  # 类型检查
```

---

> 📅 最后更新: 2026-07-02 | beta 0.0
