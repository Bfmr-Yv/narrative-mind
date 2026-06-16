//! xmgl-agent — Agent trait、注册表、生命周期管理
//!
//! 本 crate 实现 Agent 抽象层：
//! - `Agent` trait：所有 Agent 的统一接口
//! - `AgentRegistry`：Agent 注册与发现
//! - `SharedContext`：Agent 间共享上下文
//! - 9 个 Agent 实现（Character, World, Narrative, Prose,
//!   Theme, Economy, ReaderExpectation, Conception, EditorInChief）
//!
//! Phase C 开始填充实现。
