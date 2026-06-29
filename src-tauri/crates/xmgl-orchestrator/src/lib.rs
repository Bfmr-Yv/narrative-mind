//! xmgl-orchestrator — 调度中心、复杂度预判、拓扑选择、Hermes Council
//!
//! Phase B: 定义调度类型与枚举，骨架 Orchestrator。
//! Phase C: 填充复杂度预判、拓扑选择、Hermes Council 协议实现。

use xmgl_core::{AgentId, TaskComplexity, TaskType};

// =========================================================================
// Agent 拓扑
// =========================================================================

/// Agent 执行拓扑。
///
/// 根据任务复杂度选择合适的执行模式。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgentTopology {
    /// 单 Agent 执行 — 简单任务
    Single(AgentId),
    /// 并行执行 — 无依赖的多个 Agent 同时运行
    Parallel { agents: &'static [AgentId] },
    /// 串行执行 — Agent 按顺序运行，后序 Agent 可读取前序产出
    Serial { agents: &'static [AgentId] },
    /// Hermes Council — 多 Agent 协同评审 + 总编裁决
    HermesCouncil {
        analysts: &'static [AgentId],
        chair: AgentId,
    },
}

impl AgentTopology {
    /// 该拓扑涉及的所有 Agent ID。
    pub fn agent_ids(&self) -> Vec<AgentId> {
        match self {
            AgentTopology::Single(id) => vec![*id],
            AgentTopology::Parallel { agents } => agents.to_vec(),
            AgentTopology::Serial { agents } => agents.to_vec(),
            AgentTopology::HermesCouncil { analysts, chair } => {
                let mut ids = analysts.to_vec();
                ids.push(*chair);
                ids
            }
        }
    }
}

// =========================================================================
// 分析请求
// =========================================================================

/// 一次分析请求。
#[derive(Debug, Clone)]
pub struct AnalysisRequest {
    /// 请求 ID（UUID）
    pub request_id: String,
    /// 任务类型
    pub task_type: TaskType,
    /// 触发源（用户手动 / 自动）
    pub trigger: AnalysisTrigger,
    /// 目标章节范围
    pub chapter_ids: Vec<String>,
    /// 额外上下文
    pub context_note: Option<String>,
}

/// 分析触发源。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AnalysisTrigger {
    /// 用户手动触发
    Manual,
    /// 自动触发（如保存章节后自动分析）
    Auto,
}

// =========================================================================
// 冲突记录
// =========================================================================

/// Agent 间的意见冲突。
#[derive(Debug, Clone)]
pub struct AgentConflict {
    /// 冲突涉及的 Agent
    pub agents: Vec<AgentId>,
    /// 冲突描述
    pub description: String,
    /// Agent A 的建议
    pub proposal_a: String,
    /// Agent B 的建议
    pub proposal_b: String,
    /// 冲突严重级别
    pub severity: ConflictSeverity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ConflictSeverity {
    /// 轻微分歧（如措辞偏好）
    Minor,
    /// 中等冲突（如角色行为解释不同）
    Moderate,
    /// 严重冲突（如情节逻辑互斥）
    Critical,
}

// =========================================================================
// Orchestrator 骨架
// =========================================================================

/// 调度中心 — Phase B 骨架。
///
/// Phase C 填充：复杂度预判、拓扑选择、实际调度逻辑。
pub struct Orchestrator {
    /// 是否启用 Hermes Council 协议
    pub hermes_enabled: bool,
}

impl Orchestrator {
    /// 创建新的 Orchestrator。
    pub fn new() -> Self {
        Self {
            hermes_enabled: true,
        }
    }

    /// 预判任务复杂度。
    ///
    /// Phase B: 始终返回 `Moderate`。
    /// Phase C: 根据文本长度、任务类型、Agent 反馈调整。
    pub fn predict_complexity(&self, _task_type: TaskType, _text_length: usize) -> TaskComplexity {
        TaskComplexity::Moderate
    }

    /// 选择 Agent 执行拓扑。
    ///
    /// Phase B: 简单任务 → Single，其他 → Serial。
    /// Phase C: 根据复杂度 + Agent 依赖图选择最优拓扑。
    pub fn select_topology(&self, task_type: TaskType, complexity: TaskComplexity) -> AgentTopology {
        match complexity {
            TaskComplexity::Trivial | TaskComplexity::Simple => {
                AgentTopology::Single(self.default_agent_for(task_type))
            }
            TaskComplexity::Moderate | TaskComplexity::Complex => {
                AgentTopology::Serial {
                    agents: &[AgentId::Character, AgentId::Narrative, AgentId::Prose],
                }
            }
            TaskComplexity::FullScene => {
                if self.hermes_enabled {
                    AgentTopology::HermesCouncil {
                        analysts: &[
                            AgentId::Character,
                            AgentId::World,
                            AgentId::Narrative,
                            AgentId::Prose,
                            AgentId::Theme,
                        ],
                        chair: AgentId::EditorInChief,
                    }
                } else {
                    AgentTopology::Serial {
                        agents: &[
                            AgentId::Character,
                            AgentId::World,
                            AgentId::Narrative,
                            AgentId::Prose,
                            AgentId::Theme,
                        ],
                    }
                }
            }
        }
    }

    /// 裁决 Agent 冲突。
    ///
    /// Phase B: 总是返回第一条建议。
    /// Phase C: 实现加权评分 + 总编裁决。
    pub fn resolve_conflict(&self, conflict: &AgentConflict) -> String {
        conflict.proposal_a.clone()
    }

    fn default_agent_for(&self, task_type: TaskType) -> AgentId {
        match task_type {
            TaskType::PadCompute | TaskType::ActionInfer | TaskType::EntityExtract => {
                AgentId::Character
            }
            TaskType::RuleCheck | TaskType::SpatialCheck => AgentId::World,
            TaskType::ForeshadowDetect
            | TaskType::CausalExtract
            | TaskType::ResolutionCheck
            | TaskType::EventPredict => AgentId::Narrative,
            TaskType::StyleCheck | TaskType::RegisterCheck => AgentId::Prose,
            TaskType::ThemeExtract => AgentId::Theme,
            TaskType::EconomyCheck => AgentId::Economy,
            TaskType::ExpectationAnalyze => AgentId::ReaderExpectation,
            TaskType::ImageryDetect => AgentId::Conception,
            _ => AgentId::EditorInChief,
        }
    }
}

impl Default for Orchestrator {
    fn default() -> Self {
        Self::new()
    }
}

// =========================================================================
// Tests
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_topology_agent_ids() {
        let topo = AgentTopology::Single(AgentId::Character);
        assert_eq!(topo.agent_ids(), vec![AgentId::Character]);

        let topo = AgentTopology::Parallel {
            agents: &[AgentId::Character, AgentId::World],
        };
        assert_eq!(topo.agent_ids().len(), 2);

        let topo = AgentTopology::HermesCouncil {
            analysts: &[AgentId::Character, AgentId::World],
            chair: AgentId::EditorInChief,
        };
        let ids = topo.agent_ids();
        assert_eq!(ids.len(), 3);
        assert!(ids.contains(&AgentId::EditorInChief));
    }

    #[test]
    fn test_predict_complexity_default() {
        let orch = Orchestrator::new();
        assert_eq!(
            orch.predict_complexity(TaskType::PadCompute, 1000),
            TaskComplexity::Moderate
        );
    }

    #[test]
    fn test_select_topology_trivial() {
        let orch = Orchestrator::new();
        let topo = orch.select_topology(TaskType::StyleCheck, TaskComplexity::Trivial);
        assert!(matches!(topo, AgentTopology::Single(AgentId::Prose)));
    }

    #[test]
    fn test_select_topology_full_scene_hermes() {
        let orch = Orchestrator::new();
        let topo = orch.select_topology(TaskType::SceneAnalysis, TaskComplexity::FullScene);
        assert!(matches!(topo, AgentTopology::HermesCouncil { .. }));
    }

    #[test]
    fn test_select_topology_full_scene_no_hermes() {
        let mut orch = Orchestrator::new();
        orch.hermes_enabled = false;
        let topo = orch.select_topology(TaskType::SceneAnalysis, TaskComplexity::FullScene);
        assert!(matches!(topo, AgentTopology::Serial { .. }));
    }

    #[test]
    fn test_resolve_conflict_returns_a() {
        let orch = Orchestrator::new();
        let conflict = AgentConflict {
            agents: vec![AgentId::Character, AgentId::World],
            description: "角色位置矛盾".into(),
            proposal_a: "方案A: 角色在屋内".into(),
            proposal_b: "方案B: 角色在花园".into(),
            severity: ConflictSeverity::Moderate,
        };
        let resolved = orch.resolve_conflict(&conflict);
        assert_eq!(resolved, "方案A: 角色在屋内");
    }

    #[test]
    fn test_default_agent_task_mapping() {
        let orch = Orchestrator::new();
        assert_eq!(
            orch.default_agent_for(TaskType::PadCompute),
            AgentId::Character
        );
        assert_eq!(
            orch.default_agent_for(TaskType::RuleCheck),
            AgentId::World
        );
        assert_eq!(
            orch.default_agent_for(TaskType::ForeshadowDetect),
            AgentId::Narrative
        );
        assert_eq!(
            orch.default_agent_for(TaskType::ThemeExtract),
            AgentId::Theme
        );
    }
}
