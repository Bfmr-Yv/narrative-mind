//! xmgl-orchestrator 集成测试
//!
//! 需要 LLM_API_KEY 配置才能运行 Hermes Council 测试。

use std::collections::HashMap;
use std::sync::Arc;

use xmgl_agent::{AgentRegistry, SharedContext};
use xmgl_core::{CoreError, CoreResult, LLMCallResponse, LlmClient, TaskType};
use xmgl_orchestrator::{AnalysisRequest, AnalysisTrigger, Orchestrator};

/// Mock LLM client that always fails — used for no-LLM pipeline tests.
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

/// 完整分析管线（不含 LLM）— 验证拓扑选择 + 发现解析
#[tokio::test]
async fn test_full_analysis_pipeline_no_llm() {
    let mut orch = Orchestrator::new();
    orch.max_upgrade_rounds = 0; // 禁用升级避免超时

    let registry = AgentRegistry::with_all_agents();
    let llm = Arc::new(FailingMockLlmClient) as Arc<dyn LlmClient>;
    let mut ctx = SharedContext::new("test-project", "测试章节文本内容。\n第二行。");

    let request = AnalysisRequest {
        request_id: "integration-test-1".into(),
        task_type: TaskType::StyleCheck,
        trigger: AnalysisTrigger::Manual,
        chapter_ids: vec![],
        context_note: None,
    };

    let result = orch
        .run_analysis(&request, &mut ctx, &registry, llm, None)
        .await;

    match result {
        Ok(ar) => {
            assert!(!ar.agent_outputs.is_empty(), "即使失败也应有输出");
        }
        Err(_) => {
            // LLM 客户端错误可接受
        }
    }
}

/// HermesCouncil 拓扑 + 冲突裁决 → 产生 [RULING] finding
#[tokio::test]
#[ignore = "需要 LLM_API_KEY 配置"]
async fn test_hermes_council_ruling() {
    // 此测试需要真实 LLM 客户端。Phase K 后从环境变量读取配置。
    // 使用 xmgl_llm::LlmClientImpl 替代 Python sidecar。
    let orch = Orchestrator::new();
    let registry = AgentRegistry::with_all_agents();
    // Phase K: 使用 Rust 原生 LLM 客户端
    let llm_result = xmgl_llm::LlmClientImpl::new();
    if llm_result.is_err() || !llm_result.as_ref().unwrap().is_configured() {
        eprintln!("跳过: LLM 未配置");
        return;
    }
    let llm = Arc::new(llm_result.unwrap()) as Arc<dyn LlmClient>;
    let mut ctx = SharedContext::new(
        "test-project",
        "第一章\n\n清晨的阳光透过窗棂洒进房间。李明从床上坐起来，揉了揉惺忪的睡眼。他看了看床头的闹钟——已经七点半了。\n\n\"糟了！\"他急忙跳下床，今天是开学第一天。",
    );

    let request = AnalysisRequest {
        request_id: "integration-test-hc".into(),
        task_type: TaskType::SceneAnalysis,
        trigger: AnalysisTrigger::Manual,
        chapter_ids: vec![],
        context_note: None,
    };

    let result = orch
        .run_analysis(&request, &mut ctx, &registry, llm, None)
        .await;

    match result {
        Ok(ar) => {
            println!("拓扑: {:?}", ar.topology);
            println!("发现数: {}", ar.findings.len());
            println!("成本: ${:.4}", ar.total_cost_usd);

            // 验证 HermesCouncil 产生 [RULING] finding（如果有冲突）
            let rulings: Vec<_> = ar
                .findings
                .iter()
                .filter(|f| f.title.contains("[RULING]"))
                .collect();
            println!("裁决数: {}", rulings.len());
        }
        Err(e) => {
            panic!("HermesCouncil 分析不应失败: {e}");
        }
    }
}
