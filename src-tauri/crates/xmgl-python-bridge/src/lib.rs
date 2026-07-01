//! xmgl-python-bridge — Python Sidecar HTTP 客户端
//!
//! Phase B: HTTP 客户端、请求/响应类型、重试逻辑、健康检查。

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;
use xmgl_core::{CoreError, CoreResult, TaskType};

// =========================================================================
// 默认配置常量
// =========================================================================

const DEFAULT_BASE_URL: &str = "http://localhost:9091";
const DEFAULT_TIMEOUT_SECS: u64 = 30;
const DEFAULT_HEALTH_CHECK_INTERVAL_SECS: u64 = 5;
const MAX_RETRIES: u32 = 3;
const CONSECUTIVE_FAILURE_LIMIT: u32 = 5;

// =========================================================================
// 请求/响应类型
// =========================================================================

/// 单次 LLM 调用请求。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMCallRequest {
    pub request_id: String,
    pub task_type: TaskType,
    pub system_prompt_key: String,
    pub user_message: String,
    #[serde(default = "default_response_format")]
    pub response_format: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature_override: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens_override: Option<u32>,
}

fn default_response_format() -> String {
    "json".into()
}

/// LLM 调用用量统计。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub cost_usd: f64,
    pub model: String,
    pub latency_ms: u32,
}

/// 单次 LLM 调用响应。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMCallResponse {
    pub request_id: String,
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usage: Option<LLMUsage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// 批量 LLM 调用响应。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchLLMResponse {
    pub results: Vec<LLMCallResponse>,
    pub total_cost_usd: f64,
    pub total_latency_ms: u32,
}

/// 语料切片（语料检索返回）。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorpusSlice {
    pub slice_id: String,
    pub text: String,
    pub source_chapter_id: String,
    pub similarity_score: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, String>>,
}

/// 健康检查响应（对齐 Python `/v1/llm/health` 返回格式）。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    #[serde(default)]
    pub llm_available: bool,
    #[serde(default)]
    pub model: String,
}

// =========================================================================
// PythonBridge
// =========================================================================

/// Python Sidecar HTTP 客户端。
///
/// 封装所有 Python sidecar HTTP 调用，含自动重试和健康检查。
pub struct PythonBridge {
    base_url: String,
    client: Client,
    health_check_interval: Duration,
    restart_on_failure: bool,
    consecutive_failures: u32,
}

impl PythonBridge {
    /// 创建新的 PythonBridge。
    ///
    /// `base_url` 为 `None` 时使用默认 `http://localhost:9091`。
    pub fn new(base_url: Option<&str>) -> CoreResult<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(DEFAULT_TIMEOUT_SECS))
            .build()
            .map_err(|e| CoreError::Internal(format!("failed to create HTTP client: {e}")))?;

        Ok(Self {
            base_url: base_url.unwrap_or(DEFAULT_BASE_URL).trim_end_matches('/').to_string(),
            client,
            health_check_interval: Duration::from_secs(DEFAULT_HEALTH_CHECK_INTERVAL_SECS),
            restart_on_failure: false,
            consecutive_failures: 0,
        })
    }

    /// 设置是否在连续失败后尝试重启 sidecar（Phase D 实现实际重启逻辑）。
    pub fn set_restart_on_failure(&mut self, enabled: bool) {
        self.restart_on_failure = enabled;
    }

    /// 设置 health check 间隔。
    pub fn set_health_check_interval(&mut self, secs: u64) {
        self.health_check_interval = Duration::from_secs(secs);
    }

    /// 获取连续失败计数。
    pub fn consecutive_failures(&self) -> u32 {
        self.consecutive_failures
    }

    /// 健康检查。
    ///
    /// 返回 `(ok, llm_available, model)`。
    pub async fn health_check(&mut self) -> CoreResult<(bool, bool, String)> {
        let url = format!("{}/v1/llm/health", self.base_url);

        match self.client.get(&url).send().await {
            Ok(resp) => {
                if resp.status().is_success() {
                    self.consecutive_failures = 0;
                    if let Ok(body) = resp.json::<HealthStatus>().await {
                        let ok = body.status == "ok";
                        let llm_available = body.llm_available;
                        let model = body.model;
                        return Ok((ok, llm_available, model));
                    }
                    // 解析失败也视为 OK
                    Ok((true, false, "unknown".into()))
                } else {
                    self.record_failure();
                    Ok((false, false, "unknown".into()))
                }
            }
            Err(e) => {
                self.record_failure();
                Err(CoreError::Internal(format!("health check failed: {e}")))
            }
        }
    }

    /// 单次 LLM 调用。
    ///
    /// 含自动重试（3 次，指数退避 1s → 2s → 4s）。
    pub async fn call_llm(&mut self, req: &LLMCallRequest) -> CoreResult<LLMCallResponse> {
        let url = format!("{}/v1/llm/call", self.base_url);
        let body = serde_json::to_value(req)
            .map_err(|e| CoreError::Internal(format!("serialize LLMCallRequest: {e}")))?;

        let result = self.post_with_retry(&url, &body).await?;

        let response: LLMCallResponse = serde_json::from_value(result)
            .map_err(|e| CoreError::Internal(format!("deserialize LLMCallResponse: {e}")))?;

        Ok(response)
    }

    /// 批量 LLM 调用。
    ///
    /// 参数：
    /// - `parallel`: `true` 时 Python 端并发执行
    /// - `max_concurrency`: 最大并发数
    pub async fn call_llm_batch(
        &mut self,
        requests: &[LLMCallRequest],
        parallel: bool,
        max_concurrency: u32,
    ) -> CoreResult<BatchLLMResponse> {
        let url = format!("{}/v1/llm/call_batch", self.base_url);

        let body = serde_json::json!({
            "requests": requests,
            "parallel": parallel,
            "max_concurrency": max_concurrency,
        });

        let result = self.post_with_retry(&url, &body).await?;

        let response: BatchLLMResponse = serde_json::from_value(result)
            .map_err(|e| CoreError::Internal(format!("deserialize BatchLLMResponse: {e}")))?;

        Ok(response)
    }

    /// 渲染 Prompt 模板。
    ///
    /// `variables` 为模板变量键值对。
    pub async fn render_prompt(
        &mut self,
        prompt_key: &str,
        variables: &HashMap<String, String>,
    ) -> CoreResult<String> {
        let url = format!("{}/v1/prompts/render", self.base_url);

        let body = serde_json::json!({
            "prompt_key": prompt_key,
            "variables": variables,
        });

        let result = self.post_with_retry(&url, &body).await?;

        result
            .get("user_message")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| CoreError::Internal("missing 'user_message' field in prompt response".into()))
    }

    /// 语料检索。
    ///
    /// `top_k` 控制返回的最大切片数。
    pub async fn search_corpus(
        &mut self,
        query: &str,
        top_k: u32,
    ) -> CoreResult<Vec<CorpusSlice>> {
        let url = format!("{}/v1/corpus/search", self.base_url);

        let body = serde_json::json!({
            "query_text": query,
            "top_k": top_k,
        });

        let result = self.post_with_retry(&url, &body).await?;

        let slices: Vec<CorpusSlice> = result
            .get("results")
            .ok_or_else(|| CoreError::Internal("missing 'results' field in corpus response".into()))
            .and_then(|v| {
                serde_json::from_value(v.clone())
                    .map_err(|e| CoreError::Internal(format!("deserialize corpus results: {e}")))
            })?;

        Ok(slices)
    }

    // ── 内部方法 ──

    /// POST 请求 + 自动重试（指数退避）。
    async fn post_with_retry(
        &mut self,
        url: &str,
        body: &serde_json::Value,
    ) -> CoreResult<serde_json::Value> {
        let mut last_err = None;

        for attempt in 0..=MAX_RETRIES {
            match self.client.post(url).json(body).send().await {
                Ok(resp) => {
                    if resp.status().is_success() {
                        self.consecutive_failures = 0;
                        return resp.json::<serde_json::Value>().await.map_err(|e| {
                            CoreError::Internal(format!("parse JSON response: {e}"))
                        });
                    }
                    // HTTP 错误（4xx/5xx）
                    let status = resp.status();
                    let body_text = resp.text().await.unwrap_or_default();
                    last_err = Some(CoreError::Internal(format!(
                        "HTTP {status}: {body_text}"
                    )));
                }
                Err(e) => {
                    last_err = Some(CoreError::Internal(format!("request failed: {e}")));
                }
            }

            if attempt < MAX_RETRIES {
                // 指数退避: 1s → 2s → 4s
                let delay_ms = 1000 * (1 << attempt);
                tokio::time::sleep(Duration::from_millis(delay_ms)).await;
            }
        }

        // 所有重试均失败
        self.record_failure();
        Err(last_err.unwrap_or_else(|| CoreError::Internal("max retries exceeded".into())))
    }

    fn record_failure(&mut self) {
        self.consecutive_failures += 1;
    }

    /// 检查是否已达到连续失败阈值，应由上层决定是否重启 sidecar。
    pub fn should_restart(&self) -> bool {
        self.restart_on_failure && self.consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT
    }
}

// =========================================================================
// Tests
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_base_url() {
        let bridge = PythonBridge::new(None).unwrap();
        assert_eq!(bridge.base_url, "http://localhost:9091");
    }

    #[test]
    fn test_custom_base_url_trailing_slash_trimmed() {
        let bridge = PythonBridge::new(Some("http://127.0.0.1:9091/")).unwrap();
        assert_eq!(bridge.base_url, "http://127.0.0.1:9091");
    }

    #[test]
    fn test_initial_consecutive_failures_zero() {
        let bridge = PythonBridge::new(None).unwrap();
        assert_eq!(bridge.consecutive_failures(), 0);
    }

    #[test]
    fn test_should_restart_defaults_false() {
        let bridge = PythonBridge::new(None).unwrap();
        assert!(!bridge.should_restart());
    }

    #[test]
    fn test_set_restart_on_failure() {
        let mut bridge = PythonBridge::new(None).unwrap();
        bridge.set_restart_on_failure(true);
        // 即便启用，失败计数仍为 0 时不应重启
        assert!(!bridge.should_restart());
    }

    #[test]
    fn test_llm_call_request_serialization() {
        let req = LLMCallRequest {
            request_id: "r1".into(),
            task_type: TaskType::PadCompute,
            system_prompt_key: "pad_v1".into(),
            user_message: "分析情感".into(),
            response_format: "json".into(),
            temperature_override: Some(0.7),
            max_tokens_override: None,
        };

        let json = serde_json::to_value(&req).unwrap();
        assert_eq!(json["request_id"], "r1");
        assert_eq!(json["task_type"], "PadCompute");
        assert!(json.get("temperature_override").is_some());
        assert!(json.get("max_tokens_override").is_none());
    }

    #[test]
    fn test_llm_usage_deserialization() {
        let json = serde_json::json!({
            "input_tokens": 500,
            "output_tokens": 200,
            "cost_usd": 0.015,
            "model": "deepseek-v4-pro",
            "latency_ms": 1200
        });
        let usage: LLMUsage = serde_json::from_value(json).unwrap();
        assert_eq!(usage.input_tokens, 500);
        assert_eq!(usage.cost_usd, 0.015);
    }

    #[test]
    fn test_corpus_slice_deserialization() {
        let json = serde_json::json!({
            "slice_id": "s1",
            "text": "sample corpus text",
            "source_chapter_id": "ch1",
            "similarity_score": 0.92
        });
        let slice: CorpusSlice = serde_json::from_value(json).unwrap();
        assert_eq!(slice.slice_id, "s1");
        assert!((slice.similarity_score - 0.92).abs() < 0.001);
        assert!(slice.metadata.is_none());
    }
}
