//! xmgl-agent — Agent trait、注册表、生命周期管理、9 个 Agent 实现
//!
//! Phase B: 定义 Agent trait、AgentRegistry、SharedContext、Agent 骨架。
//! Phase C: 填充各 Agent 的实际分析逻辑。
//! Phase D: 扩展 build_variables，不同 Agent 传不同变量。

use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use xmgl_core::{AgentId, CoreResult, LLMUsage, LlmClient, ModelTier, ProjectContext, TaskType};

// =========================================================================
// SharedContext — Agent 间共享上下文
// =========================================================================

/// Agent 间共享的只读上下文。
///
/// Orchestrator 在每一轮分析开始前填充此结构，
/// Agent 通过它获取当前项目/章节信息以及前序 Agent 的产出。
#[derive(Debug, Clone)]
pub struct SharedContext {
    /// 当前项目 ID
    pub project_id: String,
    /// 当前章节 ID（可选）
    pub chapter_id: Option<String>,
    /// 当前章节标题
    pub chapter_title: Option<String>,
    /// 当前章节全文
    pub chapter_text: String,
    /// 前序 Agent 的分析产出：`AgentId → 产出文本`
    pub outputs: HashMap<AgentId, String>,
    /// 附加元数据（世界设定、角色档案等）
    pub metadata: HashMap<String, String>,
}

impl SharedContext {
    /// 创建新的空上下文。
    pub fn new(project_id: &str, chapter_text: &str) -> Self {
        Self {
            project_id: project_id.to_string(),
            chapter_id: None,
            chapter_title: None,
            chapter_text: chapter_text.to_string(),
            outputs: HashMap::new(),
            metadata: HashMap::new(),
        }
    }

    /// 设置章节 ID。
    pub fn with_chapter(mut self, chapter_id: &str) -> Self {
        self.chapter_id = Some(chapter_id.to_string());
        self
    }

    /// 设置章节标题。
    pub fn with_title(mut self, title: &str) -> Self {
        self.chapter_title = Some(title.to_string());
        self
    }

    /// 添加元数据。
    pub fn with_metadata(mut self, key: &str, value: &str) -> Self {
        self.metadata.insert(key.to_string(), value.to_string());
        self
    }

    /// 记录某个 Agent 的分析产出。
    pub fn record_output(&mut self, agent_id: AgentId, output: String) {
        self.outputs.insert(agent_id, output);
    }

    /// 读取某个 Agent 的分析产出。
    pub fn get_output(&self, agent_id: AgentId) -> Option<&str> {
        self.outputs.get(&agent_id).map(|s| s.as_str())
    }

    /// 从 ProjectContext 注入创作上下文到 metadata。
    ///
    /// 将 ProjectContext 各 section 序列化为字符串，写入 `self.metadata`。
    /// 使用 `entry().or_insert()` 确保不覆盖已有值（用户手动传入的 metadata 优先）。
    /// 空 section 不写入。
    pub fn enrich_with_project_context(&mut self, pctx: &ProjectContext) {
        // world_rules — 拼接所有字段
        if let Some(ref wr) = pctx.world_rules {
            let mut parts = Vec::new();
            if !wr.magic_system.is_empty() {
                parts.push(format!("力量体系: {}", wr.magic_system));
            }
            if !wr.technology_level.is_empty() {
                parts.push(format!("技术水平: {}", wr.technology_level));
            }
            if !wr.social_structure.is_empty() {
                parts.push(format!("社会结构: {}", wr.social_structure));
            }
            if !wr.geography.is_empty() {
                parts.push(format!("地理: {}", wr.geography));
            }
            for rule in &wr.custom_rules {
                parts.push(format!("自定义规则: {}", rule));
            }
            if !parts.is_empty() {
                self.metadata
                    .entry("world_rules".into())
                    .or_insert(parts.join("\n"));
            }
        }

        // character_profiles — JSON 数组字符串
        if !pctx.character_profiles.is_empty() {
            let json = serde_json::to_string(&pctx.character_profiles).unwrap_or_default();
            self.metadata
                .entry("character_profiles".into())
                .or_insert(json);
        }

        // plot_outline
        if let Some(ref po) = pctx.plot_outline {
            let mut parts = Vec::new();
            if !po.main_plot.is_empty() {
                parts.push(format!("主线: {}", po.main_plot));
            }
            for sub in &po.subplots {
                parts.push(format!("支线: {}", sub));
            }
            for fs in &po.foreshadow_plan {
                parts.push(format!("伏笔规划: {}", fs));
            }
            for co in &po.chapter_outlines {
                parts.push(format!(
                    "第{}章: {} | 关键事件: {}",
                    co.chapter_index,
                    co.summary,
                    co.key_events.join("、")
                ));
            }
            if !parts.is_empty() {
                self.metadata
                    .entry("plot_outline".into())
                    .or_insert(parts.join("\n"));
            }
        }

        // style_guide
        if let Some(ref sg) = pctx.style_guide {
            let mut parts = Vec::new();
            if !sg.prose_style.is_empty() {
                parts.push(format!("文体风格: {}", sg.prose_style));
            }
            if !sg.sentence_preferences.is_empty() {
                parts.push(format!("句式偏好: {}", sg.sentence_preferences));
            }
            if !sg.dialogue_conventions.is_empty() {
                parts.push(format!("对话惯例: {}", sg.dialogue_conventions));
            }
            if !sg.narrative_distance.is_empty() {
                parts.push(format!("叙事距离: {}", sg.narrative_distance));
            }
            if !parts.is_empty() {
                self.metadata
                    .entry("style_guide".into())
                    .or_insert(parts.join("\n"));
            }
        }

        // theme_map
        if let Some(ref tm) = pctx.theme_map {
            // theme_keywords — 主要主题
            if !tm.primary_themes.is_empty() {
                self.metadata
                    .entry("theme_keywords".into())
                    .or_insert(tm.primary_themes.join(", "));
            }
            // genre — 第一个主题作为体裁标签
            if let Some(first_theme) = tm.primary_themes.first() {
                self.metadata
                    .entry("genre".into())
                    .or_insert(first_theme.clone());
            }
            // imagery_keywords — 意象母题
            if !tm.imagery_motifs.is_empty() {
                self.metadata
                    .entry("imagery_keywords".into())
                    .or_insert(tm.imagery_motifs.join(", "));
            }
        }
    }
}

// =========================================================================
// Agent trait
// =========================================================================

/// 所有 Agent 的统一接口。
///
/// 每个 Agent 实现此 trait，由 Orchestrator 统一调度。
#[async_trait]
pub trait Agent: Send + Sync {
    /// Agent 标识。
    fn id(&self) -> AgentId;

    /// 中文显示名。
    fn name(&self) -> &'static str;

    /// 该 Agent 使用的模型级别。
    fn model_tier(&self) -> ModelTier;

    /// 核心路由：根据 TaskType 返回对应的 prompt key。
    ///
    /// 一个 Agent 可以处理多种 TaskType，每种对应不同的 system prompt。
    /// 这解决了 17 个 prompt 模板中 7 个死代码的问题（TG 3b）。
    fn prompt_key_for(&self, task_type: TaskType) -> &'static str;

    /// 每个 Agent 的默认分析维度。
    fn default_task_type(&self) -> TaskType;

    /// 默认 prompt key（向后兼容）。
    fn default_prompt_key(&self) -> &'static str;

    /// Agent 使用的 prompt key（委托给 `default_prompt_key()`）。
    fn prompt_key(&self) -> &'static str {
        self.default_prompt_key()
    }

    /// 执行分析。
    ///
    /// `ctx` 包含当前项目/章节信息及前序 Agent 产出。
    /// `llm` 为 LLM 客户端（实现 `LlmClient` trait）。
    /// `task_type` 动态选择 prompt key。
    /// 返回分析结果文本和可选的 LLM 用量统计。
    async fn analyze(
        &self, ctx: &SharedContext, llm: Arc<dyn LlmClient>, task_type: TaskType,
    ) -> CoreResult<(String, Option<LLMUsage>)>;

    /// 构造 prompt 模板变量。
    fn build_variables(&self, ctx: &SharedContext) -> HashMap<String, String>;

    /// 是否启用（可在运行时关闭）。
    fn enabled(&self) -> bool {
        true
    }
}

// =========================================================================
// AgentRegistry
// =========================================================================

/// Agent 注册表 — 集中管理所有 Agent 实例。
///
/// 支持按 `AgentId` 查找，供 Orchestrator 调度使用。
pub struct AgentRegistry {
    agents: HashMap<AgentId, Arc<dyn Agent>>,
}

impl AgentRegistry {
    /// 创建空的注册表。
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }

    /// 注册一个 Agent。
    pub fn register(&mut self, agent: Arc<dyn Agent>) {
        self.agents.insert(agent.id(), agent);
    }

    /// 按 ID 获取 Agent（返回 Arc 以支持跨任务共享）。
    pub fn get(&self, id: AgentId) -> Option<Arc<dyn Agent>> {
        self.agents.get(&id).cloned()
    }

    /// 列出所有已注册 Agent 的 ID。
    pub fn list_all(&self) -> Vec<AgentId> {
        let mut ids: Vec<AgentId> = self.agents.keys().copied().collect();
        ids.sort_by_key(|id| id.name());
        ids
    }

    /// 已注册 Agent 数量。
    pub fn len(&self) -> usize {
        self.agents.len()
    }

    /// 注册表是否为空。
    pub fn is_empty(&self) -> bool {
        self.agents.is_empty()
    }

    /// 创建默认注册表 — 包含全部 9 个 Agent 的骨架实例。
    pub fn with_all_agents() -> Self {
        let mut registry = Self::new();
        registry.register(Arc::new(CharacterAgent));
        registry.register(Arc::new(WorldAgent));
        registry.register(Arc::new(NarrativeAgent));
        registry.register(Arc::new(ProseAgent));
        registry.register(Arc::new(ThemeAgent));
        registry.register(Arc::new(EconomyAgent));
        registry.register(Arc::new(ReaderExpectationAgent));
        registry.register(Arc::new(ConceptionAgent));
        registry.register(Arc::new(EditorInChiefAgent));
        registry.register(Arc::new(EntityExtractAgent));
        registry
    }
}

impl Default for AgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// =========================================================================
// 共享辅助函数
// =========================================================================

/// 从 SharedContext 收集所有前序 Agent 输出为汇总文本。
fn collect_prior_outputs(ctx: &SharedContext) -> String {
    if ctx.outputs.is_empty() {
        return "（无前序输出）".into();
    }
    ctx.outputs
        .iter()
        .map(|(id, output)| format!("[{}] {}", id.name(), output))
        .collect::<Vec<_>>()
        .join("\n\n")
}

// =========================================================================
// Agent 宏（带通用 analyze 实现）
// =========================================================================

macro_rules! agent_impl {
    ($name:ident, $id:expr, $display:expr, $tier:expr,
     $default_task_type:expr, $default_prompt_key:expr,
     |$tt:ident| $route_body:expr,
     |$ctx:ident| $body:expr) => {
        pub struct $name;

        #[async_trait]
        impl Agent for $name {
            fn id(&self) -> AgentId {
                $id
            }

            fn name(&self) -> &'static str {
                $display
            }

            fn model_tier(&self) -> ModelTier {
                $tier
            }

            fn default_task_type(&self) -> TaskType {
                $default_task_type
            }

            fn default_prompt_key(&self) -> &'static str {
                $default_prompt_key
            }

            fn prompt_key_for(&self, $tt: TaskType) -> &'static str {
                $route_body
            }

            fn build_variables(&self, $ctx: &SharedContext) -> HashMap<String, String> {
                $body
            }

            async fn analyze(
                &self,
                ctx: &SharedContext,
                llm: Arc<dyn LlmClient>,
                task_type: TaskType,
            ) -> CoreResult<(String, Option<LLMUsage>)> {
                let vars = self.build_variables(ctx);
                let response = llm
                    .call_agent(self.prompt_key_for(task_type), &vars, task_type)
                    .await?;
                if response.success {
                    let output = response
                        .result
                        .map(|v| v.to_string())
                        .unwrap_or_default();
                    Ok((output, response.usage))
                } else {
                    Err(xmgl_core::CoreError::Internal(
                        response.error.unwrap_or_else(|| "LLM call failed".into()),
                    ))
                }
            }
        }
    };
}

// ── CharacterAgent: PAD 情感计算 + 角色分析 ──
agent_impl!(CharacterAgent, AgentId::Character, "角色 Agent", ModelTier::Pro,
    TaskType::PadCompute, "pad_compute",
    |tt| match tt {
        TaskType::PadCompute => "pad_compute",
        TaskType::ActionInfer => "action_infer",
        TaskType::EntityExtract => "entity_extract",
        _ => "pad_compute",
    },
    |ctx| {
    let mut vars = HashMap::new();
    // 注意：format_pad_prompt 读取 "scene_text"，不是 "chapter_text"
    vars.insert("scene_text".into(), ctx.chapter_text.clone());
    if let Some(ref title) = ctx.chapter_title {
        vars.insert("chapter_title".into(), title.clone());
    }
    if let Some(profiles) = ctx.metadata.get("character_profiles") {
        vars.insert("character_profiles".into(), profiles.clone());
    }
    // 角色 ID — 用于聚焦分析对象
    if let Some(char_id) = ctx.metadata.get("character_id") {
        vars.insert("character_id".into(), char_id.clone());
    }
    // 语料参考 — 同类角色的历史行为
    if let Some(corpus) = ctx.metadata.get("corpus_context") {
        vars.insert("corpus_context".into(), corpus.clone());
    }
    // 情感标记 — 已知的情感线索
    if let Some(note) = ctx.metadata.get("emotion_note") {
        vars.insert("emotion_note".into(), note.clone());
    }
    vars
});

// ── WorldAgent: 世界规则 + 空间检查 ──
agent_impl!(WorldAgent, AgentId::World, "世界 Agent", ModelTier::Flash,
    TaskType::RuleCheck, "rule_check",
    |tt| match tt {
        TaskType::RuleCheck => "rule_check",
        TaskType::SpatialCheck => "spatial_check",
        _ => "rule_check",
    },
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(rules) = ctx.metadata.get("world_rules") {
        vars.insert("world_rules".into(), rules.clone());
    }
    vars
});

// ── NarrativeAgent: 叙事分析 + 伏笔检测 ──
agent_impl!(NarrativeAgent, AgentId::Narrative, "叙事 Agent", ModelTier::Pro,
    TaskType::ForeshadowDetect, "foreshadow_detect",
    |tt| match tt {
        TaskType::ForeshadowDetect => "foreshadow_detect",
        TaskType::CausalExtract => "causal_extract",
        TaskType::ResolutionCheck => "resolution_check",
        TaskType::EventPredict => "event_predict",
        _ => "foreshadow_detect",
    },
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(outline) = ctx.metadata.get("plot_outline") {
        vars.insert("plot_outline".into(), outline.clone());
    }
    if let Some(char_output) = ctx.get_output(AgentId::Character) {
        vars.insert("character_analysis".into(), char_output.to_string());
    }
    vars
});

// ── ProseAgent: 文体检查 + 寄存器检查 ──
agent_impl!(ProseAgent, AgentId::Prose, "文辞 Agent", ModelTier::Flash,
    TaskType::StyleCheck, "style_check",
    |tt| match tt {
        TaskType::StyleCheck => "style_check",
        TaskType::RegisterCheck => "register_check",
        _ => "style_check",
    },
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(guide) = ctx.metadata.get("style_guide") {
        vars.insert("style_guide".into(), guide.clone());
    }
    vars
});

// ── ThemeAgent: 主题提取 ──
agent_impl!(ThemeAgent, AgentId::Theme, "主题 Agent", ModelTier::Pro,
    TaskType::ThemeExtract, "theme_extract",
    |_tt| "theme_extract",
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(keywords) = ctx.metadata.get("theme_keywords") {
        vars.insert("theme_keywords".into(), keywords.clone());
    }
    vars
});

// ── EconomyAgent: 经济性检查 ──
agent_impl!(EconomyAgent, AgentId::Economy, "经济 Agent", ModelTier::Flash,
    TaskType::EconomyCheck, "economy_check",
    |_tt| "economy_check",
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    vars.insert("word_count".into(), ctx.chapter_text.len().to_string());
    vars
});

// ── ReaderExpectationAgent: 读者预期分析 ──
agent_impl!(ReaderExpectationAgent, AgentId::ReaderExpectation, "预期 Agent", ModelTier::Flash,
    TaskType::ExpectationAnalyze, "expectation_analyze",
    |_tt| "expectation_analyze",
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(genre) = ctx.metadata.get("genre") {
        vars.insert("genre".into(), genre.clone());
    }
    vars
});

// ── ConceptionAgent: 意象检测 ──
agent_impl!(ConceptionAgent, AgentId::Conception, "构思 Agent", ModelTier::Flash,
    TaskType::ImageryDetect, "imagery_detect",
    |_tt| "imagery_detect",
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(keywords) = ctx.metadata.get("imagery_keywords") {
        vars.insert("imagery_keywords".into(), keywords.clone());
    }
    vars
});

// ── EditorInChiefAgent: 总编 — 汇总所有前序输出 ──
agent_impl!(EditorInChiefAgent, AgentId::EditorInChief, "总编 Agent", ModelTier::Pro,
    TaskType::SceneAnalysis, "scene_analysis",
    |tt| match tt {
        TaskType::SceneAnalysis => "scene_analysis",
        TaskType::Rerank => "rerank",
        _ => "scene_analysis",
    },
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    let prior = collect_prior_outputs(ctx);
    vars.insert("agent_outputs".into(), prior);
    vars
});

// ── EntityExtractAgent: 实体提取 — Phase L1 ──
agent_impl!(EntityExtractAgent, AgentId::EntityExtract, "实体提取 Agent", ModelTier::Flash,
    TaskType::EntityExtract, "entity_extract",
    |_tt| "entity_extract",
    |ctx| {
    let mut vars = HashMap::new();
    vars.insert("chapter_text".into(), ctx.chapter_text.clone());
    if let Some(ref title) = ctx.chapter_title {
        vars.insert("chapter_title".into(), title.clone());
    }
    vars
});

// =========================================================================
// Tests
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    // ── SharedContext ──

    #[test]
    fn test_shared_context_new() {
        let ctx = SharedContext::new("p1", "hello world");
        assert_eq!(ctx.project_id, "p1");
        assert_eq!(ctx.chapter_text, "hello world");
        assert!(ctx.chapter_id.is_none());
        assert!(ctx.chapter_title.is_none());
        assert!(ctx.outputs.is_empty());
        assert!(ctx.metadata.is_empty());
    }

    #[test]
    fn test_shared_context_with_chapter() {
        let ctx = SharedContext::new("p1", "text").with_chapter("ch1");
        assert_eq!(ctx.chapter_id.unwrap(), "ch1");
    }

    #[test]
    fn test_shared_context_with_title() {
        let ctx = SharedContext::new("p1", "text").with_title("第一章");
        assert_eq!(ctx.chapter_title.unwrap(), "第一章");
    }

    #[test]
    fn test_shared_context_with_metadata() {
        let ctx = SharedContext::new("p1", "text")
            .with_metadata("genre", "武侠")
            .with_metadata("style_guide", "简洁有力");
        assert_eq!(ctx.metadata.get("genre").unwrap(), "武侠");
        assert_eq!(ctx.metadata.get("style_guide").unwrap(), "简洁有力");
    }

    #[test]
    fn test_shared_context_record_and_get_output() {
        let mut ctx = SharedContext::new("p1", "text");
        ctx.record_output(AgentId::Character, r#"{"pleasure": 0.8}"#.into());
        assert!(ctx.get_output(AgentId::Character).is_some());
        assert!(ctx.get_output(AgentId::World).is_none());
    }

    // ── Agent trait ──

    #[test]
    fn test_agent_stub_ids() {
        let agents: Vec<Arc<dyn Agent>> = vec![
            Arc::new(CharacterAgent),
            Arc::new(WorldAgent),
            Arc::new(NarrativeAgent),
            Arc::new(ProseAgent),
            Arc::new(ThemeAgent),
            Arc::new(EconomyAgent),
            Arc::new(ReaderExpectationAgent),
            Arc::new(ConceptionAgent),
            Arc::new(EditorInChiefAgent),
            Arc::new(EntityExtractAgent),
        ];

        let ids: Vec<AgentId> = agents.iter().map(|a| a.id()).collect();
        assert_eq!(ids.len(), 10);
        assert!(ids.contains(&AgentId::Character));
        assert!(ids.contains(&AgentId::EditorInChief));
    }

    #[test]
    fn test_agent_model_tiers() {
        let char_agent = CharacterAgent;
        let world_agent = WorldAgent;
        assert_eq!(char_agent.model_tier(), ModelTier::Pro);
        assert_eq!(world_agent.model_tier(), ModelTier::Flash);
    }

    #[test]
    fn test_agent_enabled_default() {
        assert!(CharacterAgent.enabled());
    }

    #[test]
    fn test_agent_prompt_keys() {
        assert_eq!(CharacterAgent.prompt_key(), "pad_compute");
        assert_eq!(WorldAgent.prompt_key(), "rule_check");
        assert_eq!(NarrativeAgent.prompt_key(), "foreshadow_detect");
        assert_eq!(EditorInChiefAgent.prompt_key(), "scene_analysis");
    }

    #[test]
    fn test_agent_build_variables() {
        let ctx = SharedContext::new("p1", "测试文本内容");
        let vars = CharacterAgent.build_variables(&ctx);
        assert_eq!(vars.get("scene_text").unwrap(), "测试文本内容");
        // CharacterAgent 不传 chapter_title（未设置）
        assert!(!vars.contains_key("chapter_title"));
    }

    #[test]
    fn test_agent_build_variables_with_metadata() {
        let ctx = SharedContext::new("p1", "测试文本")
            .with_title("第一章")
            .with_metadata("character_profiles", "贾宝玉: 17岁");
        let vars = CharacterAgent.build_variables(&ctx);
        assert_eq!(vars.get("chapter_title").unwrap(), "第一章");
        assert_eq!(vars.get("character_profiles").unwrap(), "贾宝玉: 17岁");
    }

    #[test]
    fn test_editor_in_chief_receives_prior_outputs() {
        let mut ctx = SharedContext::new("p1", "测试文本");
        ctx.record_output(AgentId::Character, r#"{"pleasure": 0.8}"#.into());
        ctx.record_output(AgentId::World, r#"{"valid": true}"#.into());
        let vars = EditorInChiefAgent.build_variables(&ctx);
        let prior = vars.get("agent_outputs").unwrap();
        assert!(prior.contains("角色 Agent"));
        assert!(prior.contains("世界 Agent"));
    }

    #[test]
    fn test_economy_agent_includes_word_count() {
        let ctx = SharedContext::new("p1", "测试文本");
        let vars = EconomyAgent.build_variables(&ctx);
        assert!(vars.contains_key("word_count"));
    }

    #[test]
    fn test_narrative_agent_receives_character_output() {
        let mut ctx = SharedContext::new("p1", "测试文本");
        ctx.record_output(AgentId::Character, r#"{"pleasure": 0.8}"#.into());
        let vars = NarrativeAgent.build_variables(&ctx);
        assert!(vars.contains_key("character_analysis"));
    }

    #[test]
    fn test_agent_id_as_task_type_str() {
        assert_eq!(AgentId::Character.as_task_type_str(), "pad_compute");
        assert_eq!(AgentId::World.as_task_type_str(), "rule_check");
        assert_eq!(AgentId::Narrative.as_task_type_str(), "foreshadow_detect");
        assert_eq!(AgentId::Theme.as_task_type_str(), "theme_extract");
    }

    // ── AgentRegistry ──

    #[test]
    fn test_registry_empty() {
        let reg = AgentRegistry::new();
        assert!(reg.is_empty());
        assert_eq!(reg.len(), 0);
    }

    #[test]
    fn test_registry_register_and_get() {
        let mut reg = AgentRegistry::new();
        reg.register(Arc::new(CharacterAgent));

        let agent = reg.get(AgentId::Character).unwrap();
        assert_eq!(agent.id(), AgentId::Character);
        assert_eq!(agent.name(), "角色 Agent");
    }

    #[test]
    fn test_registry_list_all() {
        let mut reg = AgentRegistry::new();
        reg.register(Arc::new(CharacterAgent));
        reg.register(Arc::new(WorldAgent));
        reg.register(Arc::new(NarrativeAgent));

        let ids = reg.list_all();
        assert_eq!(ids.len(), 3);
    }

    #[test]
    fn test_registry_with_all_agents() {
        let reg = AgentRegistry::with_all_agents();
        assert_eq!(reg.len(), 10);
        assert!(reg.get(AgentId::Character).is_some());
        assert!(reg.get(AgentId::EditorInChief).is_some());
    }

    #[test]
    fn test_registry_get_nonexistent() {
        let reg = AgentRegistry::new();
        assert!(reg.get(AgentId::Character).is_none());
    }
}
