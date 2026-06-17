//! xmgl-memory — 三层记忆系统（工作/情节/永久）+ SQLite 持久化
//!
//! 本 crate 实现记忆层：
//! - WorkingMemory：当前会话上下文（MMR 窗口）— Phase C
//! - EpisodicMemory：情节记忆（角色弧光、伏笔状态、因果链）— Phase C
//! - PermanentMemory：永久记忆（世界观规则、角色档案、语料索引）— Phase C
//! - SQLite 存储（xmgl.db）+ 成本追踪表（cost_log）— Phase B
//!
//! # Phase B 实现计划
//!
//! ## 数据库初始化
//! ```ignore
//! pub fn init_db(path: &str) -> Result<Connection>;
//! pub fn run_migrations(conn: &Connection) -> Result<()>;
//! ```
//!
//! ## 项目 CRUD（被 xmgl-project 调用）
//! ```ignore
//! pub fn insert_project(conn: &Connection, meta: &ProjectMeta) -> Result<()>;
//! pub fn list_projects(conn: &Connection) -> Result<Vec<ProjectMeta>>;
//! pub fn get_project(conn: &Connection, id: &str) -> Result<Option<ProjectMeta>>;
//! pub fn update_project(conn: &Connection, meta: &ProjectMeta) -> Result<()>;
//! pub fn delete_project(conn: &Connection, id: &str) -> Result<()>;
//! ```
//!
//! ## 章节 CRUD（被 xmgl-project 调用）
//! ```ignore
//! pub fn insert_chapter(conn: &Connection, chapter: &ChapterData) -> Result<()>;
//! pub fn get_chapter(conn: &Connection, id: &str) -> Result<Option<ChapterData>>;
//! pub fn list_chapters(conn: &Connection, project_id: &str) -> Result<Vec<ChapterData>>;
//! pub fn update_chapter(conn: &Connection, chapter: &ChapterData) -> Result<()>;
//! pub fn delete_chapter(conn: &Connection, id: &str) -> Result<()>;
//! ```
//!
//! ## 成本追踪
//! ```ignore
//! pub fn log_cost(conn: &Connection, entry: &CostEntry) -> Result<()>;
//! pub fn get_monthly_cost(conn: &Connection, year: i32, month: i32) -> Result<f64>;
//! pub fn check_budget_fuse(conn: &Connection) -> Result<BudgetFuseLevel>;
//! ```
//!
//! ## Phase B 建表（7 张）
//! - projects, project_settings, chapters
//! - cost_log, monthly_budget
//! - pad_history, analysis_history（先建表，Phase C/D 填充）
//!
//! Phase C 追加：episodic_memory, causality_graph, foreshadowing_registry, permanent_memory
//!
//! 详细接口规格见 `docs/PHASE-B-INTERFACES.md`

#[cfg(test)]
mod tests {
    #[test]
    fn it_compiles() {
        assert!(true);
    }
}
