//! xmgl-tauri — Tauri Commands + Events 胶水层
//!
//! 本 crate 实现 Tauri 桌面框架集成：
//! - `#[tauri::command]` IPC 命令处理
//! - Tauri 事件系统（前后端推送）
//! - 连接 Orchestrator、Project、Memory 的胶水代码
//! - 文件系统操作（项目目录管理）
//!
//! # Phase B 实现计划
//!
//! ## 全局状态
//! ```ignore
//! pub struct AppState {
//!     pub project_manager: ProjectManager,
//!     pub python_bridge: PythonBridge,
//!     // Phase D 再加：
//!     // pub orchestrator: Orchestrator,
//! }
//! ```
//!
//! ## Tauri Commands（前端 invoke 调用）
//!
//! ### 项目
//! ```ignore
//! #[tauri::command]
//! pub async fn list_projects(state: State<'_, AppState>) -> Result<Vec<ProjectMeta>, String>;
//! #[tauri::command]
//! pub async fn create_project(state: State<'_, AppState>, name: String) -> Result<ProjectMeta, String>;
//! #[tauri::command]
//! pub async fn get_project(state: State<'_, AppState>, id: String) -> Result<Option<ProjectMeta>, String>;
//! #[tauri::command]
//! pub async fn delete_project(state: State<'_, AppState>, id: String) -> Result<(), String>;
//! ```
//!
//! ### 章节
//! ```ignore
//! #[tauri::command]
//! pub async fn list_chapters(state: State<'_, AppState>, project_id: String) -> Result<Vec<ChapterData>, String>;
//! #[tauri::command]
//! pub async fn create_chapter(state: State<'_, AppState>, project_id: String, title: String, text: String) -> Result<ChapterData, String>;
//! #[tauri::command]
//! pub async fn get_chapter(state: State<'_, AppState>, id: String) -> Result<Option<ChapterData>, String>;
//! #[tauri::command]
//! pub async fn update_chapter(state: State<'_, AppState>, chapter: ChapterData) -> Result<(), String>;
//! #[tauri::command]
//! pub async fn delete_chapter(state: State<'_, AppState>, id: String) -> Result<(), String>;
//! ```
//!
//! ## Tauri Events（Rust → 前端推送）
//! ```ignore
//! // agent:progress  — Agent 开始/完成分析阶段
//! // proposal:ready  — 新修改建议就绪 → 前端渲染黄点
//! // analysis:complete — 分析完成，成本+耗时汇总
//! ```
//!
//! ## main.rs 集成（Phase B 版本）
//! ```ignore
//! use xmgl_tauri::{commands, AppState};
//! use xmgl_project::ProjectManager;
//! use xmgl_python_bridge::PythonBridge;
//!
//! fn main() {
//!     let project_manager = ProjectManager::new("xmgl.db").expect("数据库初始化失败");
//!     let python_bridge = PythonBridge::new(None).expect("Python Bridge 创建失败");
//!
//!     tauri::Builder::default()
//!         .manage(AppState { project_manager, python_bridge })
//!         .invoke_handler(tauri::generate_handler![
//!             commands::list_projects,
//!             commands::create_project,
//!             commands::get_project,
//!             commands::delete_project,
//!             commands::list_chapters,
//!             commands::create_chapter,
//!             commands::get_chapter,
//!             commands::update_chapter,
//!             commands::delete_chapter,
//!         ])
//!         .run(tauri::generate_context!())
//!         .expect("无法启动 Tauri 应用");
//! }
//! ```
//!
//! 注意：需要在 Cargo.toml 加 `tauri = { workspace = true }`，
//! 同时在 workspace 层声明 tauri 依赖。
//!
//! 详细接口规格见 `docs/PHASE-B-INTERFACES.md`

#[cfg(test)]
mod tests {
    #[test]
    fn it_compiles() {
        assert!(true);
    }
}
