//! Narrative Mind v4.0 — 共享类型定义
//!
//! 所有 crate 依赖的基础类型（serde + thiserror）。

use serde::{Deserialize, Serialize};
use std::str::FromStr;
use thiserror::Error;

// =========================================================================
// PAD 情感模型
// =========================================================================

/// PAD 三维情感坐标
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PADState {
    /// 愉悦度 [-1, 1]
    pub pleasure: f64,
    /// 唤醒度 [-1, 1]
    pub arousal: f64,
    /// 支配度 [-1, 1]
    pub dominance: f64,
}

impl PADState {
    pub fn new(pleasure: f64, arousal: f64, dominance: f64) -> Self {
        Self {
            pleasure,
            arousal,
            dominance,
        }
    }
}

impl Default for PADState {
    fn default() -> Self {
        Self {
            pleasure: 0.0,
            arousal: 0.0,
            dominance: 0.0,
        }
    }
}

// =========================================================================
// Agent 标识
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AgentId {
    Character,
    World,
    Narrative,
    Prose,
    Theme,
    Economy,
    ReaderExpectation,
    Conception,
    EditorInChief,
}

impl AgentId {
    pub fn name(&self) -> &'static str {
        match self {
            AgentId::Character => "角色 Agent",
            AgentId::World => "世界 Agent",
            AgentId::Narrative => "叙事 Agent",
            AgentId::Prose => "文辞 Agent",
            AgentId::Theme => "主题 Agent",
            AgentId::Economy => "经济 Agent",
            AgentId::ReaderExpectation => "预期 Agent",
            AgentId::Conception => "构思 Agent",
            AgentId::EditorInChief => "总编 Agent",
        }
    }

    /// 返回该 Agent 默认对应的 TaskType 的字符串表示。
    pub fn as_task_type_str(&self) -> &'static str {
        match self {
            AgentId::Character => "pad_compute",
            AgentId::World => "rule_check",
            AgentId::Narrative => "foreshadow_detect",
            AgentId::Prose => "style_check",
            AgentId::Theme => "theme_extract",
            AgentId::Economy => "economy_check",
            AgentId::ReaderExpectation => "expectation_analyze",
            AgentId::Conception => "imagery_detect",
            AgentId::EditorInChief => "scene_analysis",
        }
    }

    pub fn all() -> Vec<AgentId> {
        vec![
            AgentId::Character,
            AgentId::World,
            AgentId::Narrative,
            AgentId::Prose,
            AgentId::Theme,
            AgentId::Economy,
            AgentId::ReaderExpectation,
            AgentId::Conception,
            AgentId::EditorInChief,
        ]
    }
}

// =========================================================================
// 严重级别
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Severity {
    Info,
    Warn,
    Critical,
}

// =========================================================================
// 任务类型 (17 LLM task types)
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TaskType {
    // Phase 1
    PadCompute,
    ActionInfer,
    RuleCheck,
    SpatialCheck,
    Rerank,
    EntityExtract,
    SceneAnalysis,
    // Phase 2 — 叙事
    ForeshadowDetect,
    CausalExtract,
    ResolutionCheck,
    EventPredict,
    // Phase 2 — 文辞
    StyleCheck,
    RegisterCheck,
    // Phase 3 — 主题
    ThemeExtract,
    // Phase 3 — 经济
    EconomyCheck,
    // Phase 3 — 读者预期
    ExpectationAnalyze,
    // Phase 3 — 构思
    ImageryDetect,
}

impl TaskType {
    pub fn as_str(&self) -> &'static str {
        match self {
            TaskType::PadCompute => "pad_compute",
            TaskType::ActionInfer => "action_infer",
            TaskType::RuleCheck => "rule_check",
            TaskType::SpatialCheck => "spatial_check",
            TaskType::Rerank => "rerank",
            TaskType::EntityExtract => "entity_extract",
            TaskType::SceneAnalysis => "scene_analysis",
            TaskType::ForeshadowDetect => "foreshadow_detect",
            TaskType::CausalExtract => "causal_extract",
            TaskType::ResolutionCheck => "resolution_check",
            TaskType::EventPredict => "event_predict",
            TaskType::StyleCheck => "style_check",
            TaskType::RegisterCheck => "register_check",
            TaskType::ThemeExtract => "theme_extract",
            TaskType::EconomyCheck => "economy_check",
            TaskType::ExpectationAnalyze => "expectation_analyze",
            TaskType::ImageryDetect => "imagery_detect",
        }
    }
}

impl FromStr for TaskType {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "pad_compute" => Ok(TaskType::PadCompute),
            "action_infer" => Ok(TaskType::ActionInfer),
            "rule_check" => Ok(TaskType::RuleCheck),
            "spatial_check" => Ok(TaskType::SpatialCheck),
            "rerank" => Ok(TaskType::Rerank),
            "entity_extract" => Ok(TaskType::EntityExtract),
            "scene_analysis" => Ok(TaskType::SceneAnalysis),
            "foreshadow_detect" => Ok(TaskType::ForeshadowDetect),
            "causal_extract" => Ok(TaskType::CausalExtract),
            "resolution_check" => Ok(TaskType::ResolutionCheck),
            "event_predict" => Ok(TaskType::EventPredict),
            "style_check" => Ok(TaskType::StyleCheck),
            "register_check" => Ok(TaskType::RegisterCheck),
            "theme_extract" => Ok(TaskType::ThemeExtract),
            "economy_check" => Ok(TaskType::EconomyCheck),
            "expectation_analyze" => Ok(TaskType::ExpectationAnalyze),
            "imagery_detect" => Ok(TaskType::ImageryDetect),
            _ => Err(format!("unknown TaskType: {s}")),
        }
    }
}

// =========================================================================
// 文本范围
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct TextRange {
    pub start_line: u32,
    pub start_column: u32,
    pub end_line: u32,
    pub end_column: u32,
    pub start_byte: usize,
    pub end_byte: usize,
}

// =========================================================================
// 项目 & 章节
// =========================================================================

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProjectMeta {
    pub id: String,
    pub name: String,
    pub created_at: String,
    pub updated_at: String,
    pub chapter_count: u32,
    pub total_words: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChapterData {
    pub id: String,
    pub project_id: String,
    pub title: String,
    pub text: String,
    pub word_count: u32,
    pub sort_order: u32,
    pub created_at: String,
    pub updated_at: String,
}

// =========================================================================
// 定价级别
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PricingTier {
    Free,
    Pro,
    Premium,
}

// =========================================================================
// 模型级别
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelTier {
    RuleOnly,
    Flash,
    Pro,
}

// =========================================================================
// 复杂度
// =========================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskComplexity {
    Trivial,
    Simple,
    Moderate,
    Complex,
    FullScene,
}

// =========================================================================
// 核心错误类型
// =========================================================================

/// xmgl-core 统一错误类型。
///
/// 所有 crate 通过此类型共享基础错误语义，
/// 上层 crate 可通过 `thiserror` 的 `#[from]` 或手动 `impl From` 转换。
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum CoreError {
    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Already exists: {0}")]
    AlreadyExists(String),

    #[error("Invalid argument: {0}")]
    InvalidArgument(String),

    #[error("Invalid state: {0}")]
    InvalidState(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

/// `Result` alias，以 CoreError 为默认错误类型。
pub type CoreResult<T> = Result<T, CoreError>;

// =========================================================================
// Tests
// =========================================================================

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
        for task in &[
            TaskType::PadCompute,
            TaskType::EntityExtract,
            TaskType::SceneAnalysis,
        ] {
            let s = task.as_str();
            assert!(!s.is_empty());
            let roundtrip: TaskType = s.parse().unwrap();
            assert_eq!(&roundtrip, task);
        }
    }

    #[test]
    fn test_task_type_from_str_invalid() {
        let result: Result<TaskType, _> = "nonexistent".parse();
        assert!(result.is_err());
    }

    #[test]
    fn test_chapter_data_sort_order() {
        let chapter = ChapterData {
            id: "ch1".into(),
            project_id: "p1".into(),
            title: "Test Chapter".into(),
            text: "Hello world".into(),
            word_count: 2,
            sort_order: 5,
            created_at: "2026-01-01".into(),
            updated_at: "2026-01-02".into(),
        };
        assert_eq!(chapter.sort_order, 5);
    }

    #[test]
    fn test_project_meta_eq() {
        let a = ProjectMeta {
            id: "p1".into(),
            name: "Test".into(),
            created_at: "2026-01-01".into(),
            updated_at: "2026-01-02".into(),
            chapter_count: 3,
            total_words: 1000,
        };
        let b = ProjectMeta {
            id: "p1".into(),
            name: "Test".into(),
            created_at: "2026-01-01".into(),
            updated_at: "2026-01-02".into(),
            chapter_count: 3,
            total_words: 1000,
        };
        assert_eq!(a, b);
    }

    #[test]
    fn test_chapter_data_eq() {
        let ch = |sort_order: u32| ChapterData {
            id: "ch1".into(),
            project_id: "p1".into(),
            title: "Ch1".into(),
            text: "text".into(),
            word_count: 4,
            sort_order,
            created_at: "2026-01-01".into(),
            updated_at: "2026-01-01".into(),
        };
        assert_eq!(ch(1), ch(1));
        assert_ne!(ch(1), ch(2));
    }

    #[test]
    fn test_core_error_display() {
        let e = CoreError::NotFound("chapter ch1".into());
        assert_eq!(e.to_string(), "Not found: chapter ch1");

        let e = CoreError::AlreadyExists("project p1".into());
        assert_eq!(e.to_string(), "Already exists: project p1");

        let e = CoreError::InvalidArgument("sort_order must be >= 0".into());
        assert_eq!(
            e.to_string(),
            "Invalid argument: sort_order must be >= 0"
        );

        let e = CoreError::InvalidState("agent not initialized".into());
        assert_eq!(e.to_string(), "Invalid state: agent not initialized");

        let e = CoreError::Internal("database connection lost".into());
        assert_eq!(e.to_string(), "Internal error: database connection lost");
    }

    #[test]
    fn test_core_error_eq() {
        let e1 = CoreError::NotFound("x".into());
        let e2 = CoreError::NotFound("x".into());
        assert_eq!(e1, e2);

        let e3 = CoreError::NotFound("y".into());
        assert_ne!(e1, e3);
    }
}
