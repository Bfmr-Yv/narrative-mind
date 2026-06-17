# Phase B 接口规格书

> **用途**: Phase B 开发对接文档 — 定义所有 crate 的公共 API、跨层数据流、IPC 契约
> **日期**: 2026-06-17
> **状态**: 接口定义阶段，尚未实现

---

## 零、依赖拓扑与数据流

```
┌─────────────────────────────────────────────────────┐
│                    Tauri WebView                     │
│              (React + Monaco + Zustand)              │
└──────────────┬──────────────────────┬───────────────┘
               │ invoke()             │ Tauri events
               ▼                      ▼
┌─────────────────────────────────────────────────────┐
│              xmgl-tauri (胶水层)                     │
│   #[tauri::command]                                  │
│   list_projects, create_project,                     │
│   get_chapter, update_chapter                        │
│   → emit: agent:progress, proposal:ready,            │
│           analysis:complete                          │
└──────┬──────────────────────┬───────────────────────┘
       │                      │                        
       ▼                      ▼                        
┌──────────────┐   ┌─────────────────────┐            
│ xmgl-project │   │ xmgl-python-bridge  │            
│ ProjectManager│   │ PythonBridge        │            
│ 章节 CRUD    │   │ HTTP → localhost:9091│            
└──────┬───────┘   └─────────────────────┘            
       │                                              
       ▼                                              
┌──────────────┐                                      
│ xmgl-memory  │                                      
│ SQLite 持久化 │                                      
│ 11 张表      │                                      
└──────────────┘                                      
```

**依赖规则**（五大硬边界）：
- 只有 `xmgl-orchestrator` 有记忆写入权（Phase D 才激活，Phase B 先跳过）
- 只有 `xmgl-python-bridge` 做 HTTP
- `xmgl-core` 零外部依赖（仅 serde）
- 前端不直接调 LLM API，全部通过 Tauri IPC

---

## 一、xmgl-memory — SQLite 持久化层

### 1.1 crate 定位

最底层。被 `xmgl-project` 和 `xmgl-orchestrator` 依赖。Phase B 先实现项目/章节相关的表，Phase C/D 再补 Agent 记忆表。

### 1.2 公共 API（计划签名）

```rust
// 数据库初始化
pub fn init_db(path: &str) -> Result<Connection>;

// Schema migration（幂等）
pub fn run_migrations(conn: &Connection) -> Result<()>;

// 项目 CRUD（底层，被 xmgl-project 调用）
pub fn insert_project(conn: &Connection, meta: &ProjectMeta) -> Result<()>;
pub fn list_projects(conn: &Connection) -> Result<Vec<ProjectMeta>>;
pub fn get_project(conn: &Connection, id: &str) -> Result<Option<ProjectMeta>>;
pub fn update_project(conn: &Connection, meta: &ProjectMeta) -> Result<()>;
pub fn delete_project(conn: &Connection, id: &str) -> Result<()>;

// 章节 CRUD（底层）
pub fn insert_chapter(conn: &Connection, chapter: &ChapterData) -> Result<()>;
pub fn get_chapter(conn: &Connection, id: &str) -> Result<Option<ChapterData>>;
pub fn list_chapters(conn: &Connection, project_id: &str) -> Result<Vec<ChapterData>>;
pub fn update_chapter(conn: &Connection, chapter: &ChapterData) -> Result<()>;
pub fn delete_chapter(conn: &Connection, id: &str) -> Result<()>;

// 成本追踪
pub fn log_cost(conn: &Connection, entry: &CostEntry) -> Result<()>;
pub fn get_monthly_cost(conn: &Connection, year: i32, month: i32) -> Result<f64>;
```

### 1.3 Phase B 表结构

以下 7 张表在 Phase B 创建（剩余 4 张等到 Phase C/D）：

```sql
-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    chapter_count INTEGER NOT NULL DEFAULT 0,
    total_words INTEGER NOT NULL DEFAULT 0
);

-- 项目设置表
CREATE TABLE IF NOT EXISTS project_settings (
    project_id  TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    settings_json TEXT NOT NULL DEFAULT '{}'
);

-- 章节表
CREATE TABLE IF NOT EXISTS chapters (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT '',
    text        TEXT NOT NULL DEFAULT '',
    word_count  INTEGER NOT NULL DEFAULT 0,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 成本日志
CREATE TABLE IF NOT EXISTS cost_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type   TEXT NOT NULL,
    model       TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd    REAL NOT NULL,
    latency_ms  INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 月度预算
CREATE TABLE IF NOT EXISTS monthly_budget (
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    budget_usd  REAL NOT NULL DEFAULT 20.0,
    spent_usd   REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (year, month)
);

-- PAD 历史（Phase B 先建表，Phase C 填充）
CREATE TABLE IF NOT EXISTS pad_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT NOT NULL,
    scene_id    TEXT,
    pleasure    REAL NOT NULL DEFAULT 0.0,
    arousal     REAL NOT NULL DEFAULT 0.0,
    dominance   REAL NOT NULL DEFAULT 0.0,
    computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 分析历史（Phase B 先建表，Phase D 填充）
CREATE TABLE IF NOT EXISTS analysis_history (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    chapter_id  TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    complexity  TEXT NOT NULL,
    agent_count INTEGER NOT NULL,
    total_cost  REAL NOT NULL,
    total_latency_ms INTEGER NOT NULL,
    findings_json TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Phase C/D 再加：`episodic_memory`, `causality_graph`, `foreshadowing_registry`, `permanent_memory`

### 1.4 Cargo.toml 已有依赖

```toml
[dependencies]
xmgl-core = { path = "../xmgl-core" }
rusqlite = { workspace = true }
serde_json = { workspace = true }
chrono = { workspace = true }
```

无需修改。`thiserror` 可选，若需要自定义错误类型再加。

---

## 二、xmgl-project — 项目/章节管理

### 2.1 crate 定位

中间层。封装 `xmgl-memory` 的数据操作，加上业务逻辑（字数统计、旧数据迁移）。

### 2.2 公共 API（计划签名）

```rust
use xmgl_core::{ProjectMeta, ChapterData};
use xmgl_memory;

pub struct ProjectManager {
    db_path: String,
}

impl ProjectManager {
    /// 新建或打开已有数据库。首次调用自动 run migrations。
    pub fn new(db_path: &str) -> Result<Self>;

    // ── 项目管理 ──

    /// 创建新项目，自动生成 UUID
    pub fn create_project(&self, name: &str) -> Result<ProjectMeta>;
    /// 列出所有项目
    pub fn list_projects(&self) -> Result<Vec<ProjectMeta>>;
    /// 获取单个项目
    pub fn get_project(&self, id: &str) -> Result<Option<ProjectMeta>>;
    /// 更新项目元数据
    pub fn update_project(&self, meta: &ProjectMeta) -> Result<()>;
    /// 删除项目及所有关联章节
    pub fn delete_project(&self, id: &str) -> Result<()>;

    // ── 章节管理 ──

    /// 在项目中创建新章节
    pub fn create_chapter(&self, project_id: &str, title: &str, text: &str) -> Result<ChapterData>;
    /// 获取单个章节
    pub fn get_chapter(&self, id: &str) -> Result<Option<ChapterData>>;
    /// 列出项目的所有章节（按 sort_order 排序）
    pub fn list_chapters(&self, project_id: &str) -> Result<Vec<ChapterData>>;
    /// 更新章节（标题、正文、排序）
    pub fn update_chapter(&self, chapter: &ChapterData) -> Result<()>;
    /// 删除章节
    pub fn delete_chapter(&self, id: &str) -> Result<()>;

    // ── 统计 ──

    /// 重新计算项目的 chapter_count 和 total_words
    pub fn recalc_project_stats(&self, project_id: &str) -> Result<()>;

    // ── 旧数据迁移 ──

    /// 从 v3.1 JSON 文件迁移数据（../xmgl_xs/ 目录）
    /// 首次运行时自动检测并迁移，完成后写入 .xmgl_migrated_v4 标记文件
    pub fn migrate_from_v3(&self, v3_project_path: &str) -> Result<MigrationReport>;
}

pub struct MigrationReport {
    pub projects_migrated: u32,
    pub chapters_migrated: u32,
    pub errors: Vec<String>,
}
```

### 2.3 Cargo.toml 已有依赖

```toml
[dependencies]
xmgl-core = { path = "../xmgl-core" }
xmgl-memory = { path = "../xmgl-memory" }
serde_json = { workspace = true }
chrono = { workspace = true }
uuid = { workspace = true }
```

无需修改。

---

## 三、xmgl-python-bridge — Python Sidecar HTTP 客户端

### 3.1 crate 定位

独立层。与 Rust 核心其他部分无依赖（仅依赖 xmgl-core 获取类型）。

### 3.2 公共 API（计划签名）

```rust
use xmgl_core::{TaskType, ModelTier};

pub struct PythonBridge {
    base_url: String,          // "http://localhost:9091"
    client: reqwest::Client,
    health_check_interval: Duration,  // 5s
    restart_on_failure: bool,
}

pub struct LLMCallRequest {
    pub request_id: String,
    pub task_type: TaskType,
    pub system_prompt_key: String,
    pub user_message: String,
    pub response_format: String,      // "json" | "text"
    pub temperature_override: Option<f64>,
    pub max_tokens_override: Option<u32>,
}

pub struct LLMUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub cost_usd: f64,
    pub model: String,
    pub latency_ms: u32,
}

pub struct LLMCallResponse {
    pub request_id: String,
    pub success: bool,
    pub result: Option<serde_json::Value>,
    pub usage: Option<LLMUsage>,
    pub error: Option<String>,
}

pub struct BatchLLMResponse {
    pub results: Vec<LLMCallResponse>,
    pub total_cost_usd: f64,
    pub total_latency_ms: u32,
}

impl PythonBridge {
    /// 创建客户端，默认 base_url = http://localhost:9091
    pub fn new(base_url: Option<&str>) -> Result<Self>;

    /// 健康检查 → GET /v1/llm/health
    /// 返回 (ok, llm_available, model_name)
    pub async fn health_check(&self) -> Result<(bool, bool, String)>;

    /// 单次 LLM 调用 → POST /v1/llm/call
    pub async fn call_llm(&self, req: &LLMCallRequest) -> Result<LLMCallResponse>;

    /// 批量 LLM 调用 → POST /v1/llm/call_batch
    pub async fn call_llm_batch(&self, requests: &[LLMCallRequest], parallel: bool, max_concurrency: u32) -> Result<BatchLLMResponse>;

    /// 渲染 Prompt → POST /v1/prompts/render
    pub async fn render_prompt(&self, prompt_key: &str, variables: &HashMap<String, String>) -> Result<String>;

    /// 语料搜索 → POST /v1/corpus/search
    pub async fn search_corpus(&self, query: &str, top_k: u32) -> Result<Vec<CorpusSlice>>;
}

pub struct CorpusSlice {
    pub slice_id: String,
    pub text: String,
    pub similarity: f64,
    pub metadata: serde_json::Value,
}
```

### 3.3 重试策略

```
超时: 30s（单次 HTTP 调用）
重试: 最多 3 次，指数退避（1s, 2s, 4s）
熔断: 连续 5 次失败 → 返回错误，上层决定是否重启 sidecar
```

### 3.4 Python Sidecar HTTP 契约（已有，不需要改）

| 端点 | 方法 | 请求体 | 响应体 |
|------|------|--------|--------|
| `/v1/llm/health` | GET | — | `{"status":"ok","llm_available":bool,"model":"..."}` |
| `/v1/llm/call` | POST | `LLMCallRequest` | `LLMCallResponse` |
| `/v1/llm/call_batch` | POST | `BatchLLMRequest` | `BatchLLMResponse` |
| `/v1/prompts/render` | POST | `RenderPromptRequest` | `{"result":"..."}` |
| `/v1/corpus/search` | POST | `CorpusSearchRequest` | `{"results":[...]}` |

Python 侧的 Pydantic 模型已在 `src-python/main.py` 完全定义，无需修改。

### 3.5 Cargo.toml 已有依赖

```toml
[dependencies]
xmgl-core = { path = "../xmgl-core" }
reqwest = { workspace = true }
serde_json = { workspace = true }
tokio = { workspace = true }
```

无需修改。

---

## 四、xmgl-tauri — Tauri Commands + Events

### 4.1 crate 定位

最上层胶水层。连接 Tauri IPC 前端请求 → xmgl-project/xmgl-python-bridge。

### 4.2 Tauri IPC 契约（前端 ↔ Rust）

#### Commands（前端 invoke）

| Command | 参数 (TS) | 返回 (TS) | 对应 Rust 函数 |
|---------|----------|----------|---------------|
| `list_projects` | — | `ProjectMeta[]` | `xmgl_tauri::commands::list_projects` |
| `create_project` | `{ name: string }` | `ProjectMeta` | `xmgl_tauri::commands::create_project` |
| `get_project` | `{ id: string }` | `ProjectMeta \| null` | `xmgl_tauri::commands::get_project` |
| `delete_project` | `{ id: string }` | `void` | `xmgl_tauri::commands::delete_project` |
| `list_chapters` | `{ project_id: string }` | `ChapterData[]` | `xmgl_tauri::commands::list_chapters` |
| `create_chapter` | `{ project_id, title, text }` | `ChapterData` | `xmgl_tauri::commands::create_chapter` |
| `get_chapter` | `{ id: string }` | `ChapterData \| null` | `xmgl_tauri::commands::get_chapter` |
| `update_chapter` | `ChapterData` | `void` | `xmgl_tauri::commands::update_chapter` |
| `delete_chapter` | `{ id: string }` | `void` | `xmgl_tauri::commands::delete_chapter` |

#### Events（Rust → 前端推送）

| Event | Payload | 触发时机 |
|-------|---------|---------|
| `agent:progress` | `{ agent_id, agent_name, stage, progress_pct }` | Agent 开始/完成分析阶段 |
| `proposal:ready` | `{ proposal_id, agent_id, title, severity, location }` | 新的修改建议就绪 |
| `analysis:complete` | `{ total_cost, total_latency, agent_count, findings_count }` | 一轮分析完成（成本和耗时汇总） |

### 4.3 公共 API（计划签名）

```rust
use xmgl_project::ProjectManager;
use xmgl_python_bridge::PythonBridge;

// Tauri 命令（每个函数是 #[tauri::command]）
pub mod commands {
    // 项目
    #[tauri::command]
    pub async fn list_projects(state: State<AppState>) -> Result<Vec<ProjectMeta>, String>;
    #[tauri::command]
    pub async fn create_project(state: State<AppState>, name: String) -> Result<ProjectMeta, String>;
    #[tauri::command]
    pub async fn get_project(state: State<AppState>, id: String) -> Result<Option<ProjectMeta>, String>;
    #[tauri::command]
    pub async fn delete_project(state: State<AppState>, id: String) -> Result<(), String>;

    // 章节
    #[tauri::command]
    pub async fn list_chapters(state: State<AppState>, project_id: String) -> Result<Vec<ChapterData>, String>;
    #[tauri::command]
    pub async fn create_chapter(state: State<AppState>, project_id: String, title: String, text: String) -> Result<ChapterData, String>;
    #[tauri::command]
    pub async fn get_chapter(state: State<AppState>, id: String) -> Result<Option<ChapterData>, String>;
    #[tauri::command]
    pub async fn update_chapter(state: State<AppState>, chapter: ChapterData) -> Result<(), String>;
    #[tauri::command]
    pub async fn delete_chapter(state: State<AppState>, id: String) -> Result<(), String>;
}

/// Tauri 管理的全局状态
pub struct AppState {
    pub project_manager: ProjectManager,
    pub python_bridge: PythonBridge,
    // Phase D 再加：
    // pub orchestrator: Orchestrator,
}
```

### 4.4 main.rs 集成方式

```rust
// src-tauri/src/main.rs（Phase B 版本）
use xmgl_tauri::{commands, AppState};
use xmgl_project::ProjectManager;

fn main() {
    // 初始化 ProjectManager（自动创建/迁移 SQLite）
    let project_manager = ProjectManager::new("xmgl.db")
        .expect("无法初始化数据库");

    tauri::Builder::default()
        .manage(AppState {
            project_manager,
            python_bridge: PythonBridge::new(None).expect("无法创建 Python Bridge"),
        })
        .invoke_handler(tauri::generate_handler![
            commands::list_projects,
            commands::create_project,
            commands::get_project,
            commands::delete_project,
            commands::list_chapters,
            commands::create_chapter,
            commands::get_chapter,
            commands::update_chapter,
            commands::delete_chapter,
        ])
        .run(tauri::generate_context!())
        .expect("无法启动 Tauri 应用");
}
```

### 4.5 Cargo.toml 已有依赖

```toml
[dependencies]
xmgl-core = { path = "../xmgl-core" }
xmgl-agent = { path = "../xmgl-agent" }
xmgl-orchestrator = { path = "../xmgl-orchestrator" }
xmgl-project = { path = "../xmgl-project" }
xmgl-memory = { path = "../xmgl-memory" }
tokio = { workspace = true }
serde_json = { workspace = true }
```

需要新增 `tauri` 依赖（用于 `State`, `#[tauri::command]`）：
```toml
tauri = { workspace = true }
```

同时需要在 workspace 层添加 `tauri`（当前仅在根 `[dependencies]` 有，不在 `[workspace.dependencies]` 中）。

---

## 五、前端对接层（`src-frontend/src/api/`）

### 5.1 目录结构

```
src-frontend/src/api/
  index.ts          # 统一导出
  projects.ts       # listProjects, createProject, deleteProject
  chapters.ts       # listChapters, createChapter, getChapter, updateChapter, deleteChapter
  events.ts         # Tauri event listeners (agent:progress, proposal:ready, analysis:complete)
```

### 5.2 invoke 签名（TypeScript）

```typescript
// api/projects.ts
import { invoke } from '@tauri-apps/api/core';
import type { ProjectMeta } from '../types';

export async function listProjects(): Promise<ProjectMeta[]> {
    return invoke('list_projects');
}
export async function createProject(name: string): Promise<ProjectMeta> {
    return invoke('create_project', { name });
}
export async function deleteProject(id: string): Promise<void> {
    return invoke('delete_project', { id });
}

// api/chapters.ts
import { invoke } from '@tauri-apps/api/core';
import type { ChapterData } from '../types';

export async function listChapters(projectId: string): Promise<ChapterData[]> {
    return invoke('list_chapters', { projectId });
}
export async function createChapter(projectId: string, title: string, text: string): Promise<ChapterData> {
    return invoke('create_chapter', { projectId, title, text });
}
export async function getChapter(id: string): Promise<ChapterData | null> {
    return invoke('get_chapter', { id });
}
export async function updateChapter(chapter: ChapterData): Promise<void> {
    return invoke('update_chapter', { chapter });
}
export async function deleteChapter(id: string): Promise<void> {
    return invoke('delete_chapter', { id });
}

// api/events.ts
import { listen } from '@tauri-apps/api/event';
import type { UnlistenFn } from '@tauri-apps/api/event';

interface AgentProgress { agent_id: string; agent_name: string; stage: string; progress_pct: number; }
interface ProposalReady { proposal_id: string; agent_id: string; title: string; severity: string; location?: TextRange; }
interface AnalysisComplete { total_cost: number; total_latency: number; agent_count: number; findings_count: number; }

export function onAgentProgress(cb: (p: AgentProgress) => void): Promise<UnlistenFn> {
    return listen('agent:progress', (event) => cb(event.payload as AgentProgress));
}
export function onProposalReady(cb: (p: ProposalReady) => void): Promise<UnlistenFn> {
    return listen('proposal:ready', (event) => cb(event.payload as ProposalReady));
}
export function onAnalysisComplete(cb: (p: AnalysisComplete) => void): Promise<UnlistenFn> {
    return listen('analysis:complete', (event) => cb(event.payload as AnalysisComplete));
}
```

### 5.3 Store 扩展

Zustand store 需要新增：

```typescript
// store/index.ts 新增字段
interface AppState {
    // ... 现有字段 ...
    // Phase B 新增：
    projects: ProjectMeta[];           // 项目列表
    currentChapters: ChapterData[];    // 当前项目的章节
    analysisStatus: 'idle' | 'running' | 'done';
    lastAnalysisResult?: AnalysisComplete;
}
```

---

## 六、sqlx 依赖决定（Phase B 第一个决定）

`xmgl-memory` 需要选择一个 SQLite 库风格。Workspace 已有 `rusqlite`：

| 方案 | 优点 | 缺点 |
|------|------|------|
| **rusqlite** (已安装) | 同步 API，零额外依赖，与 tokio 配合 `spawn_blocking` | 需手写 SQL |
| sqlx | 编译期 SQL 检查，async-native | 新增依赖，需要 `sqlx::query!` 宏需要 DATABASE_URL |
| sea-orm | 最高级抽象 | 太重，不适合嵌入式场景 |

**建议选 rusqlite**，原因：
- workspace 已安装，不新增依赖
- SQLite 嵌入式场景，`spawn_blocking` 足够
- 11 张表的 SQL 手写可控

> 具体选择由维护者决定。实现时先按 rusqlite 写。

---

## 七、实现顺序（推荐）

```
Phase B 第1步: xmgl-memory
  ├── 1a. init_db() + run_migrations()（7 张表）
  ├── 1b. 项目/章节基础 CRUD（insert/list/get/update/delete）
  └── 1c. 单元测试

Phase B 第2步: xmgl-project
  ├── 2a. ProjectManager（new, create/list/get/update/delete）
  ├── 2b. 章节管理（create/list/get/update/delete + recalc_stats）
  ├── 2c. 旧数据迁移（migrate_from_v3）
  └── 2d. 单元测试

Phase B 第3步: xmgl-python-bridge
  ├── 3a. PythonBridge（new, health_check, call_llm）
  ├── 3b. 重试 + 超时 + 熔断
  └── 3c. 集成测试（需要 Python sidecar 运行）

Phase B 第4步: xmgl-tauri
  ├── 4a. AppState + 9 个 Tauri commands
  ├── 4b. main.rs 集成（uncomment use xmgl_tauri）
  ├── 4c. 前端 api/ 目录（invoke 包装器）
  └── 4d. 端到端：前端按钮 → Tauri command → SQLite
```

每一步完成后 `cargo test --workspace` 必须通过。

---

## 八、xmgl-core 已有类型（不需改）

以下类型已在 `xmgl-core::lib.rs` 完整定义，Phase B 直接引用：

| 类型 | 用途 | 关键字段 |
|------|------|---------|
| `ProjectMeta` | 项目元数据 | id, name, created_at, updated_at, chapter_count, total_words |
| `ChapterData` | 章节数据 | id, project_id, title, text, word_count, created_at, updated_at |
| `TaskType` | 任务类型枚举 | 17 个变体 + as_str() |
| `ModelTier` | 模型级别 | RuleOnly, Flash, Pro |
| `PADState` | PAD 三维情感 | pleasure, arousal, dominance（默认 0.0） |
| `AgentId` | Agent 标识 | 9 个变体 + all() + name() |
| `TextRange` | 文本位置 | start_line/column, end_line/column, start_byte, end_byte |
| `Severity` | 严重级别 | Info, Warn, Critical |

全部 `#[derive(Debug, Clone, Serialize, Deserialize)]`，可直接序列化传 IPC。

---

## 九、与 Python Sidecar 的对接

Phase B 只需确保 xmgl-python-bridge 能调通 health check。LLM 实际调用等到 Phase D/E。

验证命令：
```bash
# 终端 1：启动 sidecar
cd src-python && python main.py
# 终端 2：验证
curl http://localhost:9091/v1/llm/health
# → {"status":"ok","llm_available":false,"model":"gpt-4o-mini"}
```

`llm_available: false` 是正常的 — 没配 API key。Phase D 配好 key 后变为 `true`。

---

## 十、检查清单

- [ ] xmgl-memory: `init_db()` + `run_migrations()` 建 7 张表
- [ ] xmgl-memory: 项目/章节 CRUD 函数
- [ ] xmgl-memory: 成本日志 `log_cost()` + `get_monthly_cost()`
- [ ] xmgl-project: `ProjectManager` struct + 所有方法
- [ ] xmgl-project: `migrate_from_v3()` 旧数据迁移
- [ ] xmgl-python-bridge: `PythonBridge` + health check + LLM call
- [ ] xmgl-python-bridge: 重试/超时/熔断
- [ ] xmgl-tauri: `AppState` + 9 个 Tauri commands
- [ ] xmgl-tauri: `main.rs` 注册命令 + 管理状态
- [ ] xmgl-tauri: 事件系统（emit agent:progress 等）
- [ ] 前端 `api/` 目录：projects.ts, chapters.ts, events.ts
- [ ] 前端 Store 扩展：projects, chapters, analysisStatus
- [ ] `cargo test --workspace` 每个 crate 有测试
- [ ] `cargo tauri dev` 窗口弹出
- [ ] 手动验证：前端按钮 → SQLite 读写
