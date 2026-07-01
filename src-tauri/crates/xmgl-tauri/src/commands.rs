//! Tauri IPC Commands.
//!
//! 所有 #[tauri::command] 集中在此模块，避免 proc-macro 命名冲突。

use crate::AppState;
use tauri::State;
use xmgl_core::{ChapterData, ProjectMeta};

// ── 项目 ──

#[tauri::command]
pub fn list_projects(state: State<'_, AppState>) -> Result<Vec<ProjectMeta>, String> {
    state.project_manager.list_projects().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_project(state: State<'_, AppState>, name: String) -> Result<ProjectMeta, String> {
    state.project_manager.create_project(&name).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_project(state: State<'_, AppState>, id: String) -> Result<Option<ProjectMeta>, String> {
    state.project_manager.get_project(&id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_project(state: State<'_, AppState>, id: String) -> Result<(), String> {
    state.project_manager.delete_project(&id).map_err(|e| e.to_string())
}

// ── 章节 ──

#[tauri::command]
pub fn list_chapters(
    state: State<'_, AppState>,
    project_id: String,
) -> Result<Vec<ChapterData>, String> {
    state
        .project_manager
        .list_chapters(&project_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_chapter(
    state: State<'_, AppState>,
    project_id: String,
    title: String,
    text: String,
) -> Result<ChapterData, String> {
    state
        .project_manager
        .create_chapter(&project_id, &title, &text)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_chapter(state: State<'_, AppState>, id: String) -> Result<Option<ChapterData>, String> {
    state.project_manager.get_chapter(&id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_chapter(
    state: State<'_, AppState>,
    chapter: ChapterData,
) -> Result<(), String> {
    state
        .project_manager
        .update_chapter(&chapter)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_chapter(state: State<'_, AppState>, id: String) -> Result<(), String> {
    state.project_manager.delete_chapter(&id).map_err(|e| e.to_string())
}

// ── Python Bridge ──

#[tauri::command]
pub async fn health_check(state: State<'_, AppState>) -> Result<(bool, bool, String), String> {
    let mut bridge = state.python_bridge.lock().await;
    bridge.health_check().await.map_err(|e| e.to_string())
}
