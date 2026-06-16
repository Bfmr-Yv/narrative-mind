//! xmgl-python-bridge — Python Sidecar HTTP 客户端
//!
//! 本 crate 实现 Rust ↔ Python 通信：
//! - HTTP 客户端（reqwest）调用 Python FastAPI sidecar
//! - `/v1/llm/call` — 单次 LLM 调用
//! - `/v1/llm/call_batch` — 批量 LLM 调用
//! - `/v1/prompts/render` — Prompt 模板渲染
//! - `/v1/corpus/search` — 语料检索
//! - 健康检查 + 重试 + 超时（30s fallback）
//!
//! Phase B 开始填充实现。
