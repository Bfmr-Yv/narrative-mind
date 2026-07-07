//! xmgl-tauri 集成测试
//!
//! 验证 AppState 创建 + Command 链路（Phase K: 不再需要 sidecar）。

use xmgl_tauri::AppState;

/// AppState::new — 基础构造验证
#[test]
fn test_app_state_new_default() {
    // 用内存数据库避免磁盘污染
    let state = AppState::new(":memory:");
    assert!(state.is_ok(), "AppState::new 应成功创建");
}

/// AppState::new — 无 LLM 配置也应成功（LLM client 仅在 call_agent 时检查）
#[test]
fn test_app_state_new_default2() {
    let state = AppState::new(":memory:");
    assert!(state.is_ok());
}

/// AppState::new — 验证 agent_registry 已初始化
#[test]
fn test_app_state_new_has_registry() {
    let state = AppState::new(":memory:").unwrap();
    assert!(state.agent_registry.len() > 0);
}
