//! xmgl-tauri — Tauri Commands + Events 胶水层
//!
//! Phase B: AppState、项目/章节 Tauri commands、事件常量。
//! Phase D: 接入 Orchestrator、agent:progress / proposal:ready / analysis:complete 事件。

pub mod commands;

use tokio::sync::Mutex;
use xmgl_agent::AgentRegistry;
use xmgl_orchestrator::Orchestrator;
use xmgl_project::ProjectManager;
use xmgl_python_bridge::PythonBridge;

// =========================================================================
// AppState
// =========================================================================

/// Tauri 应用全局状态。
///
/// PythonBridge 包裹在 tokio::sync::Mutex 中（非 std::sync::Mutex），
/// 因为 health_check 等 async command 需要持锁跨越 .await 点，
/// std::sync::MutexGuard 不是 Send，会导致编译错误。
///
/// ProjectManager 本身是 Sync + Clone（仅存 db_path），无需锁。
pub struct AppState {
    pub project_manager: ProjectManager,
    pub python_bridge: Mutex<PythonBridge>,
    pub agent_registry: AgentRegistry,
    pub orchestrator: Orchestrator,
}

impl AppState {
    /// 创建 AppState。
    ///
    /// `db_path` 为 SQLite 数据库路径，
    /// `sidecar_url` 为 Python sidecar 地址（`None` 默认 `http://localhost:9091`）。
    pub fn new(db_path: &str, sidecar_url: Option<&str>) -> Result<Self, String> {
        let project_manager = ProjectManager::new(db_path).map_err(|e| e.to_string())?;
        let python_bridge = PythonBridge::new(sidecar_url).map_err(|e| e.to_string())?;

        Ok(Self {
            project_manager,
            python_bridge: Mutex::new(python_bridge),
            agent_registry: AgentRegistry::with_all_agents(),
            orchestrator: Orchestrator::new(),
        })
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
        let state = AppState::new(&db_path, None).expect("create AppState");
        assert!(state.project_manager.db_path().ends_with(".db"));
        let _ = std::fs::remove_file(&db_path);
    }

    #[test]
    fn test_app_state_new_with_sidecar_url() {
        let db_path = format!("test_tauri2_{}.db", uuid::Uuid::new_v4());
        let state =
            AppState::new(&db_path, Some("http://127.0.0.1:9091")).expect("create AppState");
        let bridge = state.python_bridge.blocking_lock();
        assert_eq!(bridge.consecutive_failures(), 0);
        drop(bridge);
        let _ = std::fs::remove_file(&db_path);
    }

    #[test]
    fn test_event_constants() {
        assert_eq!(events::AGENT_PROGRESS, "agent:progress");
        assert_eq!(events::PROPOSAL_READY, "proposal:ready");
        assert_eq!(events::ANALYSIS_COMPLETE, "analysis:complete");
    }
}
