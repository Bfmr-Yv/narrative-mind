//! xmgl-project — 项目/章节 CRUD + 旧数据迁移
//!
//! 本 crate 实现项目管理：
//! - 项目创建、打开、保存、导出
//! - 章节增删改查 + 全文检索
//! - 旧版（v3.1 Flask）数据迁移
//! - 项目元数据（字数统计、创建时间、修改时间）
//!
//! # Phase B 实现计划
//!
//! ## 核心结构
//! ```ignore
//! pub struct ProjectManager {
//!     db_path: String,
//! }
//!
//! pub struct MigrationReport {
//!     pub projects_migrated: u32,
//!     pub chapters_migrated: u32,
//!     pub errors: Vec<String>,
//! }
//! ```
//!
//! ## ProjectManager 方法
//! ```ignore
//! impl ProjectManager {
//!     /// 新建或打开已有数据库。首次调用自动 run migrations。
//!     pub fn new(db_path: &str) -> Result<Self>;
//!
//!     // ── 项目管理 ──
//!     pub fn create_project(&self, name: &str) -> Result<ProjectMeta>;
//!     pub fn list_projects(&self) -> Result<Vec<ProjectMeta>>;
//!     pub fn get_project(&self, id: &str) -> Result<Option<ProjectMeta>>;
//!     pub fn update_project(&self, meta: &ProjectMeta) -> Result<()>;
//!     pub fn delete_project(&self, id: &str) -> Result<()>;
//!
//!     // ── 章节管理 ──
//!     pub fn create_chapter(&self, project_id: &str, title: &str, text: &str) -> Result<ChapterData>;
//!     pub fn get_chapter(&self, id: &str) -> Result<Option<ChapterData>>;
//!     pub fn list_chapters(&self, project_id: &str) -> Result<Vec<ChapterData>>;
//!     pub fn update_chapter(&self, chapter: &ChapterData) -> Result<()>;
//!     pub fn delete_chapter(&self, id: &str) -> Result<()>;
//!
//!     // ── 统计 ──
//!     pub fn recalc_project_stats(&self, project_id: &str) -> Result<()>;
//!
//!     // ── 旧数据迁移 ──
//!     /// 从 v3.1 JSON 文件迁移。首次运行自动检测，完成后写 .xmgl_migrated_v4 标记。
//!     pub fn migrate_from_v3(&self, v3_project_path: &str) -> Result<MigrationReport>;
//! }
//! ```
//!
//! 依赖 `xmgl-memory` 做底层 SQLite 操作。
//! 详细接口规格见 `docs/PHASE-B-INTERFACES.md`

#[cfg(test)]
mod tests {
    #[test]
    fn it_compiles() {
        assert!(true);
    }
}
