# Narrative Mind v4.0 — 短期开发计划

> **状态**: 待开发者执行
> **创建**: 2026-06-16
> **范围**: 完成 Phase A 脚手架（当前 ~20% → 100%）
> **预计工作量**: 2-3 个会话

---

## Phase A 完成标准

```
Rust ↔ Python 健康检查通过
  │
  ├── cd src-tauri && cargo check  # 全 workspace 编译通过
  ├── cd src-python && python main.py  # FastAPI 启动无 import 错误
  ├── curl localhost:9091/v1/llm/health  # 返回 {"status":"ok"}
  └── cd src-frontend && npm run dev  # 前端 localhost:1420 可访问
```

---

## 任务列表

### T1: 修复 `xmgl-core` Cargo.toml 依赖

**问题**: `lib.rs` 用了 `use serde::{Deserialize, Serialize}` 但 Cargo.toml 的 `[dependencies]` 为空。

```toml
# src-tauri/crates/xmgl-core/Cargo.toml
[dependencies]
serde.workspace = true
```

**验证**: `cargo check -p xmgl-core`

---

### T2: 创建 Python `llm/config.py`

**问题**: `llm/__init__.py` import `LLMConfig` 和 `get_config` 但文件不存在。

**内容**:
- `LLMConfig` dataclass（provider, api_key, base_url, model, max_tokens, temperature）
- `get_config()` 函数：从 `config/llm.json` 或环境变量读取配置
- 支持 DeepSeek 和 OpenAI 两种 provider

**参考**: 旧 `../xmgl_xs/src/llm/config.py`

**验证**: `python -c "from llm.config import get_config; print(get_config())"`

---

### T3: 创建 Python `llm/client.py`

**问题**: `llm/__init__.py` import `LLMClient` 和 `get_client` 但文件不存在。

**内容**:
- `LLMClient` 类：封装 OpenAI SDK
- `get_client()` 工厂函数：根据 config 创建 client 实例
- `call()` 方法：调 LLM 并返回 `(response_text, usage_stats)`
- 使用环境变量 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` 认证

**参考**: 旧 `../xmgl_xs/src/llm/client.py`（166行）

**验证**: `python -c "from llm.client import get_client; print('ok')"`

---

### T4: 创建 Python `prompts/registry.py`

**问题**: `prompts/__init__.py` 为空，`main.py` 引用了不存在的 `PROMPT_REGISTRY`。

**内容**:
- `PROMPT_REGISTRY: dict[str, PromptTemplate]` 字典
- `PromptTemplate` dataclass（key, name, description, system_prompt, format_fn）
- 先移植 2 个基础 prompt（从旧 `../xmgl_xs/src/llm/prompts.py`）：
  - `pad_compute` — PAD 情感计算
  - `entity_extract` — 实体提取
- 其余 15 个可留占位 stub，在 Phase F 再补齐

**验证**: `python -c "from prompts.registry import PROMPT_REGISTRY; print(list(PROMPT_REGISTRY.keys()))"`

---

### T5: 创建 Python `corpus/` 子模块

**问题**: `corpus/__init__.py` 为空，`main.py` import `SliceManager`/`Retriever`/`Embedder` 失败。

**最小实现**（支架即可，Phase F 再完整移植）:
- `corpus/slice_manager.py`: `SliceManager` 类（存根，`search()` 返回空列表）
- `corpus/retriever.py`: `Retriever` 类（存根）
- `corpus/embedder.py`: `Embedder` 类（存根）

**验证**: `python -c "from corpus.slice_manager import SliceManager; print('ok')"`

---

### T6: 补全所有 crate 的 `[dependencies]`

**问题**: 所有 7 个 crate 的 Cargo.toml 都只有空 `[dependencies]`，需要声明 crate 间依赖。

```
xmgl-core:     serde
xmgl-agent:    xmgl-core, async-trait, tokio
xmgl-orchestrator: xmgl-core, xmgl-agent, xmgl-memory, xmgl-python-bridge, tokio, async-trait
xmgl-memory:   xmgl-core, rusqlite, serde_json, chrono
xmgl-project:  xmgl-core, xmgl-memory, serde_json, chrono, uuid
xmgl-python-bridge: xmgl-core, reqwest, serde_json, tokio
xmgl-tauri:    xmgl-core, xmgl-agent, xmgl-orchestrator, xmgl-project, xmgl-memory, tokio, serde_json
```

**验证**: `cargo check --workspace` 全部通过

---

### T7: 验证 Python sidecar 可启动

全部子模块 stub 就位后，确保 `python main.py` 启动不报 import 错误，健康检查端点返回正确。

**验证**:
```bash
cd src-python
python main.py &
sleep 2
curl localhost:9091/v1/llm/health
```

---

### T8: 将占位 `add` 函数替换为 crate 文档

6 个 crate 的 `lib.rs` 目前是默认的 `pub fn add(...)`。替换为 crate 级文档注释：

```rust
//! xmgl-{name} — {职责描述}
//! 
//! 本 crate 实现{具体功能}。
//! Phase B 开始填充实现。
```

**验证**: 每个 crate 有清晰的文档说明

---

## 执行顺序

```
T1 (xmgl-core dep) ──────────────────────────────────────────┐
T2 (llm/config.py) ── T3 (llm/client.py) ──┐                  │
T4 (prompts/registry.py) ──────────────────┤                  │
T5 (corpus/ stubs) ────────────────────────┤                  │
                                            ├── T7 (验证启动)  │
T6 (crate deps) ───────────────────────────┘                  │
T8 (lib.rs 文档) ──────────────────────────────────────────────┘
                                                               │
                                                         全部通过
                                                               │
                                                         Phase A ✓
```

T1-T6 可并行执行（互不依赖），T7 在所有 Python 子模块完成后验证，T8 收尾。

---

## 不做的事（留给后续 Phase）

- ❌ 不实现 Agent trait（Phase C）
- ❌ 不创建 SQLite schema（Phase B）
- ❌ 不写 Tauri commands（Phase B）
- ❌ 不创建 Monaco 装饰系统（Phase E）
- ❌ 不移植所有 17 个 prompts（只移植 2 个做支架验证）
- ❌ 不创建 tauri.conf.json（Phase B 再处理）
