//! xmgl-memory — 三层记忆系统（工作/情节/永久）+ SQLite 持久化
//!
//! 本 crate 实现记忆层：
//! - WorkingMemory：当前会话上下文（MMR 窗口）
//! - EpisodicMemory：情节记忆（角色弧光、伏笔状态、因果链）
//! - PermanentMemory：永久记忆（世界观规则、角色档案、语料索引）
//! - SQLite 存储（memory.db）+ 成本追踪表（cost_log）
//!
//! Phase B 开始填充实现（SQLite schema 设计）。
