//! LlmClientImpl — reqwest 原生 LLM 客户端。
//!
//! 实现 xmgl_core::LlmClient trait，直接调用 OpenAI-compatible API。

use std::collections::HashMap;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde_json::Value;
use uuid::Uuid;

use xmgl_core::{CoreError, CoreResult, LLMCallResponse, LLMUsage, LlmClient, TaskType};

use crate::config::{LlmConfig, resolve_config, tier_route};
use crate::prompts::PROMPT_REGISTRY;

// =========================================================================
// LlmClientImpl
// =========================================================================

pub struct LlmClientImpl {
    http: reqwest::Client,
    config: LlmConfig,
}

impl LlmClientImpl {
    /// 从环境变量构建客户端。
    pub fn new() -> CoreResult<Self> {
        let config = resolve_config();
        let http = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| CoreError::Internal(format!("create HTTP client: {e}")))?;
        Ok(Self { http, config })
    }

    /// 是否已配置 API Key。
    pub fn is_configured(&self) -> bool {
        self.config.is_configured
    }

    /// 获取配置引用（供 health_check 使用）。
    pub fn config(&self) -> &LlmConfig {
        &self.config
    }

    /// 带重试的 LLM 调用。
    async fn call_with_retry(
        &self,
        system_prompt: &str,
        user_message: &str,
        max_tokens: u32,
        temperature: f64,
    ) -> CoreResult<(Option<Value>, Option<LLMUsage>)> {
        const MAX_RETRIES: u32 = 3;
        let backoff_ms: [u64; 3] = [500, 1000, 2000];

        let url = format!(
            "{}/chat/completions",
            self.config.base_url.trim_end_matches('/')
        );

        let body = serde_json::json!({
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        });

        let mut last_error: Option<CoreError> = None;

        for attempt in 0..=MAX_RETRIES {
            let t0 = Instant::now();

            let result = self
                .http
                .post(&url)
                .header("Authorization", format!("Bearer {}", self.config.api_key))
                .json(&body)
                .send()
                .await;

            let latency_ms = t0.elapsed().as_millis() as u32;

            match result {
                Ok(resp) => {
                    let status = resp.status();

                    if status.is_success() {
                        let api_resp: Value = resp.json().await.map_err(|e| {
                            CoreError::Internal(format!("parse response: {e}"))
                        })?;

                        let content = api_resp["choices"][0]["message"]["content"]
                            .as_str()
                            .unwrap_or("");

                        let usage = api_resp.get("usage").map(|u| {
                            let input_tokens =
                                u["prompt_tokens"].as_u64().unwrap_or(0) as u32;
                            let output_tokens =
                                u["completion_tokens"].as_u64().unwrap_or(0) as u32;
                            let cost = (input_tokens as f64 * self.config.cost_input_1k
                                / 1000.0)
                                + (output_tokens as f64 * self.config.cost_output_1k
                                    / 1000.0);
                            LLMUsage {
                                input_tokens,
                                output_tokens,
                                cost_usd: cost,
                                model: self.config.model.clone(),
                                latency_ms,
                            }
                        });

                        let result = Self::parse_json_content(content);
                        return Ok((result, usage));
                    }

                    // Non-success status
                    let body_text = resp.text().await.unwrap_or_default();
                    let err =
                        CoreError::Internal(format!("HTTP {status}: {body_text}"));

                    // 4xx errors (except 429) are not retryable
                    if status.is_client_error()
                        && status != reqwest::StatusCode::TOO_MANY_REQUESTS
                    {
                        return Err(err);
                    }

                    last_error = Some(err);
                }
                Err(e) => {
                    last_error =
                        Some(CoreError::Internal(format!("request failed: {e}")));
                }
            }

            if attempt < MAX_RETRIES {
                tokio::time::sleep(Duration::from_millis(backoff_ms[attempt as usize]))
                    .await;
            }
        }

        Err(last_error.unwrap_or_else(|| {
            CoreError::Internal("max retries exceeded".into())
        }))
    }

    /// 解析 JSON 内容，带 fallback（复制 Python 逻辑）。
    fn parse_json_content(content: &str) -> Option<Value> {
        if let Ok(v) = serde_json::from_str(content) {
            return Some(v);
        }
        // 尝试从文本中提取 JSON 块
        let start = content.find('{')?;
        let end = content.rfind('}')?;
        if end > start {
            serde_json::from_str(&content[start..=end]).ok()
        } else {
            None
        }
    }
}

// =========================================================================
// LlmClient trait 实现
// =========================================================================

#[async_trait]
impl LlmClient for LlmClientImpl {
    async fn call_agent(
        &self,
        prompt_key: &str,
        variables: &HashMap<String, String>,
        task_type: TaskType,
    ) -> CoreResult<LLMCallResponse> {
        // 1. 查 prompt 注册表
        let template = PROMPT_REGISTRY.get(prompt_key).ok_or_else(|| {
            CoreError::NotFound(format!("unknown prompt key: {prompt_key}"))
        })?;

        // 2. 渲染 user_message
        let system_prompt = template.system.to_string();
        let user_message = (template.format)(variables);

        // 3. 查 tier route
        let tier = tier_route(task_type.as_str()).ok_or_else(|| {
            CoreError::NotFound(format!(
                "unknown task type: {}",
                task_type.as_str()
            ))
        })?;

        // 4. 生成 request_id
        let request_id = Uuid::new_v4().to_string();
        let short_id = request_id[..8].to_string();

        // 5. 调 LLM（带重试）
        let (result, usage) = self
            .call_with_retry(
                &system_prompt,
                &user_message,
                tier.max_tokens,
                tier.temperature,
            )
            .await?;

        Ok(LLMCallResponse {
            request_id: short_id,
            success: true,
            result,
            usage,
            error: None,
        })
    }
}

// =========================================================================
// 测试
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_json_content_valid() {
        let json = r#"{"key": "value"}"#;
        let result = LlmClientImpl::parse_json_content(json);
        assert!(result.is_some());
        assert_eq!(result.unwrap()["key"], "value");
    }

    #[test]
    fn test_parse_json_content_with_wrapper_text() {
        let text = r#"一些前置文字 {"key": "value"} 后续文字"#;
        let result = LlmClientImpl::parse_json_content(text);
        assert!(result.is_some());
        assert_eq!(result.unwrap()["key"], "value");
    }

    #[test]
    fn test_parse_json_content_invalid() {
        let text = "这不是 JSON";
        let result = LlmClientImpl::parse_json_content(text);
        assert!(result.is_none());
    }

    #[test]
    fn test_parse_json_content_empty() {
        let result = LlmClientImpl::parse_json_content("");
        assert!(result.is_none());
    }
}
