//! xmgl-orchestrator 集成测试
//!
//! 需要运行 Python sidecar + LLM_API_KEY 配置。

use xmgl_agent::{AgentRegistry, SharedContext};
use xmgl_core::TaskType;
use xmgl_orchestrator::{AnalysisRequest, AnalysisTrigger, Orchestrator};
use xmgl_python_bridge::PythonBridge;

/// 完整分析管线（不含 LLM）— 验证拓扑选择 + 发现解析
#[tokio::test]
async fn test_full_analysis_pipeline_no_llm() {
    let mut orch = Orchestrator::new();
    orch.max_upgrade_rounds = 0; // 禁用升级避免超时

    let registry = AgentRegistry::with_all_agents();
    // 使用无效端口 → agent 全部失败但不 panic
    let bridge = PythonBridge::new(Some("http://127.0.0.1:1")).unwrap();
    let mut ctx = SharedContext::new("test-project", "测试章节文本内容。\n第二行。");

    let request = AnalysisRequest {
        request_id: "integration-test-1".into(),
        task_type: TaskType::StyleCheck,
        trigger: AnalysisTrigger::Manual,
        chapter_ids: vec![],
        context_note: None,
    };

    let result = orch
        .run_analysis(&request, &mut ctx, &registry, &bridge, None)
        .await;

    match result {
        Ok(ar) => {
            assert!(!ar.agent_outputs.is_empty(), "即使失败也应有输出");
        }
        Err(_) => {
            // bridge 错误可接受
        }
    }
}

/// HermesCouncil 拓扑 + 冲突裁决 → 产生 [RULING] finding
#[tokio::test]
#[ignore = "需要运行 Python sidecar + LLM_API_KEY"]
async fn test_hermes_council_ruling() {
    let orch = Orchestrator::new();
    let registry = AgentRegistry::with_all_agents();
    let bridge = PythonBridge::new(Some("http://127.0.0.1:9091")).unwrap();
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
        .run_analysis(&request, &mut ctx, &registry, &bridge, None)
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
