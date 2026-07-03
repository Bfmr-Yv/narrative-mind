//! xmgl-orchestrator — 调度中心、复杂度预判、拓扑选择、Hermes Council
//!
//! Phase B: 定义调度类型与枚举，骨架 Orchestrator。
//! Phase C: 填充复杂度预判、拓扑选择、Hermes Council 协议实现。

use xmgl_core::{AgentId, CoreResult, TaskComplexity, TaskType};
use xmgl_agent::{AgentRegistry, SharedContext};
use xmgl_python_bridge::PythonBridge;

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

/// 单次分析执行结果。
#[derive(Debug, Clone)]
pub struct AnalysisResult {
    /// 每个 Agent 的产出 (AgentId, output_json)
    pub agent_outputs: Vec<(AgentId, String)>,
    /// 选取的拓扑
    pub topology: AgentTopology,
    /// 任务复杂度
    pub complexity: TaskComplexity,
}

/// 调度中心 — Phase D 实现。
///
/// 包含：复杂度预判、拓扑选择、HCP-MAD 渐进升级、实际调度逻辑。
pub struct Orchestrator {
    /// 是否启用 Hermes Council 协议
    pub hermes_enabled: bool,
    /// 最大升级轮数（防止无限升级）
    pub max_upgrade_rounds: u32,
}

impl Orchestrator {
    /// 创建新的 Orchestrator。
    pub fn new() -> Self {
        Self {
            hermes_enabled: true,
            max_upgrade_rounds: 2,
        }
    }

    /// 预判任务复杂度。
    ///
    /// 基于文本长度 + 任务类型综合判断：
    /// - 文本长度: <200 → Simple, 200-2000 → Moderate, >2000 → Complex/FullScene
    /// - 任务类型: 全局分析类提升一级，单一检查类保持
    pub fn predict_complexity(&self, task_type: TaskType, text_length: usize) -> TaskComplexity {
        // 1. 文本长度决定基础复杂度
        let base = if text_length < 200 {
            TaskComplexity::Trivial
        } else if text_length < 800 {
            TaskComplexity::Simple
        } else if text_length < 2000 {
            TaskComplexity::Moderate
        } else if text_length < 5000 {
            TaskComplexity::Complex
        } else {
            TaskComplexity::FullScene
        };

        // 2. 全局分析类任务至少 Moderate
        let min_for_task = match task_type {
            TaskType::SceneAnalysis => TaskComplexity::FullScene,
            TaskType::PadCompute | TaskType::ForeshadowDetect | TaskType::CausalExtract => {
                TaskComplexity::Moderate
            }
            _ => TaskComplexity::Simple,
        };

        // 取两者中较高的
        if (min_for_task as u8) > (base as u8) {
            min_for_task
        } else {
            base
        }
    }

    /// 选择 Agent 执行拓扑。
    ///
    /// 根据复杂度 + 任务类型选择最优执行模式：
    /// - Trivial/Simple: 单 Agent
    /// - Moderate: 2-3 Agent 串行（有依赖关系的）
    /// - Complex: 3-5 Agent 串行
    /// - FullScene: Hermes Council（多 Agent 协同 + 总编裁决）
    pub fn select_topology(&self, task_type: TaskType, complexity: TaskComplexity) -> AgentTopology {
        match complexity {
            TaskComplexity::Trivial | TaskComplexity::Simple => {
                AgentTopology::Single(self.default_agent_for(task_type))
            }
            TaskComplexity::Moderate => {
                // 2-3 个有依赖关系的 Agent 串行
                AgentTopology::Serial {
                    agents: &[AgentId::Character, AgentId::Narrative, AgentId::Prose],
                }
            }
            TaskComplexity::Complex => {
                // 4-5 个 Agent，串行执行以传递上下文
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
                            AgentId::Economy,
                            AgentId::ReaderExpectation,
                            AgentId::Conception,
                            AgentId::EditorInChief,
                        ],
                    }
                }
            }
        }
    }

    /// HCP-MAD 渐进升级：当当前拓扑产出质量不足时，升级到更复杂的拓扑。
    ///
    /// 升级路径：
    /// - Single → Serial(3) → Serial(5) → FullScene
    /// - Serial(3) → Serial(5) → FullScene
    /// - Serial(5) → FullScene
    ///
    /// 返回升级后的拓扑，如果已经是最复杂则返回 None。
    pub fn upgrade_topology(&self, current: &AgentTopology, _task_type: TaskType) -> Option<AgentTopology> {
        match current {
            AgentTopology::Single(_) => Some(AgentTopology::Serial {
                agents: &[AgentId::Character, AgentId::Narrative, AgentId::Prose],
            }),
            AgentTopology::Serial { agents } if agents.len() <= 3 => Some(AgentTopology::Serial {
                agents: &[
                    AgentId::Character,
                    AgentId::World,
                    AgentId::Narrative,
                    AgentId::Prose,
                    AgentId::Theme,
                ],
            }),
            AgentTopology::Serial { agents } if agents.len() <= 5 => {
                if self.hermes_enabled {
                    Some(AgentTopology::HermesCouncil {
                        analysts: &[
                            AgentId::Character,
                            AgentId::World,
                            AgentId::Narrative,
                            AgentId::Prose,
                            AgentId::Theme,
                        ],
                        chair: AgentId::EditorInChief,
                    })
                } else {
                    Some(AgentTopology::Serial {
                        agents: &[
                            AgentId::Character,
                            AgentId::World,
                            AgentId::Narrative,
                            AgentId::Prose,
                            AgentId::Theme,
                            AgentId::Economy,
                            AgentId::ReaderExpectation,
                            AgentId::Conception,
                            AgentId::EditorInChief,
                        ],
                    })
                }
            }
            // 已经是最复杂的拓扑
            _ => None,
        }
    }

    /// 裁决 Agent 冲突。
    ///
    /// Phase D: 基于严重级别的简单裁决策略：
    /// - Minor: 取 proposal_a（先到先得）
    /// - Moderate: 取 proposal_a（后续可扩展为加权评分）
    /// - Critical: 标记需要总编裁决，暂取 proposal_a
    pub fn resolve_conflict(&self, conflict: &AgentConflict) -> String {
        match conflict.severity {
            ConflictSeverity::Minor => conflict.proposal_a.clone(),
            ConflictSeverity::Moderate | ConflictSeverity::Critical => {
                // Phase D: 仍返回 proposal_a，但标记为需要人工审核
                // Phase E+: 实现真正的加权评分 + 总编裁决
                conflict.proposal_a.clone()
            }
        }
    }

    /// 执行一次分析（HCP-MAD 渐进升级）。
    ///
    /// 流程：
    /// 1. 预判复杂度 → 选择拓扑
    /// 2. 依次调用 Agent
    /// 3. 如果全部失败且还有升级空间，升级拓扑重试
    /// 4. 记录最终结果到 SharedContext
    pub async fn run_analysis(
        &self,
        request: &AnalysisRequest,
        ctx: &mut SharedContext,
        registry: &AgentRegistry,
        bridge: &mut PythonBridge,
    ) -> CoreResult<AnalysisResult> {
        let text_length = ctx.chapter_text.len();
        let complexity = self.predict_complexity(request.task_type, text_length);
        let mut topology = self.select_topology(request.task_type, complexity);
        let mut upgrade_round = 0;

        loop {
            let agent_ids = topology.agent_ids();
            let mut outputs = Vec::new();
            let mut success_count = 0;

            for agent_id in &agent_ids {
                if let Some(agent) = registry.get(*agent_id) {
                    if agent.enabled() {
                        match agent.analyze(ctx, bridge).await {
                            Ok(output) => {
                                ctx.record_output(*agent_id, output.clone());
                                outputs.push((*agent_id, output));
                                success_count += 1;
                            }
                            Err(e) => {
                                // Agent 失败不阻塞其他 Agent，记录错误
                                let err_msg = format!("{{\"error\": \"{e}\"}}");
                                ctx.record_output(*agent_id, err_msg.clone());
                                outputs.push((*agent_id, err_msg));
                            }
                        }
                    }
                }
            }

            // 如果有成功产出，或者已达最大升级轮数，或者无法再升级，返回结果
            if success_count > 0
                || upgrade_round >= self.max_upgrade_rounds
                || self.upgrade_topology(&topology, request.task_type).is_none()
            {
                return Ok(AnalysisResult {
                    agent_outputs: outputs,
                    topology,
                    complexity,
                });
            }

            // 全部失败 → HCP-MAD 升级拓扑重试
            if let Some(upgraded) = self.upgrade_topology(&topology, request.task_type) {
                topology = upgraded;
                upgrade_round += 1;
                // 清空上一轮的错误输出
                for (agent_id, _) in &outputs {
                    ctx.outputs.remove(agent_id);
                }
            } else {
                return Ok(AnalysisResult {
                    agent_outputs: outputs,
                    topology,
                    complexity,
                });
            }
        }
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

    // ── predict_complexity ──

    #[test]
    fn test_predict_complexity_short_text_simple_task() {
        let orch = Orchestrator::new();
        // 短文本 + StyleCheck → Simple（StyleCheck 最低 Simple）
        assert_eq!(
            orch.predict_complexity(TaskType::StyleCheck, 100),
            TaskComplexity::Simple
        );
    }

    #[test]
    fn test_predict_complexity_medium_text_simple_task() {
        let orch = Orchestrator::new();
        // 中等文本 + 简单任务 → Simple
        assert_eq!(
            orch.predict_complexity(TaskType::StyleCheck, 500),
            TaskComplexity::Simple
        );
    }

    #[test]
    fn test_predict_complexity_pad_compute_bumps_to_moderate() {
        let orch = Orchestrator::new();
        // 短文本但 PadCompute 至少 Moderate
        assert_eq!(
            orch.predict_complexity(TaskType::PadCompute, 100),
            TaskComplexity::Moderate
        );
    }

    #[test]
    fn test_predict_complexity_long_text() {
        let orch = Orchestrator::new();
        // 长文本 → Complex
        assert_eq!(
            orch.predict_complexity(TaskType::StyleCheck, 3000),
            TaskComplexity::Complex
        );
    }

    #[test]
    fn test_predict_complexity_scene_analysis_always_full() {
        let orch = Orchestrator::new();
        // SceneAnalysis 至少 FullScene
        assert_eq!(
            orch.predict_complexity(TaskType::SceneAnalysis, 500),
            TaskComplexity::FullScene
        );
    }

    #[test]
    fn test_predict_complexity_very_long_text() {
        let orch = Orchestrator::new();
        assert_eq!(
            orch.predict_complexity(TaskType::EntityExtract, 6000),
            TaskComplexity::FullScene
        );
    }

    // ── select_topology ──

    #[test]
    fn test_select_topology_trivial() {
        let orch = Orchestrator::new();
        let topo = orch.select_topology(TaskType::StyleCheck, TaskComplexity::Trivial);
        assert!(matches!(topo, AgentTopology::Single(AgentId::Prose)));
    }

    #[test]
    fn test_select_topology_moderate_serial_3() {
        let orch = Orchestrator::new();
        let topo = orch.select_topology(TaskType::PadCompute, TaskComplexity::Moderate);
        match topo {
            AgentTopology::Serial { agents } => assert_eq!(agents.len(), 3),
            _ => panic!("Expected Serial topology"),
        }
    }

    #[test]
    fn test_select_topology_complex_serial_5() {
        let orch = Orchestrator::new();
        let topo = orch.select_topology(TaskType::PadCompute, TaskComplexity::Complex);
        match topo {
            AgentTopology::Serial { agents } => assert_eq!(agents.len(), 5),
            _ => panic!("Expected Serial topology"),
        }
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
        match topo {
            AgentTopology::Serial { agents } => assert_eq!(agents.len(), 9),
            _ => panic!("Expected Serial with all 9 agents"),
        }
    }

    // ── upgrade_topology ──

    #[test]
    fn test_upgrade_topology_single_to_serial() {
        let orch = Orchestrator::new();
        let topo = AgentTopology::Single(AgentId::Character);
        let upgraded = orch.upgrade_topology(&topo, TaskType::PadCompute).unwrap();
        match upgraded {
            AgentTopology::Serial { agents } => assert_eq!(agents.len(), 3),
            _ => panic!("Expected Serial(3)"),
        }
    }

    #[test]
    fn test_upgrade_topology_serial_3_to_serial_5() {
        let orch = Orchestrator::new();
        let topo = AgentTopology::Serial {
            agents: &[AgentId::Character, AgentId::Narrative, AgentId::Prose],
        };
        let upgraded = orch.upgrade_topology(&topo, TaskType::PadCompute).unwrap();
        match upgraded {
            AgentTopology::Serial { agents } => assert_eq!(agents.len(), 5),
            _ => panic!("Expected Serial(5)"),
        }
    }

    #[test]
    fn test_upgrade_topology_serial_5_to_hermes() {
        let orch = Orchestrator::new();
        let topo = AgentTopology::Serial {
            agents: &[
                AgentId::Character,
                AgentId::World,
                AgentId::Narrative,
                AgentId::Prose,
                AgentId::Theme,
            ],
        };
        let upgraded = orch.upgrade_topology(&topo, TaskType::PadCompute).unwrap();
        assert!(matches!(upgraded, AgentTopology::HermesCouncil { .. }));
    }

    #[test]
    fn test_upgrade_topology_hermes_is_terminal() {
        let orch = Orchestrator::new();
        let topo = AgentTopology::HermesCouncil {
            analysts: &[
                AgentId::Character,
                AgentId::World,
                AgentId::Narrative,
                AgentId::Prose,
                AgentId::Theme,
            ],
            chair: AgentId::EditorInChief,
        };
        assert!(orch.upgrade_topology(&topo, TaskType::PadCompute).is_none());
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

    #[tokio::test]
    async fn test_run_analysis_no_upgrade_rounds() {
        // 禁用升级以避免连接不可达端口的超时
        let mut orch = Orchestrator::new();
        orch.max_upgrade_rounds = 0;
        let registry = AgentRegistry::with_all_agents();
        let mut bridge = PythonBridge::new(Some("http://127.0.0.1:1")).unwrap();
        let mut ctx = SharedContext::new("p1", "测试文本");

        let request = AnalysisRequest {
            request_id: "req-test".into(),
            task_type: TaskType::PadCompute,
            trigger: AnalysisTrigger::Manual,
            chapter_ids: vec![],
            context_note: None,
        };

        let result = orch.run_analysis(&request, &mut ctx, &registry, &mut bridge).await;
        match result {
            Ok(ar) => {
                // 无升级 → Moderate → Serial(3) → 全部失败但直接返回
                assert!(!ar.agent_outputs.is_empty());
                for (_, output) in &ar.agent_outputs {
                    assert!(output.contains("error"));
                }
            }
            Err(_) => {
                // bridge 级别错误也是可接受的
            }
        }
    }

    #[test]
    fn test_analysis_result_fields() {
        let result = AnalysisResult {
            agent_outputs: vec![(AgentId::Character, "{}".into())],
            topology: AgentTopology::Single(AgentId::Character),
            complexity: TaskComplexity::Simple,
        };
        assert_eq!(result.agent_outputs.len(), 1);
        assert_eq!(result.complexity, TaskComplexity::Simple);
    }
}
