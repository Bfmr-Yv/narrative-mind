---
name: agent-impl
description: Implement a new Agent following the Narrative Mind v4.0 Agent trait pattern. Trigger when user mentions "实现Agent"、"新增Agent"、"implement agent"、"add agent".
---

# Agent 实现向导

在 `xmgl-agent` crate 中新增 Agent 实现，遵循 9 Agent 系统规范。

## Agent 清单（9 个）

| # | Agent | AgentId 枚举 | 模型级别 | 分析镜头 |
|---|-------|-------------|---------|---------|
| 1 | 角色 Agent | `Character` | Pro | PAD三维情感、行为模式一致性 |
| 2 | 世界 Agent | `World` | Flash | 规则校验、空间一致性、力量体系 |
| 3 | 叙事 Agent | `Narrative` | Pro | 伏笔生命周期、因果链、情节节奏 |
| 4 | 文辞 Agent | `Prose` | Flash | 句长/语域/修辞、角色对话风格 |
| 5 | 主题 Agent | `Theme` | Pro | 主题提取+强度追踪 |
| 6 | 经济 Agent | `Economy` | Flash | 资源流动校验 |
| 7 | 预期 Agent | `Expectation` | Flash | 读者信息差建模 |
| 8 | 构思 Agent | `Conception` | Flash | 意象注册+演变追踪 |
| 9 | 总编 Agent | `EditorInChief` | Pro | 冲突裁决、优先级排序 |

## Agent Trait 签名（参考 `xmgl-agent/src/lib.rs`）

```rust
#[async_trait]
pub trait Agent: Send + Sync {
    fn id(&self) -> AgentId;
    fn name(&self) -> &'static str;
    fn lens(&self) -> AgentLens;
    fn model_tier(&self) -> ModelTier;

    async fn probe(&self, ctx: &SharedContext, chapter: &Chapter) -> Result<AgentProbe>;
    async fn analyze(&self, ctx: &SharedContext, chapter: &Chapter, probe: &AgentProbe) -> Result<Vec<Finding>>;
    async fn suggest(&self, ctx: &SharedContext, finding: &Finding) -> Result<Option<EditProposal>>;
}
```

## 新增 Agent 文件模板

```rust
//! xmgl-agent — <Name> Agent
//!
//! 分析镜头：<分析维度>
//! 模型级别：<Pro | Flash>

use async_trait::async_trait;
use xmgl_core::prelude::*;
use crate::{Agent, AgentId, AgentLens, AgentProbe, ModelTier, SharedContext, Finding, EditProposal};

pub struct <Name>Agent {
    // 可选：Agent 私有状态
}

impl <Name>Agent {
    pub fn new() -> Self {
        Self {}
    }
}

#[async_trait]
impl Agent for <Name>Agent {
    fn id(&self) -> AgentId { AgentId::<Name> }
    fn name(&self) -> &'static str { "<中文名> Agent" }
    fn lens(&self) -> AgentLens { AgentLens::<Name> }
    fn model_tier(&self) -> ModelTier { ModelTier::<Pro|Flash> }

    async fn probe(&self, ctx: &SharedContext, chapter: &Chapter) -> Result<AgentProbe> {
        todo!("实现探测逻辑")
    }

    async fn analyze(&self, ctx: &SharedContext, chapter: &Chapter, probe: &AgentProbe) -> Result<Vec<Finding>> {
        todo!("实现分析逻辑")
    }

    async fn suggest(&self, ctx: &SharedContext, finding: &Finding) -> Result<Option<EditProposal>> {
        todo!("实现建议生成逻辑")
    }
}
```

## 注册清单（5 处同步）

1. [ ] `xmgl-core/src/lib.rs` — `AgentId` 枚举添加变体
2. [ ] `xmgl-core/src/lib.rs` — `AgentLens` 枚举添加变体
3. [ ] `xmgl-agent/src/lib.rs` — `AgentRegistry` 注册新 Agent
4. [ ] `CLAUDE.md` — 9 Agent 表更新状态
5. [ ] `src-python/prompts/` — 添加对应 System Prompt + format 函数

## 检查命令

```bash
# 验证新 Agent 编译通过
cd src-tauri
cargo check -p xmgl-agent

# 验证 AgentId 枚举包含新变体
grep -n "AgentId" src-tauri/crates/xmgl-core/src/lib.rs

# 验证 AgentRegistry 已注册
grep -n "<Name>Agent" src-tauri/crates/xmgl-agent/src/lib.rs
```
