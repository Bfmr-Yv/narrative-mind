//! xmgl-orchestrator — 调度中心、复杂度预判、拓扑选择、Hermes Council
//!
//! Phase B: 定义调度类型与枚举，骨架 Orchestrator。
//! Phase C: 填充复杂度预判、拓扑选择、Hermes Council 协议实现。

use std::sync::Arc;
use xmgl_core::{AgentFinding, AgentId, CoreResult, Severity, TaskComplexity, TaskType, TextRange};
use xmgl_agent::{AgentRegistry, SharedContext};
use xmgl_python_bridge::{LLMUsage, PythonBridge};

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
    /// 自动触发（如保存章节后自动分析）— Phase G 被动模式使用
    #[allow(dead_code)]
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
// AnalysisObserver — 观察者 trait（Tauri 事件 + 成本追踪的解耦接口）
// =========================================================================

/// 分析过程观察者。
///
/// Orchestrator 不依赖 Tauri，通过此 trait 解耦。
/// TG 2 在 `xmgl-tauri` 中实现此 trait，用 `AppHandle.emit()` 发事件。
pub trait AnalysisObserver: Send + Sync {
    fn on_agent_start(&self, agent_id: &str, agent_name: &str, progress_pct: f64);
    fn on_agent_done(&self, agent_id: &str, agent_name: &str, progress_pct: f64);
    fn on_analysis_complete(
        &self,
        request_id: &str,
        total_cost_usd: f64,
        total_latency_ms: u64,
        agent_count: u32,
        findings_count: u32,
    );
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
    /// 从 Agent JSON 输出解析的结构化发现
    pub findings: Vec<AgentFinding>,
    /// 每个 Agent 的 LLM 用量
    pub usages: Vec<(AgentId, LLMUsage)>,
    /// 累计成本 (USD)
    pub total_cost_usd: f64,
    /// 累计延迟 (ms)
    pub total_latency_ms: u64,
}

/// 从所有 Agent 的 JSON 输出中解析结构化发现。
///
/// 每个 Agent 的输出应为 `{"findings": [...]}` 格式。
/// 如有 `quote` 字段，通过 `find_text_range` 定位行号。
fn parse_findings(
    agent_outputs: &[(AgentId, String)],
    chapter_text: &str,
) -> Vec<AgentFinding> {
    let mut findings = Vec::new();

    for (agent_id, output) in agent_outputs {
        // 先 parse JSON，再检查是否为错误输出（顶层有 "error" key 且无 "findings"）
        let parsed = match serde_json::from_str::<serde_json::Value>(output) {
            Ok(v) => v,
            Err(_) => continue, // 非 JSON 输出，跳过
        };

        // 跳过错误输出：顶层有 "error" 且没有 "findings"
        if parsed.get("error").is_some() && parsed.get("findings").is_none() {
            continue;
        }

        if let Some(finding_list) = parsed.get("findings").and_then(|v| v.as_array()) {
                for f in finding_list {
                    let title = f
                        .get("title")
                        .and_then(|v| v.as_str())
                        .unwrap_or("Untitled")
                        .to_string();
                    let description = f
                        .get("description")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();
                    let severity = match f
                        .get("severity")
                        .and_then(|v| v.as_str())
                        .unwrap_or("Info")
                    {
                        "Critical" => Severity::Critical,
                        "Warn" => Severity::Warn,
                        _ => Severity::Info,
                    };
                    let quote = f.get("quote").and_then(|v| v.as_str()).unwrap_or("");
                    let suggestion = f
                        .get("suggestion")
                        .and_then(|v| v.as_str())
                        .filter(|s| *s != "null" && !s.is_empty())
                        .map(|s| s.to_string());

                    let location = if !quote.is_empty() {
                        find_text_range(chapter_text, quote)
                    } else {
                        None
                    };

                    findings.push(AgentFinding {
                        agent_id: format!("{:?}", agent_id),
                        severity,
                        title,
                        description,
                        location,
                        suggestion,
                        timestamp: chrono::Utc::now()
                            .format("%Y-%m-%dT%H:%M:%SZ")
                            .to_string(),
                    });
                }
            }
        }

    findings
}

/// 检测 Hermes Council 中各 Agent 之间的冲突。
///
/// 如果两个不同 agent 指向相同文本位置（location）但给出不同 severity
/// 或矛盾建议，生成额外的 `AgentFinding` 标记冲突。
pub fn detect_conflicts(findings: &[AgentFinding]) -> Vec<AgentFinding> {
    let mut conflicts = Vec::new();

    for (i, a) in findings.iter().enumerate() {
        for b in findings.iter().skip(i + 1) {
            // 必须有位置信息才能检测冲突
            let (loc_a, loc_b) = match (a.location, b.location) {
                (Some(la), Some(lb)) => (la, lb),
                _ => continue,
            };
            // 位置匹配（相同行范围内）
            if loc_a.start_line != loc_b.start_line
                || loc_a.end_line != loc_b.end_line
            {
                continue;
            }
            // 同一 agent 不跟自己冲突
            if a.agent_id == b.agent_id {
                continue;
            }
            // 严重级别不同或建议相反则标记冲突
            if a.severity != b.severity
                || (a.suggestion.is_some()
                    && b.suggestion.is_some()
                    && a.suggestion != b.suggestion)
            {
                conflicts.push(AgentFinding {
                    agent_id: "HermesCouncil".into(),
                    severity: if a.severity > b.severity {
                        a.severity
                    } else {
                        b.severity
                    },
                    title: format!(
                        "[CONFLICT] {} vs {}: {}",
                        a.agent_id, b.agent_id, a.title
                    ),
                    description: format!(
                        "冲突发现 — Agent {} 认为: {}\nAgent {} 认为: {}",
                        a.agent_id, a.description, b.agent_id, b.description
                    ),
                    location: a.location,
                    suggestion: Some("请人工审核并裁决此冲突。".into()),
                    timestamp: chrono::Utc::now()
                        .format("%Y-%m-%dT%H:%M:%SZ")
                        .to_string(),
                });
            }
        }
    }

    conflicts
}

/// 计算从行首到指定字节位置的 UTF-16 code unit 偏移（Monaco 列号）。
fn utf16_column_from_byte(line_prefix: &str, byte_offset: usize) -> u32 {
    line_prefix[..byte_offset]
        .chars()
        .map(|c| c.len_utf16() as u32)
        .sum::<u32>()
        + 1 // Monaco 列号从 1 开始
}

// =========================================================================
// 执行辅助函数
// =========================================================================

/// 串行执行 agent 列表：后序 Agent 可读取前序产出。
async fn run_serial(
    agent_ids: &[AgentId],
    ctx: &mut SharedContext,
    registry: &AgentRegistry,
    bridge: &PythonBridge,
    task_type: TaskType,
    observer: Option<&dyn AnalysisObserver>,
) -> (Vec<(AgentId, String)>, Vec<(AgentId, LLMUsage)>, u32) {
    let total = agent_ids.len() as f64;
    let mut outputs = Vec::new();
    let mut usages = Vec::new();
    let mut success_count = 0u32;

    for (idx, agent_id) in agent_ids.iter().enumerate() {
        if let Some(agent) = registry.get(*agent_id) {
            if agent.enabled() {
                if let Some(obs) = observer {
                    obs.on_agent_start(
                        &format!("{:?}", agent_id),
                        agent.name(),
                        (idx as f64 / total) * 100.0,
                    );
                }

                match agent.analyze(ctx, bridge, task_type).await {
                    Ok((output, usage_opt)) => {
                        ctx.record_output(*agent_id, output.clone());
                        outputs.push((*agent_id, output));
                        success_count += 1;
                        if let Some(usage) = usage_opt {
                            usages.push((*agent_id, usage));
                        }
                        if let Some(obs) = observer {
                            obs.on_agent_done(
                                &format!("{:?}", agent_id),
                                agent.name(),
                                ((idx + 1) as f64 / total) * 100.0,
                            );
                        }
                    }
                    Err(e) => {
                        let err_msg = format!("{{\"error\": \"{e}\"}}");
                        ctx.record_output(*agent_id, err_msg.clone());
                        outputs.push((*agent_id, err_msg));
                    }
                }
            }
        }
    }

    (outputs, usages, success_count)
}

/// 并行执行 agent 列表：所有 Agent 同时运行，互不依赖。
async fn run_parallel(
    agent_ids: &[AgentId],
    ctx: &SharedContext,
    registry: &AgentRegistry,
    bridge: &PythonBridge,
    task_type: TaskType,
    _observer: Option<&dyn AnalysisObserver>,
) -> (Vec<(AgentId, String)>, Vec<(AgentId, LLMUsage)>, u32) {
    let mut handles = Vec::new();

    for &agent_id in agent_ids {
        if let Some(agent) = registry.get(agent_id) {
            if !agent.enabled() {
                continue;
            }
            let agent = Arc::clone(&agent);
            let bridge = bridge.clone();
            let ctx = ctx.clone();

            handles.push(tokio::spawn(async move {
                let result = agent.analyze(&ctx, &bridge, task_type).await;
                (agent_id, agent.name().to_string(), result)
            }));
        }
    }

    let mut outputs = Vec::new();
    let mut usages = Vec::new();
    let mut success_count = 0u32;

    for handle in handles {
        match handle.await {
            Ok((agent_id, _name, Ok((output, usage_opt)))) => {
                outputs.push((agent_id, output));
                success_count += 1;
                if let Some(usage) = usage_opt {
                    usages.push((agent_id, usage));
                }
            }
            _ => {
                // Task panicked or agent errored — skip
            }
        }
    }

    (outputs, usages, success_count)
}

/// 在文本中搜索片段，返回其行/列/字节范围。
/// 列号使用 UTF-16 code unit 计数，与 Monaco 编辑器对齐。
fn find_text_range(haystack: &str, needle: &str) -> Option<TextRange> {
    let start_byte = haystack.find(needle)?;
    let end_byte = start_byte + needle.len();

    let start_line = haystack[..start_byte].matches('\n').count() as u32 + 1;

    // 当前行的起始字节位置
    let line_start = haystack[..start_byte]
        .rfind('\n')
        .map(|p| p + 1)
        .unwrap_or(0);
    let col_byte_offset = start_byte - line_start;
    let start_column = utf16_column_from_byte(
        &haystack[line_start..],
        col_byte_offset,
    );

    let end_line = haystack[..end_byte].matches('\n').count() as u32 + 1;
    let end_line_start = haystack[..end_byte]
        .rfind('\n')
        .map(|p| p + 1)
        .unwrap_or(0);
    let end_col_byte_offset = end_byte - end_line_start;
    let end_column = utf16_column_from_byte(
        &haystack[end_line_start..],
        end_col_byte_offset,
    );

    Some(TextRange {
        start_line,
        start_column,
        end_line,
        end_column,
        start_byte,
        end_byte,
    })
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
    /// 2. 依次调用每个 Agent（传入 task_type，收集 usage）
    /// 3. 如果全部失败且还有升级空间，升级拓扑重试
    /// 4. 解析所有 Agent 的 JSON 输出 → Vec<AgentFinding>
    /// 5. 通过 observer 回调通知 Tauri 前端
    pub async fn run_analysis(
        &self,
        request: &AnalysisRequest,
        ctx: &mut SharedContext,
        registry: &AgentRegistry,
        bridge: &PythonBridge,
        observer: Option<&dyn AnalysisObserver>,
    ) -> CoreResult<AnalysisResult> {
        let text_length = ctx.chapter_text.len();
        let complexity = self.predict_complexity(request.task_type, text_length);
        let mut topology = self.select_topology(request.task_type, complexity);
        let mut upgrade_round = 0;

        loop {
            // ── 按拓扑分派执行 ──
            let (outputs, usages, success_count) = match &topology {
                AgentTopology::Single(id) => {
                    run_serial(&[*id], ctx, registry, bridge, request.task_type, observer).await
                }
                AgentTopology::Serial { agents } => {
                    run_serial(agents, ctx, registry, bridge, request.task_type, observer).await
                }
                AgentTopology::Parallel { agents } => {
                    run_parallel(agents, ctx, registry, bridge, request.task_type, observer).await
                }
                AgentTopology::HermesCouncil { analysts, chair } => {
                    // Phase 1: 并行分析 → Phase 2: Chair 串行综合
                    let (mut outputs, mut usages, success) = run_parallel(
                        analysts, ctx, registry, bridge, request.task_type, observer,
                    )
                    .await;
                    // 记录 analyst 产出到 ctx
                    for (id, ref output) in &outputs {
                        ctx.record_output(*id, output.clone());
                    }
                    // Chair 综合
                    let (chair_outputs, chair_usages, chair_success) = run_serial(
                        &[*chair], ctx, registry, bridge, request.task_type, observer,
                    )
                    .await;
                    outputs.extend(chair_outputs);
                    usages.extend(chair_usages);
                    (outputs, usages, success + chair_success)
                }
            };

            let agent_ids = topology.agent_ids();

            // 如果有成功产出，或者已达最大升级轮数，或者无法再升级，返回结果
            if success_count > 0
                || upgrade_round >= self.max_upgrade_rounds
                || self.upgrade_topology(&topology, request.task_type).is_none()
            {
                let findings = parse_findings(&outputs, &ctx.chapter_text);
                let total_cost_usd = usages.iter().map(|(_, u)| u.cost_usd).sum();
                let total_latency_ms = usages
                    .iter()
                    .map(|(_, u)| u.latency_ms as u64)
                    .sum();

                if let Some(obs) = observer {
                    obs.on_analysis_complete(
                        &request.request_id,
                        total_cost_usd,
                        total_latency_ms,
                        agent_ids.len() as u32,
                        findings.len() as u32,
                    );
                }

                return Ok(AnalysisResult {
                    agent_outputs: outputs,
                    topology,
                    complexity,
                    findings,
                    usages,
                    total_cost_usd,
                    total_latency_ms,
                });
            }

            // 全部失败 → HCP-MAD 升级拓扑重试
            if let Some(upgraded) = self.upgrade_topology(&topology, request.task_type) {
                topology = upgraded;
                upgrade_round += 1;
                for (agent_id, _) in &outputs {
                    ctx.outputs.remove(agent_id);
                }
            } else {
                let findings = parse_findings(&outputs, &ctx.chapter_text);
                return Ok(AnalysisResult {
                    agent_outputs: outputs,
                    topology,
                    complexity,
                    findings,
                    usages,
                    total_cost_usd: 0.0,
                    total_latency_ms: 0,
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
            TaskType::Rerank => AgentId::EditorInChief,
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
        let bridge = PythonBridge::new(Some("http://127.0.0.1:1")).unwrap();
        let mut ctx = SharedContext::new("p1", "测试文本");

        let request = AnalysisRequest {
            request_id: "req-test".into(),
            task_type: TaskType::PadCompute,
            trigger: AnalysisTrigger::Manual,
            chapter_ids: vec![],
            context_note: None,
        };

        let result = orch.run_analysis(&request, &mut ctx, &registry, &bridge, None).await;
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
            findings: vec![],
            usages: vec![],
            total_cost_usd: 0.0,
            total_latency_ms: 0,
        };
        assert_eq!(result.agent_outputs.len(), 1);
        assert_eq!(result.complexity, TaskComplexity::Simple);
    }
}
