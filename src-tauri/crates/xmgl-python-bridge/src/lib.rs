//! xmgl-python-bridge — Python Sidecar HTTP 客户端
//!
//! 本 crate 实现 Rust ↔ Python 通信：
//! - HTTP 客户端（reqwest）调用 Python FastAPI sidecar（localhost:9091）
//! - `/v1/llm/call` — 单次 LLM 调用
//! - `/v1/llm/call_batch` — 批量 LLM 调用
//! - `/v1/prompts/render` — Prompt 模板渲染
//! - `/v1/corpus/search` — 语料检索
//! - 健康检查 + 重试（指数退避）+ 超时（30s）
//!
//! # Phase B 实现计划
//!
//! ## 核心结构
//! ```ignore
//! pub struct PythonBridge {
//!     base_url: String,               // "http://localhost:9091"
//!     client: reqwest::Client,
//!     health_check_interval: Duration, // 5s
//!     restart_on_failure: bool,
//! }
//!
//! pub struct LLMCallRequest {
//!     pub request_id: String,
//!     pub task_type: TaskType,
//!     pub system_prompt_key: String,
//!     pub user_message: String,
//!     pub response_format: String,      // "json" | "text"
//!     pub temperature_override: Option<f64>,
//!     pub max_tokens_override: Option<u32>,
//! }
//!
//! pub struct LLMUsage {
//!     pub input_tokens: u32,
//!     pub output_tokens: u32,
//!     pub cost_usd: f64,
//!     pub model: String,
//!     pub latency_ms: u32,
//! }
//!
//! pub struct LLMCallResponse {
//!     pub request_id: String,
//!     pub success: bool,
//!     pub result: Option<serde_json::Value>,
//!     pub usage: Option<LLMUsage>,
//!     pub error: Option<String>,
//! }
//!
//! pub struct BatchLLMResponse {
//!     pub results: Vec<LLMCallResponse>,
//!     pub total_cost_usd: f64,
//!     pub total_latency_ms: u32,
//! }
//! ```
//!
//! ## PythonBridge 方法
//! ```ignore
//! impl PythonBridge {
//!     pub fn new(base_url: Option<&str>) -> Result<Self>;
//!     pub async fn health_check(&self) -> Result<(bool, bool, String)>;
//!     pub async fn call_llm(&self, req: &LLMCallRequest) -> Result<LLMCallResponse>;
//!     pub async fn call_llm_batch(&self, requests: &[LLMCallRequest], parallel: bool, max_concurrency: u32) -> Result<BatchLLMResponse>;
//!     pub async fn render_prompt(&self, prompt_key: &str, variables: &HashMap<String, String>) -> Result<String>;
//!     pub async fn search_corpus(&self, query: &str, top_k: u32) -> Result<Vec<CorpusSlice>>;
//! }
//! ```
//!
//! ## 重试策略
//! - 超时 30s（单次 HTTP 调用）
//! - 最多重试 3 次，指数退避（1s → 2s → 4s）
//! - 连续 5 次失败 → 返回错误，由上层决定是否重启 sidecar
//!
//! ## Python Sidecar HTTP 契约（已存在，不需要改）
//! | 端点 | 方法 | 说明 |
//! |------|------|------|
//! | `/v1/llm/health` | GET | 健康检查 + 成本状态 |
//! | `/v1/llm/call` | POST | 单次 LLM 调用 |
//! | `/v1/llm/call_batch` | POST | 批量 LLM 调用 |
//! | `/v1/prompts/render` | POST | 渲染 Prompt 模板 |
//! | `/v1/corpus/search` | POST | 语料向量检索 |
//!
//! Python 侧 Pydantic 模型见 `src-python/main.py`。
//! 详细接口规格见 `docs/PHASE-B-INTERFACES.md`

#[cfg(test)]
mod tests {
    #[test]
    fn it_compiles() {
        assert!(true);
    }
}
