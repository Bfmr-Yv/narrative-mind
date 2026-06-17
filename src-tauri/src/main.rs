//! Narrative Mind v4.0 — Tauri 桌面应用入口

// 先屏蔽未使用的 import，窗口能开后 Phase B 再连
// use xmgl_tauri;

// Prevent additional console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("无法启动 Tauri 应用");
}
