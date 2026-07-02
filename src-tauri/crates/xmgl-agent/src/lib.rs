//! xmgl-agent — Agent trait、注册表、生命周期管理、9 个 Agent 实现
//!
//! Phase B: 定义 Agent trait、AgentRegistry、SharedContext、Agent 骨架。
//! Phase C: 填充各 Agent 的实际分析逻辑。

use async_trait::async_trait;
use std::collections::HashMap;
use xmgl_python_bridge::PythonBridge;
use xmgl_core::{AgentId, CoreResult, ModelTier};

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
    /// 当前章节全文
    pub chapter_text: String,
    /// 前序 Agent 的分析产出：`AgentId → 产出文本`
    pub outputs: HashMap<AgentId, String>,
}

impl SharedContext {
    /// 创建新的空上下文。
    pub fn new(project_id: &str, chapter_text: &str) -> Self {
        Self {
            project_id: project_id.to_string(),
            chapter_id: None,
            chapter_text: chapter_text.to_string(),
            outputs: HashMap::new(),
        }
    }

    /// 设置章节 ID。
    pub fn with_chapter(mut self, chapter_id: &str) -> Self {
        self.chapter_id = Some(chapter_id.to_string());
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

    /// 执行分析。
    ///
    /// `ctx` 包含当前项目/章节信息及前序 Agent 产出。
    /// `bridge` 为 Python sidecar HTTP 客户端，用于调用 LLM。
    /// 返回分析结果文本（通常为 JSON）。
    async fn analyze(&self, ctx: &SharedContext, bridge: &mut PythonBridge) -> CoreResult<String>;

    /// Agent 使用的 prompt key（对应 Python 注册表）。
    fn prompt_key(&self) -> &'static str;

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
    agents: HashMap<AgentId, Box<dyn Agent>>,
}

impl AgentRegistry {
    /// 创建空的注册表。
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }

    /// 注册一个 Agent。
    pub fn register(&mut self, agent: Box<dyn Agent>) {
        self.agents.insert(agent.id(), agent);
    }

    /// 按 ID 获取 Agent。
    pub fn get(&self, id: AgentId) -> Option<&dyn Agent> {
        self.agents.get(&id).map(|a| a.as_ref())
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
        registry.register(Box::new(CharacterAgent));
        registry.register(Box::new(WorldAgent));
        registry.register(Box::new(NarrativeAgent));
        registry.register(Box::new(ProseAgent));
        registry.register(Box::new(ThemeAgent));
        registry.register(Box::new(EconomyAgent));
        registry.register(Box::new(ReaderExpectationAgent));
        registry.register(Box::new(ConceptionAgent));
        registry.register(Box::new(EditorInChiefAgent));
        registry
    }
}

impl Default for AgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// =========================================================================
// 9 个 Agent 骨架
// =========================================================================

macro_rules! agent_stub {
    ($name:ident, $id:expr, $display:expr, $tier:expr, $prompt_key:expr) => {
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

            fn prompt_key(&self) -> &'static str {
                $prompt_key
            }

            fn build_variables(&self, ctx: &SharedContext) -> HashMap<String, String> {
                let mut vars = HashMap::new();
                vars.insert("chapter_text".into(), ctx.chapter_text.clone());
                vars
            }

            async fn analyze(&self, ctx: &SharedContext, bridge: &mut PythonBridge) -> CoreResult<String> {
                let vars = self.build_variables(ctx);
                let response = bridge.call_agent(self.prompt_key(), &vars, $id.as_task_type_str()).await?;
                if response.success {
                    Ok(response.result.map(|v| v.to_string()).unwrap_or_default())
                } else {
                    Err(xmgl_core::CoreError::Internal(
                        response.error.unwrap_or_else(|| "LLM call failed".into()),
                    ))
                }
            }
        }
    };
}

agent_stub!(CharacterAgent, AgentId::Character, "角色 Agent", ModelTier::Pro, "pad_compute");
agent_stub!(WorldAgent, AgentId::World, "世界 Agent", ModelTier::Flash, "rule_check");
agent_stub!(NarrativeAgent, AgentId::Narrative, "叙事 Agent", ModelTier::Pro, "foreshadow_detect");
agent_stub!(ProseAgent, AgentId::Prose, "文辞 Agent", ModelTier::Flash, "style_check");
agent_stub!(ThemeAgent, AgentId::Theme, "主题 Agent", ModelTier::Pro, "theme_extract");
agent_stub!(EconomyAgent, AgentId::Economy, "经济 Agent", ModelTier::Flash, "economy_check");
agent_stub!(ReaderExpectationAgent, AgentId::ReaderExpectation, "预期 Agent", ModelTier::Flash, "expectation_analyze");
agent_stub!(ConceptionAgent, AgentId::Conception, "构思 Agent", ModelTier::Flash, "imagery_detect");
agent_stub!(EditorInChiefAgent, AgentId::EditorInChief, "总编 Agent", ModelTier::Pro, "scene_analysis");

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
        assert!(ctx.outputs.is_empty());
    }

    #[test]
    fn test_shared_context_with_chapter() {
        let ctx = SharedContext::new("p1", "text").with_chapter("ch1");
        assert_eq!(ctx.chapter_id.unwrap(), "ch1");
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
        let agents: Vec<Box<dyn Agent>> = vec![
            Box::new(CharacterAgent),
            Box::new(WorldAgent),
            Box::new(NarrativeAgent),
            Box::new(ProseAgent),
            Box::new(ThemeAgent),
            Box::new(EconomyAgent),
            Box::new(ReaderExpectationAgent),
            Box::new(ConceptionAgent),
            Box::new(EditorInChiefAgent),
        ];

        let ids: Vec<AgentId> = agents.iter().map(|a| a.id()).collect();
        assert_eq!(ids.len(), 9);
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
        assert_eq!(vars.get("chapter_text").unwrap(), "测试文本内容");
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
        reg.register(Box::new(CharacterAgent));

        let agent = reg.get(AgentId::Character).unwrap();
        assert_eq!(agent.id(), AgentId::Character);
        assert_eq!(agent.name(), "角色 Agent");
    }

    #[test]
    fn test_registry_list_all() {
        let mut reg = AgentRegistry::new();
        reg.register(Box::new(CharacterAgent));
        reg.register(Box::new(WorldAgent));
        reg.register(Box::new(NarrativeAgent));

        let ids = reg.list_all();
        assert_eq!(ids.len(), 3);
    }

    #[test]
    fn test_registry_with_all_agents() {
        let reg = AgentRegistry::with_all_agents();
        assert_eq!(reg.len(), 9);
        assert!(reg.get(AgentId::Character).is_some());
        assert!(reg.get(AgentId::EditorInChief).is_some());
    }

    #[test]
    fn test_registry_get_nonexistent() {
        let reg = AgentRegistry::new();
        assert!(reg.get(AgentId::Character).is_none());
    }
}
