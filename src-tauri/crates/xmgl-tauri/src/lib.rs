//! xmgl-tauri — Tauri Commands + Events 胶水层
//!
//! Phase B: AppState、项目/章节 Tauri commands、事件常量。
//! Phase D: 接入 Orchestrator、agent:progress / proposal:ready / analysis:complete 事件。
//! Phase F: TauriAnalysisObserver 接线 + 成本日志记录。

pub mod commands;

use tauri::Emitter;
use std::sync::Arc;
use xmgl_agent::AgentRegistry;
use xmgl_core::{LlmClient, TextRange};
use xmgl_llm::LlmClientImpl;
use xmgl_orchestrator::{AnalysisObserver, Orchestrator};
use xmgl_project::ProjectManager;

// =========================================================================
// AppState
// =========================================================================

/// Tauri 应用全局状态。
///
/// LlmClient 通过 `Arc<dyn LlmClient>` 共享，支持并发分析。
/// ProjectManager 本身是 Sync + Clone（仅存 db_path），无需锁。
pub struct AppState {
    pub project_manager: ProjectManager,
    pub llm_client: Arc<dyn LlmClient>,
    pub agent_registry: AgentRegistry,
    pub orchestrator: Orchestrator,
}

impl AppState {
    /// 创建 AppState。
    ///
    /// `db_path` 为 SQLite 数据库路径。
    /// LLM 配置从环境变量读取（LLM_API_KEY, LLM_BASE_URL, LLM_MODEL 等）。
    pub fn new(db_path: &str) -> Result<Self, String> {
        let project_manager = ProjectManager::new(db_path).map_err(|e| e.to_string())?;
        let llm_client = Arc::new(LlmClientImpl::new().map_err(|e| e.to_string())?)
            as Arc<dyn LlmClient>;

        Ok(Self {
            project_manager,
            llm_client,
            agent_registry: AgentRegistry::with_all_agents(),
            orchestrator: Orchestrator::new(),
        })
    }

    /// 记录一次 LLM 调用成本到 SQLite。
    #[allow(clippy::too_many_arguments)]
    pub fn log_cost_entry(
        &self,
        agent_id: &str,
        task_type: &str,
        model: &str,
        input_tokens: u32,
        output_tokens: u32,
        cost_usd: f64,
        latency_ms: u32,
    ) -> Result<(), String> {
        let db_path = self.project_manager.db_path();
        let conn =
            xmgl_memory::open_connection(db_path).map_err(|e| e.to_string())?;
        let entry = xmgl_memory::CostEntry {
            timestamp: chrono::Utc::now()
                .format("%Y-%m-%dT%H:%M:%SZ")
                .to_string(),
            agent_id: agent_id.to_string(),
            task_type: task_type.to_string(),
            model: model.to_string(),
            input_tokens,
            output_tokens,
            cost_usd,
            latency_ms,
        };
        xmgl_memory::log_cost(&conn, &entry).map_err(|e| e.to_string())
    }
}

// =========================================================================
// Tauri Events 常量
// =========================================================================

/// Tauri 事件名称常量。
pub mod events {
    /// Agent 开始/完成分析阶段。
    /// Payload: `{ agent_id: String, phase: "start" | "done", progress: f64 }`
    pub const AGENT_PROGRESS: &str = "agent:progress";

    /// 新修改建议就绪 → 前端渲染黄点（gutter marker）。
    /// Payload: `{ proposal_id: String, chapter_id: String, range: TextRange, summary: String }`
    pub const PROPOSAL_READY: &str = "proposal:ready";

    /// 分析完成，成本+耗时汇总。
    /// Payload: `{ request_id: String, total_cost_usd: f64, total_latency_ms: u32, agent_count: u32 }`
    pub const ANALYSIS_COMPLETE: &str = "analysis:complete";
}

// =========================================================================
// TauriAnalysisObserver — AnalysisObserver trait 实现
// =========================================================================

/// TG 2: 实现 `AnalysisObserver` trait，通过 Tauri `emit()` 向前端推送事件。
pub struct TauriAnalysisObserver {
    pub app_handle: tauri::AppHandle,
}

impl AnalysisObserver for TauriAnalysisObserver {
    fn on_agent_start(&self, agent_id: &str, agent_name: &str, progress_pct: f64) {
        let _ = self.app_handle.emit(
            events::AGENT_PROGRESS,
            serde_json::json!({
                "agent_id": agent_id,
                "agent_name": agent_name,
                "stage": "start",
                "progress_pct": progress_pct,
            }),
        );
    }

    fn on_agent_done(&self, agent_id: &str, agent_name: &str, progress_pct: f64) {
        let _ = self.app_handle.emit(
            events::AGENT_PROGRESS,
            serde_json::json!({
                "agent_id": agent_id,
                "agent_name": agent_name,
                "stage": "done",
                "progress_pct": progress_pct,
            }),
        );
    }

    fn on_proposal_ready(
        &self,
        proposal_id: &str,
        agent_id: &str,
        title: &str,
        severity: &str,
        location: Option<TextRange>,
        suggestion: &str,
    ) {
        let payload = serde_json::json!({
            "proposal_id": proposal_id,
            "agent_id": agent_id,
            "title": title,
            "severity": severity,
            "suggestion": suggestion,
            "location": location.map(|loc| serde_json::json!({
                "start_line": loc.start_line,
                "start_column": loc.start_column,
                "end_line": loc.end_line,
                "end_column": loc.end_column,
            })),
        });
        let _ = self.app_handle.emit(events::PROPOSAL_READY, payload);
    }

    fn on_analysis_complete(
        &self,
        request_id: &str,
        total_cost_usd: f64,
        total_latency_ms: u64,
        agent_count: u32,
        findings_count: u32,
    ) {
        let _ = self.app_handle.emit(
            events::ANALYSIS_COMPLETE,
            serde_json::json!({
                "request_id": request_id,
                "total_cost": total_cost_usd,
                "total_latency": total_latency_ms,
                "agent_count": agent_count,
                "findings_count": findings_count,
            }),
        );
    }
}

// =========================================================================
// main.rs 集成参考（Phase B）
// =========================================================================

// Phase B 的 `main.rs` 应类似：
//
// ```ignore
// use xmgl_tauri::{AppState, commands};
//
// fn main() {
//     let app_state = AppState::new("xmgl.db", None)
//         .expect("应用初始化失败");
//
//     tauri::Builder::default()
//         .manage(app_state)
//         .invoke_handler(tauri::generate_handler![
//             commands::list_projects,
//             commands::create_project,
//             commands::get_project,
//             commands::delete_project,
//             commands::list_chapters,
//             commands::create_chapter,
//             commands::get_chapter,
//             commands::update_chapter,
//             commands::delete_chapter,
//             commands::health_check,
//         ])
//         .run(tauri::generate_context!())
//         .expect("无法启动 Tauri 应用");
// }
// ```
//
// Phase D 接入 Orchestrator 后追加 agent:progress / proposal:ready
// / analysis:complete 事件的 emit 逻辑。

// =========================================================================
// Tests
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_state_new() {
        let db_path = format!("test_tauri_{}.db", uuid::Uuid::new_v4());
        let state = AppState::new(&db_path).expect("create AppState");
        assert!(state.project_manager.db_path().ends_with(".db"));
        assert!(state.agent_registry.len() > 0);
        let _ = std::fs::remove_file(&db_path);
    }

    #[test]
    fn test_app_state_new_default() {
        let db_path = format!("test_tauri2_{}.db", uuid::Uuid::new_v4());
        let state = AppState::new(&db_path).expect("create AppState");
        let _ = std::fs::remove_file(&db_path);
    }

    #[test]
    fn test_event_constants() {
        assert_eq!(events::AGENT_PROGRESS, "agent:progress");
        assert_eq!(events::PROPOSAL_READY, "proposal:ready");
        assert_eq!(events::ANALYSIS_COMPLETE, "analysis:complete");
    }
}
