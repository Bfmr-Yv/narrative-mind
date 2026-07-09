//! Tauri IPC Commands.
//!
//! 所有 #[tauri::command] 集中在此模块，避免 proc-macro 命名冲突。

use crate::{AppState, TauriAnalysisObserver};
use std::sync::Arc;
use tauri::State;
use xmgl_core::{
    AgentFinding, ChapterData, Character, ForeshadowEntry, Location,
    ProjectMeta, TaskType, TimelineEvent,
};
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
) -> Result<ChapterData, String> {
    state
        .project_manager
        .update_chapter(&chapter)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_chapter(state: State<'_, AppState>, id: String) -> Result<(), String> {
    state.project_manager.delete_chapter(&id).map_err(|e| e.to_string())
}

// ── Health ──

#[tauri::command]
pub async fn health_check(state: State<'_, AppState>) -> Result<(bool, bool, String), String> {
    let configured = state.llm_client.is_configured();
    Ok((true, configured, "llm_client".into()))
}

// ── 分析 ──

/// 分析结果（前端友好格式）
#[derive(serde::Serialize)]
pub struct AnalysisOutput {
    pub request_id: String,
    pub agent_outputs: Vec<AgentOutput>,
    pub topology: String,
    pub complexity: String,
    /// 结构化的 Agent 发现
    pub findings: Vec<AgentFinding>,
    /// 累计成本 (USD)
    pub total_cost_usd: f64,
    /// 累计延迟 (ms)
    pub total_latency_ms: u64,
    /// Phase L1: 提取的角色
    pub extracted_characters: Vec<Character>,
    /// Phase L1: 提取的地点
    pub extracted_locations: Vec<Location>,
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
/// 通过 `TauriAnalysisObserver` 向前端推送实时进度和成本汇总。
#[tauri::command]
pub async fn run_analysis(
    state: State<'_, AppState>,
    app_handle: tauri::AppHandle,
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

    // 4. 保存 request_id 以便复用
    let request_id = request.request_id.clone();

    // 5. 构造 observer
    let observer = TauriAnalysisObserver {
        app_handle: app_handle.clone(),
    };

    // 6. 执行分析（记录 wall-clock 耗时，含编排开销）
    let start = std::time::Instant::now();
    let result = state
        .orchestrator
        .run_analysis(
            &request,
            &mut ctx,
            &state.agent_registry,
            Arc::clone(&state.llm_client),
            Some(&observer),
        )
        .await
        .map_err(|e| e.to_string())?;
    let wall_clock_ms = start.elapsed().as_millis() as u64;

    // 7. 写成本日志
    for (agent_id, usage) in &result.usages {
        let _ = state.log_cost_entry(
            &format!("{agent_id:?}"),
            task_type.as_str(),
            &usage.model,
            usage.input_tokens,
            usage.output_tokens,
            usage.cost_usd,
            usage.latency_ms,
        );
    }

    // 8. 转换为前端友好格式
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
        request_id,
        agent_outputs,
        topology,
        complexity,
        findings: result.findings,
        total_cost_usd: result.total_cost_usd,
        total_latency_ms: wall_clock_ms,
        extracted_characters: result.extracted_characters,
        extracted_locations: result.extracted_locations,
    })
}

// ── 辅助：从 AppState 获取数据库连接 ──

fn open_db(state: &State<'_, AppState>) -> Result<rusqlite::Connection, String> {
    let db_path = state.project_manager.db_path();
    xmgl_memory::open_connection(db_path).map_err(|e| e.to_string())
}

// ── 角色 ──

#[tauri::command]
pub fn list_characters(
    state: State<'_, AppState>,
    project_id: String,
) -> Result<Vec<Character>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::list_characters_by_project(&conn, &project_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_character(
    state: State<'_, AppState>,
    id: String,
) -> Result<Option<Character>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::get_character(&conn, &id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_character(
    state: State<'_, AppState>,
    character: Character,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::insert_character(&conn, &character).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_character(
    state: State<'_, AppState>,
    character: Character,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::update_character(&conn, &character).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_character(
    state: State<'_, AppState>,
    id: String,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::delete_character(&conn, &id).map_err(|e| e.to_string())
}

// ── 地点 ──

#[tauri::command]
pub fn list_locations(
    state: State<'_, AppState>,
    project_id: String,
) -> Result<Vec<Location>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::list_locations_by_project(&conn, &project_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_location(
    state: State<'_, AppState>,
    id: String,
) -> Result<Option<Location>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::get_location(&conn, &id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_location(
    state: State<'_, AppState>,
    location: Location,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::insert_location(&conn, &location).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_location(
    state: State<'_, AppState>,
    location: Location,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::update_location(&conn, &location).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_location(
    state: State<'_, AppState>,
    id: String,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::delete_location(&conn, &id).map_err(|e| e.to_string())
}

// ── 伏笔 ──

#[tauri::command]
pub fn list_foreshadows(
    state: State<'_, AppState>,
    project_id: String,
) -> Result<Vec<ForeshadowEntry>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::list_foreshadows_by_project(&conn, &project_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_foreshadow(
    state: State<'_, AppState>,
    id: String,
) -> Result<Option<ForeshadowEntry>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::get_foreshadow(&conn, &id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_foreshadow(
    state: State<'_, AppState>,
    entry: ForeshadowEntry,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::insert_foreshadow(&conn, &entry).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_foreshadow(
    state: State<'_, AppState>,
    entry: ForeshadowEntry,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::update_foreshadow(&conn, &entry).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_foreshadow(
    state: State<'_, AppState>,
    id: String,
) -> Result<(), String> {
    let conn = open_db(&state)?;
    xmgl_memory::delete_foreshadow(&conn, &id).map_err(|e| e.to_string())
}

// ── 时间线（只读） ──

#[tauri::command]
pub fn list_timeline(
    state: State<'_, AppState>,
    project_id: String,
) -> Result<Vec<TimelineEvent>, String> {
    let conn = open_db(&state)?;
    xmgl_memory::list_timeline_by_project(&conn, &project_id).map_err(|e| e.to_string())
}
