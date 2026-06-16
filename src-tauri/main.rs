//! Narrative Mind v4.0 — Tauri 桌面应用入口
//!
//! Phase A: 最小 Tauri 入口，打开 WebView 显示前端。
//! Phase B: 加入 Tauri commands 注册和 Python sidecar 管理。

// Prevent additional console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("Narrative Mind 启动失败 — 请检查前端是否已构建 (npm run build)");
}
