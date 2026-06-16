---
name: crate-scaffold
description: Scaffold new Rust crates in the workspace following Narrative Mind v4.0 conventions. Trigger when user mentions "新建crate"、"添加crate"、"create crate"、"scaffold crate".
---

# Crate 脚手架

在 `src-tauri/crates/` 下创建新的 Rust crate，自动补齐所有 wiring。

## 项目结构约定

```
src-tauri/crates/<name>/
├── Cargo.toml          # workspace member，依赖 xmgl-core
└── src/
    └── lib.rs          # 公开 API，re-export 主要类型
```

## Cargo.toml 模板

```toml
[package]
name = "xmgl-<name>"
version.workspace = true
edition.workspace = true
description = "<一句话描述>"

[dependencies]
xmgl-core.workspace = true
serde.workspace = true
tokio.workspace = true
```

Workspace 依赖项统一从 `src-tauri/Cargo.toml` 的 `[workspace.dependencies]` 继承。

## lib.rs 模板

```rust
//! xmgl-<name> — <一句话描述>
//!
//! 职责：<具体职责>

pub mod error;
pub mod types;

use xmgl_core::prelude::*;

/// <Name> 的主要入口类型
pub struct <Name>Manager {
    // TODO: 添加字段
}

impl <Name>Manager {
    pub fn new() -> Self {
        Self {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_new() {
        let manager = <Name>Manager::new();
    }
}
```

## 注册清单

创建 crate 后，必须完成以下注册（4 处）：

1. [ ] `src-tauri/Cargo.toml` — `[workspace.members]` 添加 `"crates/xmgl-<name>"`
2. [ ] `CLAUDE.md` — Rust Crates 表添加一行（crate 名 + 职责 + 关键类型）
3. [ ] `docs/ARCHITECTURE-2026-06-16.md` — 如果改变了架构假设
4. [ ] `.claude/skills/` — 如果 crate 需要专属 skill

## 命名约定

- Crate 名：`xmgl-<kebab-case>` (e.g., `xmgl-python-bridge`)
- Rust 模块：`snake_case`
- Rust 类型：`PascalCase`
- API JSON 字段：`snake_case`

## 检查命令

```bash
# 验证 crate 是否被 workspace 识别
cd src-tauri
cargo check -p xmgl-<name>

# 验证命名一致性
echo "xmgl-<name>" | grep -E "^xmgl-[a-z][a-z0-9-]*$"
```
