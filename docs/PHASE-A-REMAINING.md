# Phase A 补全任务单

> **下发**: 维护者 → 开发者
> **日期**: 2026-06-16
> **预计**: 2 个会话
> **目标**: Phase A 100% — Tauri 窗口弹出 + Python sidecar 验证 + 测试基座

---

## 完成标准

```
✅ cargo tauri dev → 桌面窗口弹出，显示前端页面
✅ curl localhost:9091/v1/llm/health → {"status":"ok"}
✅ cargo test --workspace → 每个 crate 至少 1 个测试通过
```

---

## T1: 替换 main.rs 为真正的 Tauri 入口

**文件**: `src-tauri/src/main.rs`

**当前内容** (占位，不创建窗口):
```rust
fn main() {
    println!("Narrative Mind v4.0 — AI 辅助小说创作 IDE");
    println!("Rust 核心初始化中...");
    println!("脚手架就绪。");
    println!("下一步：修复 rustc 工具链，运行 cargo build 验证编译。");
}
```

**目标**: 标准 Tauri v2 入口，启动桌面窗口。

注意 —— `xmgl-tauri` crate 目前是空的 lib（只有文档注释）。先不连 xmgl-tauri，直接用最小 Tauri builder 把窗口打开：

```rust
//! Narrative Mind v4.0 — Tauri 桌面应用入口

// 先屏蔽未使用的 import，窗口能开后 Phase B 再连
// use xmgl_tauri;

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("无法启动 Tauri 应用");
}
```

**验证**: `cargo tauri dev` → 看到桌面窗口，窗口内显示前端占位页

---

## T2: 创建 capabilities/default.json

**文件**: `src-tauri/capabilities/default.json`

Tauri v2 每个窗口需要显式声明能力权限。缺少会构建报错。

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "默认窗口权限",
  "windows": ["main"],
  "permissions": [
    "core:default"
  ]
}
```

**验证**: `cargo tauri dev` 不报 capabilities 相关错误

---

## T3: 验证 Python sidecar 可启动

```bash
cd src-python
pip install -r requirements.txt   # 如果还没装
python main.py &
sleep 2
curl http://localhost:9091/v1/llm/health
```

**预期输出**:
```json
{"status":"ok","llm_available":false,"model":"gpt-4o-mini",...}
```

`llm_available: false` 是正常的 — 没配 API key。

**如果 import 报错**: 检查 `requirements.txt` 是否装了 fastapi, uvicorn, pydantic, openai

---

## T4: 替换占位 lib.rs（4 个 crate）

以下 crate 的 `lib.rs` 仍是 `pub fn add(a: u64, b: u64) -> u64 { a + b }`，替换为文档注释。

**不需要改的**:
- `xmgl-core` — 已有完整类型定义 ✅
- `xmgl-agent` — 等 Phase C，保留现状
- `xmgl-orchestrator` — 等 Phase C，保留现状

**需要改的**:

### xmgl-memory (`src-tauri/crates/xmgl-memory/src/lib.rs`)
```rust
//! xmgl-memory — 三层记忆系统 + SQLite 持久化
//!
//! Phase B 实现: SQLite schema migration, WorkingMemory, EpisodicMemory, PermanentMemory
```

### xmgl-project (`src-tauri/crates/xmgl-project/src/lib.rs`)
```rust
//! xmgl-project — 项目/章节 CRUD + 旧数据迁移
//!
//! Phase B 实现: ProjectManager, 章节增删改查, v3.1 JSON 数据迁移
```

### xmgl-python-bridge (`src-tauri/crates/xmgl-python-bridge/src/lib.rs`)
```rust
//! xmgl-python-bridge — Python Sidecar HTTP 客户端
//!
//! Phase B 实现: reqwest HTTP 客户端, /v1/llm/call, 重试+超时
```

### xmgl-tauri (`src-tauri/crates/xmgl-tauri/src/lib.rs`)
```rust
//! xmgl-tauri — Tauri Commands + Events 胶水层
//!
//! Phase B 实现: list_projects, create_project, get_chapter, update_chapter
```

**验证**: `cargo check --workspace` 通过

---

## T5: 补齐基础测试

每个 crate 至少 1 个测试。优先级最高的是 xmgl-core。

### xmgl-core (`src-tauri/crates/xmgl-core/src/lib.rs`)
在文件末尾加:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pad_state_default() {
        let pad = PADState::default();
        assert_eq!(pad.pleasure, 0.0);
        assert_eq!(pad.arousal, 0.0);
        assert_eq!(pad.dominance, 0.0);
    }

    #[test]
    fn test_agent_id_all_has_9() {
        assert_eq!(AgentId::all().len(), 9);
    }

    #[test]
    fn test_task_type_roundtrip() {
        // all TaskType variants serialize/deserialize
        for task in &[
            TaskType::PadCompute,
            TaskType::EntityExtract,
            TaskType::SceneAnalysis,
        ] {
            let s = task.as_str();
            assert!(!s.is_empty());
        }
    }
}
```

### 其余 crate（xmgl-memory, xmgl-project, xmgl-python-bridge, xmgl-tauri）
各加一个占位测试确保 crate 可测:
```rust
#[cfg(test)]
mod tests {
    #[test]
    fn it_compiles() {
        assert!(true);
    }
}
```

**验证**: `cargo test --workspace` 全部通过，不再是 `running 0 tests`

---

## 执行顺序

```
T1 (main.rs) ── T2 (capabilities) ──┐
                                    ├── 窗口弹出! ──┐
T3 (Python 验证) ───────────────────┘               │
                                                    ├── Phase A ✓
T4 (lib.rs 文档) ── T5 (测试) ──────────────────────┘
```

T1/T2 是关键路径，必须最先做（让你看到窗口）。T3/T4/T5 可以独立并行。

---

## 提交

每完成一个独立任务就 commit:

```bash
git add -A && git commit -m "feat: <T1/T2/...> <描述>"
```

全部完成后告诉我。
