//! Tauri IPC Commands.
//!
//! 所有 #[tauri::command] 集中在此模块，避免 proc-macro 命名冲突。

use crate::AppState;
use tauri::State;
use xmgl_core::{ChapterData, ProjectMeta, TaskType};
use xmgl_agent::SharedContext;
use xmgl_orchestrator::{AnalysisRequest, AnalysisTrigger};

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

// ── 分析 ──

/// 分析结果（前端友好格式）
#[derive(serde::Serialize)]
pub struct AnalysisOutput {
    pub request_id: String,
    pub agent_outputs: Vec<AgentOutput>,
    pub topology: String,
    pub complexity: String,
}

#[derive(serde::Serialize)]
pub struct AgentOutput {
    pub agent_id: String,
    pub agent_name: String,
    pub output: String,
}

/// 触发一次 Agent 分析。
///
/// `task_type` 为分析类型（如 "pad_compute"、"entity_extract"）。
/// 系统根据复杂度自动选择拓扑，调用相应 Agent，返回分析结果。
#[tauri::command]
pub async fn run_analysis(
    state: State<'_, AppState>,
    chapter_id: String,
    task_type: String,
) -> Result<AnalysisOutput, String> {
    // 1. 加载章节文本
    let chapter = state
        .project_manager
        .get_chapter(&chapter_id)
        .map_err(|e| e.to_string())?
        .ok_or_else(|| format!("chapter not found: {chapter_id}"))?;

    // 2. 构建上下文
    let mut ctx = SharedContext::new(&chapter.project_id, &chapter.text)
        .with_chapter(&chapter_id);

    // 3. 构建请求
    let tt: TaskType = task_type.parse().map_err(|e: String| e)?;
    let request = AnalysisRequest {
        request_id: uuid::Uuid::new_v4().to_string(),
        task_type: tt,
        trigger: AnalysisTrigger::Manual,
        chapter_ids: vec![chapter_id],
        context_note: None,
    };

    // 4. 执行分析
    let mut bridge = state.python_bridge.lock().await;
    let result = state
        .orchestrator
        .run_analysis(&request, &mut ctx, &state.agent_registry, &mut bridge)
        .await
        .map_err(|e| e.to_string())?;

    // 5. 转换为前端友好格式
    let topology = format!("{:?}", result.topology);
    let complexity = format!("{:?}", result.complexity);
    let agent_outputs = result
        .agent_outputs
        .into_iter()
        .map(|(id, output)| AgentOutput {
            agent_id: format!("{id:?}"),
            agent_name: id.name().to_string(),
            output,
        })
        .collect();

    Ok(AnalysisOutput {
        request_id: uuid::Uuid::new_v4().to_string(),
        agent_outputs,
        topology,
        complexity,
    })
}
