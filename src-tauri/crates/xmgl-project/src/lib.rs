//! xmgl-project — 项目/章节 CRUD + 旧数据迁移
//!
//! Phase B: ProjectManager 封装 xmgl-memory 操作，提供业务层 API。

use chrono::Utc;
use rusqlite::Connection;
use uuid::Uuid;
use xmgl_core::{ChapterData, CoreError, CoreResult, ProjectContext, ProjectMeta};

// =========================================================================
// MigrationReport
// =========================================================================

/// v3.1 → v4.0 迁移报告。
#[derive(Debug, Clone)]
pub struct MigrationReport {
    pub projects_migrated: u32,
    pub chapters_migrated: u32,
    pub errors: Vec<String>,
}

impl MigrationReport {
    pub fn has_errors(&self) -> bool {
        !self.errors.is_empty()
    }
}

// =========================================================================
// ProjectManager
// =========================================================================

/// 项目管理器 — 项目与章节的业务层 API。
///
/// 依赖 `xmgl-memory` 做底层 SQLite 操作。
/// 线程安全（仅存储 db_path，每次操作开新连接）。
#[derive(Debug, Clone)]
pub struct ProjectManager {
    db_path: String,
}

impl ProjectManager {
    /// 新建或打开已有数据库。首次调用自动执行 migrations。
    ///
    /// 成功返回 `ProjectManager`，数据库文件位于 `db_path`。
    pub fn new(db_path: &str) -> CoreResult<Self> {
        // 初始化数据库并运行 migrations。
        // init_db 打开连接并执行 DDL，之后连接可以被安全关闭
        // （文件数据库数据已持久化到磁盘，:memory: 数据库会在关闭时丢失数据）。
        let conn = xmgl_memory::init_db(db_path)?;
        conn.close()
            .map_err(|(_, e)| CoreError::Internal(format!("close db: {e}")))?;

        Ok(Self {
            db_path: db_path.to_string(),
        })
    }

    /// 获取内部的数据库路径。
    pub fn db_path(&self) -> &str {
        &self.db_path
    }

    // ── 项目管理 ──

    /// 创建新项目。
    ///
    /// 自动生成 `id`（UUID v4）、`created_at`、`updated_at`。
    pub fn create_project(&self, name: &str) -> CoreResult<ProjectMeta> {
        let conn = self.open()?;
        let now = Self::now_iso();

        let meta = ProjectMeta {
            id: Uuid::new_v4().to_string(),
            name: name.to_string(),
            created_at: now.clone(),
            updated_at: now,
            chapter_count: 0,
            total_words: 0,
        };

        xmgl_memory::insert_project(&conn, &meta)?;
        Ok(meta)
    }

    /// 列出所有项目（按更新时间降序）。
    pub fn list_projects(&self) -> CoreResult<Vec<ProjectMeta>> {
        let conn = self.open()?;
        xmgl_memory::list_projects(&conn)
    }

    /// 获取单个项目。
    pub fn get_project(&self, id: &str) -> CoreResult<Option<ProjectMeta>> {
        let conn = self.open()?;
        xmgl_memory::get_project(&conn, id)
    }

    /// 更新项目（名称、更新时间、章节数、总字数）。
    pub fn update_project(&self, meta: &ProjectMeta) -> CoreResult<()> {
        let conn = self.open()?;
        xmgl_memory::update_project(&conn, meta)
    }

    /// 删除项目（级联删除其下所有章节）。
    pub fn delete_project(&self, id: &str) -> CoreResult<()> {
        let conn = self.open()?;
        xmgl_memory::delete_project(&conn, id)
    }

    // ── 章节管理 ──

    /// 创建新章节。
    ///
    /// 自动生成 `id`（UUID v4）、计算 `word_count`、
    /// 设置 `sort_order` 为当前项目章节数、填充时间戳。
    pub fn create_chapter(&self, project_id: &str, title: &str, text: &str) -> CoreResult<ChapterData> {
        let conn = self.open()?;

        // 验证项目存在
        if xmgl_memory::get_project(&conn, project_id)?.is_none() {
            return Err(CoreError::NotFound(format!("project {project_id}")));
        }

        let now = Self::now_iso();
        let word_count = Self::count_words(text);
        let existing_count = xmgl_memory::chapter_count_for_project(&conn, project_id)?;

        let chapter = ChapterData {
            id: Uuid::new_v4().to_string(),
            project_id: project_id.to_string(),
            title: title.to_string(),
            text: text.to_string(),
            word_count,
            sort_order: existing_count, // 新章节排在最后
            created_at: now.clone(),
            updated_at: now,
        };

        xmgl_memory::insert_chapter(&conn, &chapter)?;
        drop(conn);

        // 更新项目统计
        self.recalc_project_stats(project_id)?;

        Ok(chapter)
    }

    /// 获取单个章节。
    pub fn get_chapter(&self, id: &str) -> CoreResult<Option<ChapterData>> {
        let conn = self.open()?;
        xmgl_memory::get_chapter(&conn, id)
    }

    /// 列出项目下所有章节（按 sort_order 升序）。
    pub fn list_chapters(&self, project_id: &str) -> CoreResult<Vec<ChapterData>> {
        let conn = self.open()?;
        xmgl_memory::list_chapters(&conn, project_id)
    }

    /// 更新章节。
    ///
    /// 自动更新 `updated_at` 时间戳并重新计算 `word_count`。
    pub fn update_chapter(&self, chapter: &ChapterData) -> CoreResult<ChapterData> {
        let conn = self.open()?;

        let mut updated = chapter.clone();
        updated.updated_at = Self::now_iso();
        updated.word_count = Self::count_words(&chapter.text);

        xmgl_memory::update_chapter(&conn, &updated)?;
        drop(conn);

        self.recalc_project_stats(&chapter.project_id)?;

        Ok(updated)
    }

    /// 删除章节。
    pub fn delete_chapter(&self, id: &str) -> CoreResult<()> {
        let conn = self.open()?;
        // 先找到 project_id 以便后续重新统计
        let project_id = xmgl_memory::get_chapter(&conn, id)?
            .map(|ch| ch.project_id.clone());

        xmgl_memory::delete_chapter(&conn, id)?;
        drop(conn);

        if let Some(pid) = project_id {
            self.recalc_project_stats(&pid)?;
        }

        Ok(())
    }

    // ── 统计 ──

    /// 重新计算项目的章节数和总字数，通过 xmgl-memory 写入。
    pub fn recalc_project_stats(&self, project_id: &str) -> CoreResult<()> {
        let conn = self.open()?;

        let mut meta = xmgl_memory::get_project(&conn, project_id)?
            .ok_or_else(|| CoreError::NotFound(format!("project {project_id}")))?;

        meta.chapter_count = xmgl_memory::chapter_count_for_project(&conn, project_id)?;
        meta.total_words = xmgl_memory::total_words_for_project(&conn, project_id)?;
        meta.updated_at = Self::now_iso();

        xmgl_memory::update_project(&conn, &meta)?;
        Ok(())
    }

    // ── ProjectContext ──

    /// 获取项目创作上下文。
    ///
    /// 如果项目尚无上下文记录，自动创建默认上下文并返回。
    pub fn get_project_context(&self, project_id: &str) -> CoreResult<Option<ProjectContext>> {
        let conn = self.open()?;
        xmgl_memory::get_project_context(&conn, project_id)
    }

    /// 保存项目创作上下文（乐观锁）。
    ///
    /// `expected_version`: 如果为 Some，先检查当前版本是否匹配。
    pub fn save_project_context(
        &self,
        ctx: &ProjectContext,
        expected_version: Option<u32>,
    ) -> CoreResult<ProjectContext> {
        let conn = self.open()?;
        xmgl_memory::upsert_project_context(&conn, ctx, expected_version)
    }

    // ── 旧数据迁移 ──

    /// 从 v3.1 JSON 项目目录迁移数据。
    ///
    /// Phase B: stub 实现，总是返回空报告。
    /// Phase E: 实现实际迁移逻辑（解析旧 JSON → 写入新 SQLite）。
    #[allow(dead_code)]
    pub fn migrate_from_v3(&self, _v3_project_path: &str) -> CoreResult<MigrationReport> {
        // TODO Phase E: 实现 v3.1 JSON → v4.0 SQLite 迁移逻辑
        Ok(MigrationReport {
            projects_migrated: 0,
            chapters_migrated: 0,
            errors: vec![],
        })
    }

    // ── 内部辅助 ──

    fn open(&self) -> CoreResult<Connection> {
        xmgl_memory::open_connection(&self.db_path)
    }

    fn now_iso() -> String {
        Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
    }

    /// 字数统计：中文按字符数，非中文按空格分词。
    fn count_words(text: &str) -> u32 {
        text.chars().filter(|c| !c.is_whitespace()).count() as u32
    }
}

// =========================================================================
// Tests
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    /// 测试上下文 — 自动清理临时数据库文件。
    struct TestContext {
        pm: ProjectManager,
        db_path: String,
    }

    impl Drop for TestContext {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.db_path);
        }
    }

    impl std::ops::Deref for TestContext {
        type Target = ProjectManager;
        fn deref(&self) -> &Self::Target {
            &self.pm
        }
    }

    fn setup() -> TestContext {
        let db_path = format!("test_xmgl_project_{}.db", Uuid::new_v4());
        let pm = ProjectManager::new(&db_path).expect("create ProjectManager");
        TestContext { pm, db_path }
    }

    // ── 项目 CRUD ──

    #[test]
    fn test_create_and_list_projects() {
        let pm = setup();
        let p1 = pm.create_project("Project A").unwrap();
        let _p2 = pm.create_project("Project B").unwrap();

        assert_eq!(p1.name, "Project A");
        assert!(!p1.id.is_empty());
        assert_eq!(p1.chapter_count, 0);
        assert_eq!(p1.total_words, 0);

        let list = pm.list_projects().unwrap();
        assert_eq!(list.len(), 2);
    }

    #[test]
    fn test_get_nonexistent_project() {
        let pm = setup();
        assert!(pm.get_project("no-such-id").unwrap().is_none());
    }

    #[test]
    fn test_delete_project() {
        let pm = setup();
        let p = pm.create_project("To Delete").unwrap();
        pm.delete_project(&p.id).unwrap();
        assert!(pm.get_project(&p.id).unwrap().is_none());
    }

    // ── 章节 CRUD ──

    #[test]
    fn test_create_chapter() {
        let pm = setup();
        let project = pm.create_project("Novel").unwrap();

        let ch = pm
            .create_chapter(&project.id, "Chapter 1", "It was a dark and stormy night.")
            .unwrap();

        assert_eq!(ch.title, "Chapter 1");
        assert_eq!(ch.word_count, 25); // "It was a dark and stormy night." (25 non-whitespace chars)
        assert_eq!(ch.sort_order, 0); // first chapter
        assert_eq!(ch.project_id, project.id);
    }

    #[test]
    fn test_create_chapter_nonexistent_project() {
        let pm = setup();
        let err = pm
            .create_chapter("no-such", "Title", "Text")
            .unwrap_err();
        assert!(matches!(err, CoreError::NotFound(_)));
    }

    #[test]
    fn test_list_chapters_sorted() {
        let pm = setup();
        let project = pm.create_project("Novel").unwrap();

        let ch1 = pm.create_chapter(&project.id, "Ch1", "a").unwrap();
        let ch2 = pm.create_chapter(&project.id, "Ch2", "b").unwrap();

        // sort_order 应递增
        assert_eq!(ch1.sort_order, 0);
        assert_eq!(ch2.sort_order, 1);

        let list = pm.list_chapters(&project.id).unwrap();
        assert_eq!(list.len(), 2);
        assert_eq!(list[0].sort_order, 0);
        assert_eq!(list[1].sort_order, 1);
    }

    #[test]
    fn test_update_chapter_recalculates_word_count() {
        let pm = setup();
        let project = pm.create_project("Novel").unwrap();
        let mut ch = pm.create_chapter(&project.id, "Ch1", "two words").unwrap();
        assert_eq!(ch.word_count, 8); // "two words" = 8 non-whitespace chars

        // 修改文本，word_count 应重新计算
        ch.text = "now five words here".into();
        pm.update_chapter(&ch).unwrap();

        let updated = pm.get_chapter(&ch.id).unwrap().unwrap();
        assert_eq!(updated.word_count, 16); // "now five words here" = 16 non-whitespace chars
        // updated_at 应被刷新（至少不为空）
        assert!(!updated.updated_at.is_empty());
    }

    #[test]
    fn test_delete_chapter() {
        let pm = setup();
        let project = pm.create_project("Novel").unwrap();
        let ch = pm.create_chapter(&project.id, "Ch1", "text").unwrap();

        pm.delete_chapter(&ch.id).unwrap();
        assert!(pm.get_chapter(&ch.id).unwrap().is_none());
    }

    #[test]
    fn test_recalc_project_stats() {
        let pm = setup();
        let project = pm.create_project("Novel").unwrap();

        pm.create_chapter(&project.id, "Ch1", "one two three").unwrap();
        pm.create_chapter(&project.id, "Ch2", "four five").unwrap();

        pm.recalc_project_stats(&project.id).unwrap();
        let updated = pm.get_project(&project.id).unwrap().unwrap();
        assert_eq!(updated.chapter_count, 2);
        assert_eq!(updated.total_words, 19); // "one two three"(11) + "four five"(8)
    }

    #[test]
    fn test_migration_report_stub() {
        let pm = setup();
        let report = pm.migrate_from_v3("/nonexistent").unwrap();
        assert_eq!(report.projects_migrated, 0);
        assert_eq!(report.chapters_migrated, 0);
        assert!(!report.has_errors());
    }

    #[test]
    fn test_db_path() {
        let pm = ProjectManager::new("test_path.db").unwrap();
        assert_eq!(pm.db_path(), "test_path.db");
        // clean up
        let _ = std::fs::remove_file("test_path.db");
    }
}
