//! Provider 检测、API Key 解析、Tier 路由表、成本常量。
//!
//! 复制 Python `src-python/llm/config.py` 的全部逻辑。

use std::env;

// =========================================================================
// Provider 默认值
// =========================================================================

// --- DeepSeek V4 ---
pub const DEEPSEEK_BASE_URL: &str = "https://api.deepseek.com/v1";
pub const DEEPSEEK_PRO_MODEL: &str = "deepseek-v4-pro";
pub const DEEPSEEK_FLASH_MODEL: &str = "deepseek-v4-flash";
pub const DEEPSEEK_COST_INPUT_1K: f64 = 0.000435;
pub const DEEPSEEK_COST_OUTPUT_1K: f64 = 0.00087;
pub const DEEPSEEK_FLASH_COST_INPUT_1K: f64 = 0.00014;
pub const DEEPSEEK_FLASH_COST_OUTPUT_1K: f64 = 0.00028;

// --- OpenAI ---
pub const OPENAI_BASE_URL: &str = "https://api.openai.com/v1";
pub const OPENAI_DEFAULT_MODEL: &str = "gpt-4o-mini";
pub const OPENAI_COST_INPUT_1K: f64 = 0.00015;
pub const OPENAI_COST_OUTPUT_1K: f64 = 0.00060;

// --- Xiaomi MiMo ---
pub const MIMO_BASE_URL: &str = "https://token-plan-cn.xiaomimimo.com/v1";
pub const MIMO_PRO_MODEL: &str = "mimo-v2.5-pro";
pub const MIMO_FLASH_MODEL: &str = "mimo-v2.5";
pub const MIMO_COST_INPUT_1K: f64 = 0.003;
pub const MIMO_COST_OUTPUT_1K: f64 = 0.006;
pub const MIMO_FLASH_COST_INPUT_1K: f64 = 0.001;
pub const MIMO_FLASH_COST_OUTPUT_1K: f64 = 0.002;

// 月度预算强硬上限
pub const MONTHLY_BUDGET_USD: f64 = 20.00;

// 三层熔断阈值
pub const MELTDOWN_WARN_RATIO: f64 = 0.50;
pub const MELTDOWN_RESTRICT_RATIO: f64 = 0.80;
pub const MELTDOWN_BLOCK_RATIO: f64 = 0.95;

// API 超时
pub const API_TIMEOUT_SECS: u64 = 25;
pub const MAX_RETRIES: u32 = 2;

// =========================================================================
// Provider 检测
// =========================================================================

/// 检测当前使用的 LLM provider。
///
/// 优先级: `LLM_PROVIDER` 环境变量 > `MIMO_API_KEY` 存在 > `DEEPSEEK_API_KEY` 存在 > 默认 `openai`
pub fn resolve_provider() -> &'static str {
    if let Ok(provider) = env::var("LLM_PROVIDER") {
        let p = provider.trim().to_lowercase();
        if p == "deepseek" || p == "openai" || p == "mimo" {
            // Leak is intentional — returned &'static str lives for program lifetime
            return match p.as_str() {
                "deepseek" => "deepseek",
                "mimo" => "mimo",
                _ => "openai",
            };
        }
    }
    if env::var("MIMO_API_KEY").is_ok() {
        return "mimo";
    }
    if env::var("DEEPSEEK_API_KEY").is_ok() {
        return "deepseek";
    }
    "openai"
}

// =========================================================================
// LlmConfig
// =========================================================================

#[derive(Debug, Clone)]
pub struct LlmConfig {
    pub api_key: String,
    pub base_url: String,
    pub model: String,
    pub flash_model: String,
    pub is_configured: bool,
    pub provider: String,
    pub cost_input_1k: f64,
    pub cost_output_1k: f64,
    pub flash_cost_input_1k: f64,
    pub flash_cost_output_1k: f64,
}

/// 解析完整 LLM 配置。
///
/// API Key 优先级: `LLM_API_KEY` → `DEEPSEEK_API_KEY` → `MIMO_API_KEY` → `OPENAI_API_KEY`
/// Base URL: `LLM_BASE_URL` → provider 默认
/// Model: `LLM_MODEL` → provider 默认
pub fn resolve_config() -> LlmConfig {
    let provider = resolve_provider();

    let (default_url, pro_model, flash_model, cost_in, cost_out, flash_cost_in, flash_cost_out) =
        match provider {
            "deepseek" => (
                DEEPSEEK_BASE_URL,
                DEEPSEEK_PRO_MODEL,
                DEEPSEEK_FLASH_MODEL,
                DEEPSEEK_COST_INPUT_1K,
                DEEPSEEK_COST_OUTPUT_1K,
                DEEPSEEK_FLASH_COST_INPUT_1K,
                DEEPSEEK_FLASH_COST_OUTPUT_1K,
            ),
            "mimo" => (
                MIMO_BASE_URL,
                MIMO_PRO_MODEL,
                MIMO_FLASH_MODEL,
                MIMO_COST_INPUT_1K,
                MIMO_COST_OUTPUT_1K,
                MIMO_FLASH_COST_INPUT_1K,
                MIMO_FLASH_COST_OUTPUT_1K,
            ),
            _ => (
                OPENAI_BASE_URL,
                OPENAI_DEFAULT_MODEL,
                OPENAI_DEFAULT_MODEL,
                OPENAI_COST_INPUT_1K,
                OPENAI_COST_OUTPUT_1K,
                OPENAI_COST_INPUT_1K,
                OPENAI_COST_OUTPUT_1K,
            ),
        };

    // API Key 解析
    let api_key = env::var("LLM_API_KEY")
        .or_else(|_| env::var("DEEPSEEK_API_KEY"))
        .or_else(|_| env::var("MIMO_API_KEY"))
        .or_else(|_| env::var("OPENAI_API_KEY"))
        .unwrap_or_default();

    let base_url = env::var("LLM_BASE_URL")
        .unwrap_or_else(|_| default_url.to_string());

    let model = env::var("LLM_MODEL")
        .unwrap_or_else(|_| pro_model.to_string());

    let is_configured = !api_key.trim().is_empty();

    LlmConfig {
        api_key,
        base_url,
        model,
        flash_model: flash_model.to_string(),
        is_configured,
        provider: provider.to_string(),
        cost_input_1k: cost_in,
        cost_output_1k: cost_out,
        flash_cost_input_1k: flash_cost_in,
        flash_cost_output_1k: flash_cost_out,
    }
}

// =========================================================================
// Tier 路由表
// =========================================================================

#[derive(Debug, Clone, Copy)]
pub struct TierRoute {
    pub max_tokens: u32,
    pub temperature: f64,
}

/// 根据 task_type 字符串返回 tier 配置。
///
/// 复制 Python TIER_CONFIG 的全部 17 条映射。
pub fn tier_route(task_type: &str) -> Option<TierRoute> {
    match task_type {
        "pad_compute" => Some(TierRoute { max_tokens: 1024, temperature: 0.2 }),
        "action_infer" => Some(TierRoute { max_tokens: 1536, temperature: 0.3 }),
        "rule_check" => Some(TierRoute { max_tokens: 1536, temperature: 0.2 }),
        "spatial_check" => Some(TierRoute { max_tokens: 1024, temperature: 0.2 }),
        "rerank" => Some(TierRoute { max_tokens: 1024, temperature: 0.1 }),
        "entity_extract" => Some(TierRoute { max_tokens: 1536, temperature: 0.1 }),
        "scene_analysis" => Some(TierRoute { max_tokens: 4096, temperature: 0.4 }),
        "foreshadow_detect" => Some(TierRoute { max_tokens: 2048, temperature: 0.3 }),
        "causal_extract" => Some(TierRoute { max_tokens: 2048, temperature: 0.2 }),
        "resolution_check" => Some(TierRoute { max_tokens: 1024, temperature: 0.2 }),
        "event_predict" => Some(TierRoute { max_tokens: 2048, temperature: 0.4 }),
        "style_check" => Some(TierRoute { max_tokens: 1536, temperature: 0.2 }),
        "register_check" => Some(TierRoute { max_tokens: 1536, temperature: 0.3 }),
        "theme_extract" => Some(TierRoute { max_tokens: 2048, temperature: 0.4 }),
        "economy_check" => Some(TierRoute { max_tokens: 1536, temperature: 0.2 }),
        "expectation_analyze" => Some(TierRoute { max_tokens: 2048, temperature: 0.4 }),
        "imagery_detect" => Some(TierRoute { max_tokens: 2048, temperature: 0.4 }),
        "world_rule_extract" => Some(TierRoute { max_tokens: 2048, temperature: 0.1 }),
        "character_profile_extract" => Some(TierRoute { max_tokens: 2048, temperature: 0.1 }),
        "plot_structure_extract" => Some(TierRoute { max_tokens: 2048, temperature: 0.1 }),
        "style_extract" => Some(TierRoute { max_tokens: 2048, temperature: 0.1 }),
        "expand_context" => Some(TierRoute { max_tokens: 2048, temperature: 0.5 }),
        _ => None,
    }
}

// =========================================================================
// 测试
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    // 注意: 这些测试直接调 resolve_provider/resolve_config，
    // 对当前进程环境变量敏感。主要测逻辑路径。

    #[test]
    fn test_tier_route_known_task() {
        let route = tier_route("pad_compute").unwrap();
        assert_eq!(route.max_tokens, 1024);
        assert!((route.temperature - 0.2).abs() < 0.001);
    }

    #[test]
    fn test_tier_route_scene_analysis() {
        let route = tier_route("scene_analysis").unwrap();
        assert_eq!(route.max_tokens, 4096);
        assert!((route.temperature - 0.4).abs() < 0.001);
    }

    #[test]
    fn test_tier_route_unknown_task() {
        assert!(tier_route("nonexistent").is_none());
    }

    #[test]
    fn test_tier_route_all_17_keys() {
        let keys = [
            "pad_compute", "action_infer", "rule_check", "spatial_check", "rerank",
            "entity_extract", "scene_analysis", "foreshadow_detect", "causal_extract",
            "resolution_check", "event_predict", "style_check", "register_check",
            "theme_extract", "economy_check", "expectation_analyze", "imagery_detect",
        ];
        for key in keys {
            assert!(tier_route(key).is_some(), "missing tier route for: {key}");
        }
        assert_eq!(keys.len(), 17);
    }

    #[test]
    fn test_resolve_config_returns_valid_struct() {
        let config = resolve_config();
        // 不设环境变量时 provider 为 openai，但 api_key 可能为空
        assert!(!config.base_url.is_empty());
        assert!(!config.model.is_empty());
    }
}
