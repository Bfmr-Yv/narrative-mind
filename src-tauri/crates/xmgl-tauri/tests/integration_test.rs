//! xmgl-tauri 集成测试
//!
//! 验证 AppState 创建 + Command 链路（无需真实 sidecar）。

use xmgl_tauri::AppState;

/// AppState::new — 基础构造验证
#[test]
fn test_app_state_new_default() {
    // 用内存数据库避免磁盘污染
    let state = AppState::new(":memory:", Some("http://127.0.0.1:1"));
    assert!(state.is_ok(), "AppState::new 应成功创建");
}

/// AppState::new — 自定义 sidecar URL
#[test]
fn test_app_state_new_with_custom_url() {
    let state = AppState::new(":memory:", Some("http://localhost:9091"));
    assert!(state.is_ok(), "AppState::new 应支持自定义 URL");
}

/// AppState::new — 默认 sidecar URL (None)
#[test]
fn test_app_state_new_none_url() {
    let state = AppState::new(":memory:", None);
    assert!(state.is_ok(), "AppState::new 应在 None URL 时使用默认值");
}
