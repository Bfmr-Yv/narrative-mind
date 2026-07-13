//! xmgl-orchestrator — 调度中心、复杂度预判、拓扑选择、Hermes Council
//!
//! Phase B: 定义调度类型与枚举，骨架 Orchestrator。
//! Phase C: 填充复杂度预判、拓扑选择、Hermes Council 协议实现。

use std::collections::HashMap;
use std::sync::Arc;
use xmgl_core::{
    AgentFinding, AgentId, Character, CharacterStatus, CoreResult, LLMUsage, LlmClient, Location,
    Severity, TaskComplexity, TaskType, TextRange,
};
use xmgl_agent::{AgentRegistry, SharedContext};

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
    /// 冲突方 A
    pub agent_a: AgentId,
    /// 冲突方 B
    pub agent_b: AgentId,
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
    /// 一条修改建议就绪 → 前端渲染黄点。
    fn on_proposal_ready(
        &self,
        proposal_id: &str,
        agent_id: &str,
        title: &str,
        severity: &str,
        location: Option<TextRange>,
        suggestion: &str,
    );
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
    /// Phase L1: 从 Agent 输出中解析的角色
    pub extracted_characters: Vec<Character>,
    /// Phase L1: 从 Agent 输出中解析的地点
    pub extracted_locations: Vec<Location>,
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

/// 从 Agent 输出中提取实体数据（角色 + 地点）。
///
/// 遍历所有 Agent 输出，寻找顶层 `characters` 和 `locations` JSON 数组字段。
/// 支持两种格式：
/// - 字符串数组：`["贾宝玉", "林黛玉"]` → 构造 Character/Location 结构体（名称以外字段为空）
/// - 对象数组：`[{"name": "贾宝玉", "role": "主角", ...}]` → 从 LLM 语义字段提取
///
/// 数据库管理字段（id、project_id、created_at、updated_at、source）始终在 Rust 端生成。
fn extract_entities(
    agent_outputs: &[(AgentId, String)],
    project_id: &str,
    chapter_id: Option<&str>,
) -> (Vec<Character>, Vec<Location>) {
    let mut characters: Vec<Character> = Vec::new();
    let mut locations: Vec<Location> = Vec::new();
    let now = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();

    for (_agent_id, output) in agent_outputs {
        let parsed = match serde_json::from_str::<serde_json::Value>(output) {
            Ok(v) => v,
            Err(_) => continue,
        };

        // ── 角色 ──
        if let Some(chars) = parsed.get("characters").and_then(|v| v.as_array()) {
            for c in chars {
                match c {
                    // LLM 返回字符串 → 从名称构造
                    serde_json::Value::String(name) => {
                        let id = format!(
                            "char-{}",
                            &uuid::Uuid::new_v4().to_string()[..8]
                        );
                        characters.push(Character {
                            id,
                            project_id: project_id.to_string(),
                            name: name.clone(),
                            aliases: vec![],
                            status: CharacterStatus::Unknown,
                            current_location: None,
                            role: String::new(),
                            summary: String::new(),
                            first_appearance_chapter: chapter_id.map(|s| s.to_string()),
                            source: "llm_extract".to_string(),
                            created_at: now.clone(),
                            updated_at: now.clone(),
                        });
                    }
                    // LLM 返回对象 → 提取语义字段
                    _ => {
                        let name = c
                            .get("name")
                            .and_then(|v| v.as_str())
                            .unwrap_or("");
                        if name.is_empty() {
                            continue;
                        }

                        let aliases: Vec<String> = c
                            .get("aliases")
                            .and_then(|v| v.as_array())
                            .map(|a| {
                                a.iter()
                                    .filter_map(|v| v.as_str().map(String::from))
                                    .collect()
                            })
                            .unwrap_or_default();

                        let role = c
                            .get("role")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();

                        let summary = c
                            .get("summary")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();

                        let status = match c
                            .get("status")
                            .and_then(|v| v.as_str())
                            .unwrap_or("Unknown")
                        {
                            "Dead" => CharacterStatus::Dead,
                            "Alive" => CharacterStatus::Alive,
                            _ => CharacterStatus::Unknown,
                        };

                        let current_location = c
                            .get("current_location")
                            .and_then(|v| v.as_str())
                            .filter(|s| !s.is_empty())
                            .map(String::from);

                        let id = format!(
                            "char-{}",
                            &uuid::Uuid::new_v4().to_string()[..8]
                        );
                        characters.push(Character {
                            id,
                            project_id: project_id.to_string(),
                            name: name.to_string(),
                            aliases,
                            status,
                            current_location,
                            role,
                            summary,
                            first_appearance_chapter: chapter_id.map(|s| s.to_string()),
                            source: "llm_extract".to_string(),
                            created_at: now.clone(),
                            updated_at: now.clone(),
                        });
                    }
                }
            }
        }

        // ── 地点 ──
        if let Some(locs) = parsed.get("locations").and_then(|v| v.as_array()) {
            for l in locs {
                match l {
                    // LLM 返回字符串 → 从名称构造
                    serde_json::Value::String(name) => {
                        let id = format!(
                            "loc-{}",
                            &uuid::Uuid::new_v4().to_string()[..8]
                        );
                        locations.push(Location {
                            id,
                            project_id: project_id.to_string(),
                            name: name.clone(),
                            aliases: vec![],
                            location_type: String::new(),
                            parent_location: None,
                            description: String::new(),
                            features: vec![],
                            created_at: now.clone(),
                            updated_at: now.clone(),
                        });
                    }
                    // LLM 返回对象 → 提取语义字段
                    _ => {
                        let name = l
                            .get("name")
                            .and_then(|v| v.as_str())
                            .unwrap_or("");
                        if name.is_empty() {
                            continue;
                        }

                        let aliases: Vec<String> = l
                            .get("aliases")
                            .and_then(|v| v.as_array())
                            .map(|a| {
                                a.iter()
                                    .filter_map(|v| v.as_str().map(String::from))
                                    .collect()
                            })
                            .unwrap_or_default();

                        let location_type = l
                            .get("location_type")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();

                        let description = l
                            .get("description")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();

                        let features: Vec<String> = l
                            .get("features")
                            .and_then(|v| v.as_array())
                            .map(|a| {
                                a.iter()
                                    .filter_map(|v| v.as_str().map(String::from))
                                    .collect()
                            })
                            .unwrap_or_default();

                        let parent_location = l
                            .get("parent_location")
                            .and_then(|v| v.as_str())
                            .filter(|s| !s.is_empty())
                            .map(String::from);

                        let id = format!(
                            "loc-{}",
                            &uuid::Uuid::new_v4().to_string()[..8]
                        );
                        locations.push(Location {
                            id,
                            project_id: project_id.to_string(),
                            name: name.to_string(),
                            aliases,
                            location_type,
                            parent_location,
                            description,
                            features,
                            created_at: now.clone(),
                            updated_at: now.clone(),
                        });
                    }
                }
            }
        }
    }

    (characters, locations)
}

/// 判断两个文本范围是否重叠。
///
/// 重叠检测比精确匹配更保守——两个 Agent 指向同一段文本的不同范围
/// 通常意味着对同一问题的不同判断，应标记为冲突。
fn ranges_overlap(a: TextRange, b: TextRange) -> bool {
    // 行范围不重叠
    if a.end_line < b.start_line || b.end_line < a.start_line {
        return false;
    }
    // 同行但列范围不重叠
    if a.start_line == a.end_line
        && b.start_line == b.end_line
        && a.start_line == b.start_line
        && (a.end_column < b.start_column || b.end_column < a.start_column)
    {
        return false;
    }
    true
}

/// 从 AgentFinding 的 agent_id 字符串解析回 AgentId 枚举。
fn parse_agent_id(s: &str) -> Option<AgentId> {
    match s {
        "Character" => Some(AgentId::Character),
        "World" => Some(AgentId::World),
        "Narrative" => Some(AgentId::Narrative),
        "Prose" => Some(AgentId::Prose),
        "Theme" => Some(AgentId::Theme),
        "Economy" => Some(AgentId::Economy),
        "ReaderExpectation" => Some(AgentId::ReaderExpectation),
        "Conception" => Some(AgentId::Conception),
        "EditorInChief" => Some(AgentId::EditorInChief),
        "EntityExtract" => Some(AgentId::EntityExtract),
        _ => None,
    }
}

/// 检测 Hermes Council 中各 Agent 之间的冲突。
///
/// 如果两个不同 agent 指向重叠的文本位置但给出不同 severity
/// 或矛盾建议，同时产出 `AgentFinding`（前端展示）和 `AgentConflict`（供 resolve_conflict 裁决）。
pub fn detect_conflicts(findings: &[AgentFinding]) -> (Vec<AgentFinding>, Vec<AgentConflict>) {
    let mut conflict_findings = Vec::new();
    let mut agent_conflicts = Vec::new();

    for (i, a) in findings.iter().enumerate() {
        for b in findings.iter().skip(i + 1) {
            // 必须有位置信息才能检测冲突
            let (loc_a, loc_b) = match (a.location, b.location) {
                (Some(la), Some(lb)) => (la, lb),
                _ => continue,
            };
            // 范围重叠检测（保守精确匹配会漏掉真正的冲突）
            if !ranges_overlap(loc_a, loc_b) {
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
                let conflict_severity = match a.severity.max(b.severity) {
                    Severity::Critical => ConflictSeverity::Critical,
                    Severity::Warn => ConflictSeverity::Moderate,
                    _ => ConflictSeverity::Minor,
                };

                // AgentFinding — 前端展示
                conflict_findings.push(AgentFinding {
                    agent_id: "HermesCouncil".into(),
                    severity: a.severity.max(b.severity),
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

                // AgentConflict — 结构化冲突，供 resolve_conflict 裁决
                if let (Some(agent_a), Some(agent_b)) =
                    (parse_agent_id(&a.agent_id), parse_agent_id(&b.agent_id))
                {
                    agent_conflicts.push(AgentConflict {
                        agent_a,
                        agent_b,
                        description: format!(
                            "{} vs {}: {}",
                            a.agent_id, b.agent_id, a.title
                        ),
                        proposal_a: a.suggestion.clone().unwrap_or_default(),
                        proposal_b: b.suggestion.clone().unwrap_or_default(),
                        severity: conflict_severity,
                    });
                }
            }
        }
    }

    (conflict_findings, agent_conflicts)
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
    llm: Arc<dyn LlmClient>,
    agent_task_types: &HashMap<AgentId, TaskType>,
    observer: Option<&dyn AnalysisObserver>,
) -> (Vec<(AgentId, String)>, Vec<(AgentId, LLMUsage)>, u32) {
    let total = agent_ids.len() as f64;
    let mut outputs = Vec::new();
    let mut usages = Vec::new();
    let mut success_count = 0u32;

    for (idx, agent_id) in agent_ids.iter().enumerate() {
        if let Some(agent) = registry.get(*agent_id) {
            if agent.enabled() {
                let task_type = agent_task_types
                    .get(agent_id)
                    .copied()
                    .unwrap_or_else(|| Orchestrator::task_type_for_agent(agent_id));

                if let Some(obs) = observer {
                    obs.on_agent_start(
                        &format!("{:?}", agent_id),
                        agent.name(),
                        (idx as f64 / total) * 100.0,
                    );
                }

                match agent.analyze(ctx, Arc::clone(&llm), task_type).await {
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
    llm: Arc<dyn LlmClient>,
    agent_task_types: &HashMap<AgentId, TaskType>,
    observer: Option<&dyn AnalysisObserver>,
) -> (Vec<(AgentId, String)>, Vec<(AgentId, LLMUsage)>, u32) {
    let total = agent_ids.len() as f64;
    let mut handles = Vec::new();

    // Emit batch_start for each agent before spawning
    if let Some(obs) = observer {
        for (idx, agent_id) in agent_ids.iter().enumerate() {
            if let Some(agent) = registry.get(*agent_id) {
                obs.on_agent_start(
                    &format!("{:?}", agent_id),
                    agent.name(),
                    (idx as f64 / total) * 100.0,
                );
            }
        }
    }

    for (idx, &agent_id) in agent_ids.iter().enumerate() {
        if let Some(agent) = registry.get(agent_id) {
            if !agent.enabled() {
                continue;
            }
            let agent = Arc::clone(&agent);
            let llm = Arc::clone(&llm);
            let ctx = ctx.clone();
            let done_pct = ((idx + 1) as f64 / total) * 100.0;
            // Capture per-agent task type for the spawned task
            let task_type = agent_task_types
                .get(&agent_id)
                .copied()
                .unwrap_or_else(|| Orchestrator::task_type_for_agent(&agent_id));

            handles.push(tokio::spawn(async move {
                let result = agent.analyze(&ctx, llm, task_type).await;
                (agent_id, agent.name().to_string(), done_pct, result)
            }));
        }
    }

    let mut outputs = Vec::new();
    let mut usages = Vec::new();
    let mut success_count = 0u32;

    for handle in handles {
        match handle.await {
            Ok((agent_id, name, done_pct, Ok((output, usage_opt)))) => {
                outputs.push((agent_id, output));
                success_count += 1;
                if let Some(usage) = usage_opt {
                    usages.push((agent_id, usage));
                }
                if let Some(obs) = observer {
                    obs.on_agent_done(&format!("{:?}", agent_id), &name, done_pct);
                }
            }
            Ok((agent_id, _, _, Err(e))) => {
                // Agent errored — record error output so it's visible in findings
                let err_msg = format!("{{\"error\": \"{e}\"}}");
                outputs.push((agent_id, err_msg));
            }
            Err(_) => {
                // Task panicked (JoinError) — unrecoverable, skip
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
    /// 是否启用 Phase 4 反思回合
    pub enable_reflection: bool,
    /// 最大反思轮数（防止无限循环）
    pub max_reflection_rounds: u32,
}

impl Orchestrator {
    /// 创建新的 Orchestrator。
    pub fn new() -> Self {
        Self {
            hermes_enabled: true,
            max_upgrade_rounds: 2,
            enable_reflection: true,
            max_reflection_rounds: 2,
        }
    }

    /// 返回每个 AgentId 对应的主 TaskType。
    ///
    /// 用于并行调度时，每个 Agent 拿到自己的 TaskType，
    /// 从而让 `prompt_key_for()` 路由到正确的 system prompt。
    pub fn task_type_for_agent(agent_id: &AgentId) -> TaskType {
        match agent_id {
            AgentId::Character => TaskType::PadCompute,
            AgentId::World => TaskType::RuleCheck,
            AgentId::Narrative => TaskType::ForeshadowDetect,
            AgentId::Prose => TaskType::StyleCheck,
            AgentId::Theme => TaskType::ThemeExtract,
            AgentId::Economy => TaskType::EconomyCheck,
            AgentId::ReaderExpectation => TaskType::ExpectationAnalyze,
            AgentId::Conception => TaskType::ImageryDetect,
            AgentId::EditorInChief => TaskType::SceneAnalysis,
            AgentId::EntityExtract => TaskType::EntityExtract,
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
                            AgentId::EntityExtract,
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
                            AgentId::EntityExtract,
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
                            AgentId::EntityExtract,
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
                            AgentId::EntityExtract,
                        ],
                    })
                }
            }
            // 已经是最复杂的拓扑
            _ => None,
        }
    }

    /// 裁决 Agent 冲突 — Phase H 加权评分。
    ///
    /// 评分维度（三维加权）：
    /// 1. Agent 模型级别: Pro=3, Flash=1（各自 agent 独立评分）
    /// 2. 冲突级别: Critical=3, Moderate=2, Minor=1
    /// 3. 建议质量: 建议长度 / 50（归一化，上限 5）
    ///
    /// 总分 = agent_tier * 0.4 + severity * 0.4 + quality * 0.2
    /// 对 proposal_a 和 proposal_b 分别用各自 agent 的 tier 评分，取高分者。
    pub fn resolve_conflict(&self, conflict: &AgentConflict) -> String {
        fn agent_tier(id: &AgentId) -> f64 {
            match id {
                AgentId::Character
                | AgentId::Narrative
                | AgentId::Theme
                | AgentId::EditorInChief => 3.0,
                _ => 1.0,
            }
        }

        let severity_weight = match conflict.severity {
            ConflictSeverity::Critical => 3.0,
            ConflictSeverity::Moderate => 2.0,
            ConflictSeverity::Minor => 1.0,
        };

        let score = |proposal: &str, tier: f64| -> f64 {
            let quality = (proposal.len() as f64 / 50.0).min(5.0);
            tier * 0.4 + severity_weight * 0.4 + quality * 0.2
        };

        let score_a = score(&conflict.proposal_a, agent_tier(&conflict.agent_a));
        let score_b = score(&conflict.proposal_b, agent_tier(&conflict.agent_b));

        if score_a >= score_b {
            conflict.proposal_a.clone()
        } else {
            conflict.proposal_b.clone()
        }
    }

    /// 全维度并行分析：调度全部 10 个 Agent，每个用其主 TaskType。
    ///
    /// 用于"一键全面分析"模式——并行执行所有 Agent，
    /// 解析 findings、entity 并返回聚合结果。
    pub async fn run_full_parallel(
        &self,
        ctx: &mut SharedContext,
        registry: &AgentRegistry,
        llm: Arc<dyn LlmClient>,
        observer: Option<&dyn AnalysisObserver>,
    ) -> CoreResult<AnalysisResult> {
        let all_agents = AgentId::all();
        let agent_task_types: HashMap<AgentId, TaskType> = all_agents
            .iter()
            .map(|id| (*id, Self::task_type_for_agent(id)))
            .collect();

        let (outputs, usages, _success_count) = run_parallel(
            &all_agents,
            ctx,
            registry,
            Arc::clone(&llm),
            &agent_task_types,
            observer,
        )
        .await;

        // 回写 ctx
        for (id, ref output) in &outputs {
            ctx.record_output(*id, output.clone());
        }

        let findings = parse_findings(&outputs, &ctx.chapter_text);
        let total_cost_usd = usages.iter().map(|(_, u)| u.cost_usd).sum();
        let total_latency_ms = usages.iter().map(|(_, u)| u.latency_ms as u64).sum();

        if let Some(obs) = observer {
            obs.on_analysis_complete(
                "",
                total_cost_usd,
                total_latency_ms,
                all_agents.len() as u32,
                findings.len() as u32,
            );
            for f in &findings {
                if let Some(ref suggestion) = f.suggestion {
                    obs.on_proposal_ready(
                        &uuid::Uuid::new_v4().to_string(),
                        &f.agent_id,
                        &f.title,
                        &format!("{:?}", f.severity),
                        f.location,
                        suggestion,
                    );
                }
            }
        }

        let (extracted_characters, extracted_locations) =
            extract_entities(&outputs, &ctx.project_id, ctx.chapter_id.as_deref());

        Ok(AnalysisResult {
            agent_outputs: outputs,
            topology: AgentTopology::Parallel {
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
                    AgentId::EntityExtract,
                ],
            },
            complexity: TaskComplexity::FullScene,
            findings,
            usages,
            total_cost_usd,
            total_latency_ms,
            extracted_characters,
            extracted_locations,
        })
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
        llm: Arc<dyn LlmClient>,
        observer: Option<&dyn AnalysisObserver>,
    ) -> CoreResult<AnalysisResult> {
        let text_length = ctx.chapter_text.len();
        let complexity = self.predict_complexity(request.task_type, text_length);
        let mut topology = self.select_topology(request.task_type, complexity);
        let mut upgrade_round = 0;

        loop {
            // 构建 per-agent task type map：每个 Agent 拿到自己的主 TaskType
            let agent_task_types: HashMap<AgentId, TaskType> = topology
                .agent_ids()
                .into_iter()
                .map(|id| (id, Orchestrator::task_type_for_agent(&id)))
                .collect();

            // ── 按拓扑分派执行 ──
            let (outputs, usages, success_count) = match &topology {
                AgentTopology::Single(id) => {
                    run_serial(&[*id], ctx, registry, Arc::clone(&llm), &agent_task_types, observer).await
                }
                AgentTopology::Serial { agents } => {
                    run_serial(agents, ctx, registry, Arc::clone(&llm), &agent_task_types, observer).await
                }
                AgentTopology::Parallel { agents } => {
                    let (outputs, usages, success_count) = run_parallel(
                        agents, ctx, registry, Arc::clone(&llm), &agent_task_types, observer,
                    )
                    .await;
                    // 回写 ctx（升级轮次需要前序产出）
                    for (id, ref output) in &outputs {
                        ctx.record_output(*id, output.clone());
                    }
                    (outputs, usages, success_count)
                }
                AgentTopology::HermesCouncil { analysts, chair } => {
                    // Phase 1: 并行分析 → Phase 2: Chair 串行综合
                    let (mut outputs, mut usages, success) = run_parallel(
                        analysts, ctx, registry, Arc::clone(&llm), &agent_task_types, observer,
                    )
                    .await;
                    // 记录 analyst 产出到 ctx
                    for (id, ref output) in &outputs {
                        ctx.record_output(*id, output.clone());
                    }
                    // Chair 综合
                    let (chair_outputs, chair_usages, chair_success) = run_serial(
                        &[*chair], ctx, registry, Arc::clone(&llm), &agent_task_types, observer,
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
                let mut findings = parse_findings(&outputs, &ctx.chapter_text);

                // ── Phase 4-5: Hermes Council 冲突裁决 + 最终裁定 ──
                if matches!(topology, AgentTopology::HermesCouncil { .. })
                    && self.enable_reflection
                {
                    let (conflict_findings, agent_conflicts) = detect_conflicts(&findings);
                    if !agent_conflicts.is_empty() {
                        // Phase 4: 将冲突 finding 追加到结果
                        findings.extend(conflict_findings);

                        // Phase 5: 对每个冲突调 resolve_conflict 加权裁决
                        let resolutions: Vec<String> = agent_conflicts
                            .iter()
                            .map(|ac| {
                                let winner = self.resolve_conflict(ac);
                                format!(
                                    "[{:?}] {:?} vs {:?} → 裁决: {}",
                                    ac.severity, ac.agent_a, ac.agent_b, winner
                                )
                            })
                            .collect();

                        findings.push(AgentFinding {
                            agent_id: "HermesCouncil".into(),
                            severity: Severity::Info,
                            title: "[RULING] Hermes Council 最终裁决".into(),
                            description: resolutions.join("\n"),
                            location: None,
                            suggestion: Some(format!(
                                "以上 {} 个冲突已通过加权评分自动裁决，请人工审核确认。",
                                agent_conflicts.len()
                            )),
                            timestamp: chrono::Utc::now()
                                .format("%Y-%m-%dT%H:%M:%SZ")
                                .to_string(),
                        });
                    }
                }
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
                    // 为每个有建议的 finding 发射 proposal:ready
                    for f in &findings {
                        if let Some(ref suggestion) = f.suggestion {
                            obs.on_proposal_ready(
                                &format!("{}-{}", request.request_id, f.title),
                                &f.agent_id,
                                &f.title,
                                &format!("{:?}", f.severity),
                                f.location,
                                suggestion,
                            );
                        }
                    }
                }

                let (extracted_characters, extracted_locations) =
                    extract_entities(&outputs, &ctx.project_id, ctx.chapter_id.as_deref());

                return Ok(AnalysisResult {
                    agent_outputs: outputs,
                    topology,
                    complexity,
                    findings,
                    usages,
                    total_cost_usd,
                    total_latency_ms,
                    extracted_characters,
                    extracted_locations,
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
                let (extracted_characters, extracted_locations) =
                    extract_entities(&outputs, &ctx.project_id, ctx.chapter_id.as_deref());
                return Ok(AnalysisResult {
                    agent_outputs: outputs,
                    topology,
                    complexity,
                    findings,
                    usages,
                    total_cost_usd: 0.0,
                    total_latency_ms: 0,
                    extracted_characters,
                    extracted_locations,
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
    use std::collections::HashMap;
    use xmgl_core::{CoreError, LLMCallResponse};

    // Phase K: FailingMockLlmClient 替代 PythonBridge 用于无 sidecar 环境测试。
    struct FailingMockLlmClient;

    #[async_trait::async_trait]
    impl LlmClient for FailingMockLlmClient {
        async fn call_agent(
            &self,
            _prompt_key: &str,
            _variables: &HashMap<String, String>,
            _task_type: TaskType,
        ) -> CoreResult<LLMCallResponse> {
            Err(CoreError::Internal("mock failure".into()))
        }
    }

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
            AgentTopology::Serial { agents } => assert_eq!(agents.len(), 10),
            _ => panic!("Expected Serial with all 10 agents"),
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
            agent_a: AgentId::Character,
            agent_b: AgentId::World,
            description: "角色位置矛盾".into(),
            proposal_a: "方案A: 角色在屋内".into(),
            proposal_b: "方案B: 角色在花园".into(),
            severity: ConflictSeverity::Moderate,
        };
        let resolved = orch.resolve_conflict(&conflict);
        // Character (Pro=3.0) vs World (Flash=1.0) — same length, Character wins
        assert_eq!(resolved, "方案A: 角色在屋内");
    }

    #[test]
    fn test_resolve_conflict_tier_matters() {
        let orch = Orchestrator::new();
        // Two Flash agents, identical proposal length → tie broken by scoring order (a >= b)
        let conflict = AgentConflict {
            agent_a: AgentId::World,
            agent_b: AgentId::Economy,
            description: "资源冲突".into(),
            proposal_a: "A".into(),
            proposal_b: "B".into(),
            severity: ConflictSeverity::Minor,
        };
        let resolved = orch.resolve_conflict(&conflict);
        // Both Flash=1.0, same length → score_a >= score_b → returns proposal_a
        assert_eq!(resolved, "A");
    }

    // ── ranges_overlap ──

    #[test]
    fn test_ranges_overlap_exact_match() {
        let a = TextRange {
            start_line: 10, start_column: 5, end_line: 12, end_column: 10,
            start_byte: 0, end_byte: 50,
        };
        let b = a;
        assert!(ranges_overlap(a, b));
    }

    #[test]
    fn test_ranges_overlap_partial_same_lines() {
        let a = TextRange {
            start_line: 5, start_column: 0, end_line: 8, end_column: 20,
            start_byte: 0, end_byte: 100,
        };
        let b = TextRange {
            start_line: 7, start_column: 0, end_line: 10, end_column: 5,
            start_byte: 50, end_byte: 150,
        };
        assert!(ranges_overlap(a, b));
    }

    #[test]
    fn test_ranges_overlap_non_overlapping_lines() {
        let a = TextRange {
            start_line: 1, start_column: 0, end_line: 3, end_column: 0,
            start_byte: 0, end_byte: 30,
        };
        let b = TextRange {
            start_line: 5, start_column: 0, end_line: 8, end_column: 0,
            start_byte: 40, end_byte: 80,
        };
        assert!(!ranges_overlap(a, b));
    }

    #[test]
    fn test_ranges_overlap_same_line_adjacent_non_overlapping() {
        let a = TextRange {
            start_line: 3, start_column: 0, end_line: 3, end_column: 10,
            start_byte: 0, end_byte: 10,
        };
        let b = TextRange {
            start_line: 3, start_column: 11, end_line: 3, end_column: 20,
            start_byte: 11, end_byte: 20,
        };
        // a ends at col 10, b starts at col 11 → non-overlapping
        assert!(!ranges_overlap(a, b));
    }

    #[test]
    fn test_ranges_overlap_touching_lines() {
        let a = TextRange {
            start_line: 1, start_column: 0, end_line: 5, end_column: 10,
            start_byte: 0, end_byte: 50,
        };
        let b = TextRange {
            start_line: 5, start_column: 5, end_line: 8, end_column: 0,
            start_byte: 45, end_byte: 80,
        };
        // a ends at line 5 col 10, b starts at line 5 col 5 → same line, overlapping
        assert!(ranges_overlap(a, b));
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
        // 禁用升级以避免多次重试
        let mut orch = Orchestrator::new();
        orch.max_upgrade_rounds = 0;
        let registry = AgentRegistry::with_all_agents();
        let llm = Arc::new(FailingMockLlmClient) as Arc<dyn LlmClient>;
        let mut ctx = SharedContext::new("p1", "测试文本");

        let request = AnalysisRequest {
            request_id: "req-test".into(),
            task_type: TaskType::PadCompute,
            trigger: AnalysisTrigger::Manual,
            chapter_ids: vec![],
            context_note: None,
        };

        let result = orch.run_analysis(&request, &mut ctx, &registry, llm, None).await;
        match result {
            Ok(ar) => {
                // 无升级 → Moderate → Serial(3) → 全部失败但直接返回
                assert!(!ar.agent_outputs.is_empty());
                for (_, output) in &ar.agent_outputs {
                    assert!(output.contains("error"));
                }
            }
            Err(_) => {
                // LLM 客户端级别错误也是可接受的
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
            extracted_characters: vec![],
            extracted_locations: vec![],
        };
        assert_eq!(result.agent_outputs.len(), 1);
        assert_eq!(result.complexity, TaskComplexity::Simple);
    }
}
