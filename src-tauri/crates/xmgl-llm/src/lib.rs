//! xmgl-llm — Rust 原生 LLM 调用层
//!
//! Phase K: 替代 Python sidecar，通过 reqwest 直接调用 OpenAI-compatible API。
//!
//! 模块:
//! - `config`: Provider 检测、API Key 解析、Tier 路由表、成本常量
//! - `prompts`: 17 个 System Prompt + 格式化函数 + PROMPT_REGISTRY
//! - `client`: LlmClientImpl (reqwest Client + 重试 + JSON 解析)

mod config;
mod prompts;
mod client;

pub use client::LlmClientImpl;
pub use config::{LlmConfig, TierRoute, tier_route};
