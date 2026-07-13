//! Narrative Mind v4.0 — Tauri 桌面应用入口
//!
//! Phase B: 接线 xmgl-tauri 的 AppState + commands。
//! Phase D: 接入 Orchestrator + Agent 事件循环。

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
        ])
        .run(tauri::generate_context!())
        .expect("无法启动 Tauri 应用");
}
