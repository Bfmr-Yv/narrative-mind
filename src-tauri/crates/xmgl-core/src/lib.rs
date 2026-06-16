//! Narrative Mind v4.0 — 共享类型定义
//!
//! 所有 crate 依赖的基础类型，零外部依赖（仅 serde）。

use serde::{Deserialize, Serialize};

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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectMeta {
    pub id: String,
    pub name: String,
    pub created_at: String,
    pub updated_at: String,
    pub chapter_count: u32,
    pub total_words: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChapterData {
    pub id: String,
    pub project_id: String,
    pub title: String,
    pub text: String,
    pub word_count: u32,
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
        }
    }
}
