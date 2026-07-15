//! Narrative Mind v4.0 — Tauri 桌面应用入口
//!
//! Phase A-D 完成: 创作工坊四能力就绪（上下文导入/多维分析/反思闭环/续写生成）。
//! Phase E: 实体管理面板。
//! Phase F: 成本追踪 + 分析观察者接线。
//! Phase G/H: 分析结果可视化 + 建议管理。
//! Phase L: 三面板 UI 重构。

// 防止未连接 Tauri 时显示控制台窗口
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use xmgl_tauri::{commands, AppState};

fn main() {
    let app_state = AppState::new("xmgl.db").expect("应用初始化失败");

    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::list_projects,
            commands::create_project,
            commands::get_project,
            commands::delete_project,
            commands::list_chapters,
            commands::create_chapter,
            commands::get_chapter,
            commands::update_chapter,
            commands::delete_chapter,
            commands::health_check,
            commands::run_analysis,
            // Phase L1: 实体 CRUD
            commands::list_characters,
            commands::get_character,
            commands::create_character,
            commands::update_character,
            commands::delete_character,
            commands::list_locations,
            commands::get_location,
            commands::create_location,
            commands::update_location,
            commands::delete_location,
            commands::list_foreshadows,
            commands::get_foreshadow,
            commands::create_foreshadow,
            commands::update_foreshadow,
            commands::delete_foreshadow,
            commands::list_timeline,
            // Phase L2: 项目设置
            commands::list_project_settings,
            commands::set_project_setting,
            commands::delete_project_setting,
            // Phase A: ProjectContext
            commands::get_project_context,
            commands::save_project_context,
            commands::run_full_analysis,
            // Phase B: 上下文入口
            commands::expand_context_section,
            commands::run_import_analysis,
            // Phase C: 建议管理
            commands::set_suggestion_state,
            commands::get_dismissed_suggestions,
            commands::clear_dismissed_suggestions,
            // Phase D: 续写生成
            commands::run_continuation,
            // Phase D: 黄金三章
            commands::start_golden_three,
            commands::continue_golden_three,
            commands::finalize_golden_three,
            commands::resume_golden_three,
        ])
        .run(tauri::generate_context!())
        .expect("无法启动 Tauri 应用");
}
