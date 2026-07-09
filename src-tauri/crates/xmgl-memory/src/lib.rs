//! xmgl-memory — 三层记忆系统（工作/情节/永久）+ SQLite 持久化
//!
//! Phase B: 数据库初始化、项目/章节 CRUD、成本追踪。
//! Phase C 追加: episodic_memory, causality_graph, foreshadowing_registry, permanent_memory.

use chrono::Datelike;
use rusqlite::{params, Connection, Result as SqlResult};
use xmgl_core::{
    ChapterData, Character, CharacterRelation, CharacterStatus, CoreError, CoreResult,
    ForeshadowEntry, ForeshadowStatus, Location, ProjectMeta, TimelineEvent,
    TimelineEventType,
};

// =========================================================================
// 辅助: rusqlite → CoreError
// =========================================================================

fn map_err(e: rusqlite::Error) -> CoreError {
    CoreError::Internal(e.to_string())
}

// =========================================================================
// 成本追踪类型
// =========================================================================

/// 单次 LLM 调用成本记录。
#[derive(Debug, Clone)]
pub struct CostEntry {
    pub timestamp: String,
    pub agent_id: String,
    pub task_type: String,
    pub model: String,
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub cost_usd: f64,
    pub latency_ms: u32,
}

/// 预算熔断级别（对应三层熔断策略: 50% / 80% / 95%）。
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum BudgetFuseLevel {
    /// 低于 50%: 正常
    Normal,
    /// 50%–80%: 仅 Pro Agent 可用
    ProOnly,
    /// 80%–95%: 仅规则引擎可用
    RuleOnly,
    /// ≥95%: 熔断，禁止所有 LLM 调用
    Fused,
}

// =========================================================================
// 数据库初始化
// =========================================================================

/// 打开（或创建）SQLite 数据库，启用 WAL 模式 + 外键，并执行 migrations。
pub fn init_db(path: &str) -> CoreResult<Connection> {
    let conn = Connection::open(path).map_err(map_err)?;
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")
        .map_err(map_err)?;
    run_migrations(&conn)?;
    Ok(conn)
}

/// 仅打开连接，不执行 migrations（用于 ProjectManager 等已在 `new()` 中跑过迁移的场景）。
pub fn open_connection(path: &str) -> CoreResult<Connection> {
    let conn = Connection::open(path).map_err(map_err)?;
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")
        .map_err(map_err)?;
    Ok(conn)
}

/// 执行建表迁移（幂等 — 全部使用 IF NOT EXISTS）。
pub fn run_migrations(conn: &Connection) -> CoreResult<()> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            chapter_count INTEGER NOT NULL DEFAULT 0,
            total_words INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS project_settings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            key         TEXT NOT NULL,
            value       TEXT NOT NULL,
            UNIQUE(project_id, key)
        );

        CREATE TABLE IF NOT EXISTS chapters (
            id          TEXT PRIMARY KEY,
            project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            text        TEXT NOT NULL DEFAULT '',
            word_count   INTEGER NOT NULL DEFAULT 0,
            sort_order  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cost_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT NOT NULL,
            agent_id     TEXT NOT NULL,
            task_type    TEXT NOT NULL,
            model        TEXT NOT NULL,
            input_tokens  INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cost_usd     REAL NOT NULL,
            latency_ms   INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS monthly_budget (
            year       INTEGER NOT NULL,
            month      INTEGER NOT NULL,
            budget_usd REAL NOT NULL DEFAULT 20.0,
            spent_usd  REAL NOT NULL DEFAULT 0.0,
            PRIMARY KEY (year, month)
        );

        CREATE TABLE IF NOT EXISTS pad_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            chapter_id   TEXT NOT NULL,
            timestamp    TEXT NOT NULL,
            pleasure     REAL NOT NULL,
            arousal      REAL NOT NULL,
            dominance    REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analysis_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            agent_id    TEXT NOT NULL,
            chapter_id  TEXT NOT NULL,
            task_type   TEXT NOT NULL,
            result_json TEXT NOT NULL,
            cost_usd    REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS characters (
            id              TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            aliases         TEXT NOT NULL DEFAULT '[]',
            status          TEXT NOT NULL DEFAULT 'Alive',
            current_location TEXT,
            role            TEXT NOT NULL DEFAULT '',
            summary         TEXT NOT NULL DEFAULT '',
            first_appearance_chapter TEXT,
            source          TEXT NOT NULL DEFAULT 'manual',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS character_relations (
            id              TEXT PRIMARY KEY,
            character_a     TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
            character_b     TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
            relation_type   TEXT NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS locations (
            id              TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            aliases         TEXT NOT NULL DEFAULT '[]',
            location_type   TEXT NOT NULL DEFAULT '',
            parent_location TEXT,
            description     TEXT NOT NULL DEFAULT '',
            features        TEXT NOT NULL DEFAULT '[]',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS foreshadow_entries (
            id                  TEXT PRIMARY KEY,
            project_id          TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title               TEXT NOT NULL,
            description         TEXT NOT NULL DEFAULT '',
            quote               TEXT,
            setup_chapter_id    TEXT NOT NULL,
            payoff_chapter_id   TEXT,
            status              TEXT NOT NULL DEFAULT 'Planted',
            related_characters  TEXT NOT NULL DEFAULT '[]',
            related_locations   TEXT NOT NULL DEFAULT '[]',
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS timeline_events (
            id              TEXT PRIMARY KEY,
            chapter_id      TEXT NOT NULL,
            chapter_title   TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            related_entities TEXT NOT NULL DEFAULT '[]',
            sort_order      INTEGER NOT NULL DEFAULT 0
        );
        ",
    )
    .map_err(map_err)
}

// =========================================================================
// 项目 CRUD
// =========================================================================

pub fn insert_project(conn: &Connection, meta: &ProjectMeta) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO projects (id, name, created_at, updated_at, chapter_count, total_words)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![
            meta.id,
            meta.name,
            meta.created_at,
            meta.updated_at,
            meta.chapter_count,
            meta.total_words,
        ],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn list_projects(conn: &Connection) -> CoreResult<Vec<ProjectMeta>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, name, created_at, updated_at, chapter_count, total_words
             FROM projects ORDER BY updated_at DESC",
        )
        .map_err(map_err)?;

    let rows = stmt
        .query_map([], |row| {
            Ok(ProjectMeta {
                id: row.get(0)?,
                name: row.get(1)?,
                created_at: row.get(2)?,
                updated_at: row.get(3)?,
                chapter_count: row.get(4)?,
                total_words: row.get(5)?,
            })
        })
        .map_err(map_err)?;

    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn get_project(conn: &Connection, id: &str) -> CoreResult<Option<ProjectMeta>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, name, created_at, updated_at, chapter_count, total_words
             FROM projects WHERE id = ?1",
        )
        .map_err(map_err)?;

    let mut rows = stmt
        .query_map(params![id], |row| {
            Ok(ProjectMeta {
                id: row.get(0)?,
                name: row.get(1)?,
                created_at: row.get(2)?,
                updated_at: row.get(3)?,
                chapter_count: row.get(4)?,
                total_words: row.get(5)?,
            })
        })
        .map_err(map_err)?;

    match rows.next() {
        Some(Ok(meta)) => Ok(Some(meta)),
        Some(Err(e)) => Err(map_err(e)),
        None => Ok(None),
    }
}

pub fn update_project(conn: &Connection, meta: &ProjectMeta) -> CoreResult<()> {
    let affected = conn
        .execute(
            "UPDATE projects SET name = ?1, updated_at = ?2, chapter_count = ?3, total_words = ?4
             WHERE id = ?5",
            params![
                meta.name,
                meta.updated_at,
                meta.chapter_count,
                meta.total_words,
                meta.id,
            ],
        )
        .map_err(map_err)?;

    if affected == 0 {
        return Err(CoreError::NotFound(format!("project {}", meta.id)));
    }
    Ok(())
}

pub fn delete_project(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM projects WHERE id = ?1", params![id])
        .map_err(map_err)?;

    if affected == 0 {
        return Err(CoreError::NotFound(format!("project {id}")));
    }
    Ok(())
}

// =========================================================================
// 章节 CRUD
// =========================================================================

pub fn insert_chapter(conn: &Connection, chapter: &ChapterData) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO chapters (id, project_id, title, text, word_count, sort_order, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            chapter.id,
            chapter.project_id,
            chapter.title,
            chapter.text,
            chapter.word_count,
            chapter.sort_order,
            chapter.created_at,
            chapter.updated_at,
        ],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn get_chapter(conn: &Connection, id: &str) -> CoreResult<Option<ChapterData>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, title, text, word_count, sort_order, created_at, updated_at
             FROM chapters WHERE id = ?1",
        )
        .map_err(map_err)?;

    let mut rows = stmt
        .query_map(params![id], |row| {
            Ok(ChapterData {
                id: row.get(0)?,
                project_id: row.get(1)?,
                title: row.get(2)?,
                text: row.get(3)?,
                word_count: row.get(4)?,
                sort_order: row.get(5)?,
                created_at: row.get(6)?,
                updated_at: row.get(7)?,
            })
        })
        .map_err(map_err)?;

    match rows.next() {
        Some(Ok(ch)) => Ok(Some(ch)),
        Some(Err(e)) => Err(map_err(e)),
        None => Ok(None),
    }
}

pub fn list_chapters(conn: &Connection, project_id: &str) -> CoreResult<Vec<ChapterData>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, title, text, word_count, sort_order, created_at, updated_at
             FROM chapters WHERE project_id = ?1 ORDER BY sort_order ASC",
        )
        .map_err(map_err)?;

    let rows = stmt
        .query_map(params![project_id], |row| {
            Ok(ChapterData {
                id: row.get(0)?,
                project_id: row.get(1)?,
                title: row.get(2)?,
                text: row.get(3)?,
                word_count: row.get(4)?,
                sort_order: row.get(5)?,
                created_at: row.get(6)?,
                updated_at: row.get(7)?,
            })
        })
        .map_err(map_err)?;

    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn update_chapter(conn: &Connection, chapter: &ChapterData) -> CoreResult<()> {
    let affected = conn
        .execute(
            "UPDATE chapters SET title = ?1, text = ?2, word_count = ?3,
             sort_order = ?4, updated_at = ?5 WHERE id = ?6",
            params![
                chapter.title,
                chapter.text,
                chapter.word_count,
                chapter.sort_order,
                chapter.updated_at,
                chapter.id,
            ],
        )
        .map_err(map_err)?;

    if affected == 0 {
        return Err(CoreError::NotFound(format!("chapter {}", chapter.id)));
    }
    Ok(())
}

pub fn delete_chapter(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM chapters WHERE id = ?1", params![id])
        .map_err(map_err)?;

    if affected == 0 {
        return Err(CoreError::NotFound(format!("chapter {id}")));
    }
    Ok(())
}

pub fn chapter_count_for_project(conn: &Connection, project_id: &str) -> CoreResult<u32> {
    let count: u32 = conn
        .query_row(
            "SELECT COUNT(*) FROM chapters WHERE project_id = ?1",
            params![project_id],
            |row| row.get(0),
        )
        .map_err(map_err)?;
    Ok(count)
}

pub fn total_words_for_project(conn: &Connection, project_id: &str) -> CoreResult<u32> {
    let total: f64 = conn
        .query_row(
            "SELECT COALESCE(SUM(word_count), 0) FROM chapters WHERE project_id = ?1",
            params![project_id],
            |row| row.get(0),
        )
        .map_err(map_err)?;
    Ok(total as u32)
}

// =========================================================================
// JSON 辅助
// =========================================================================

fn ser_vec(v: &[String]) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "[]".into())
}

fn de_vec(s: &str) -> Vec<String> {
    serde_json::from_str(s).unwrap_or_default()
}

fn parse_status(s: &str) -> CharacterStatus {
    match s {
        "Dead" => CharacterStatus::Dead,
        "Unknown" => CharacterStatus::Unknown,
        _ => CharacterStatus::Alive,
    }
}

fn parse_foreshadow_status(s: &str) -> ForeshadowStatus {
    match s {
        "Hinted" => ForeshadowStatus::Hinted,
        "PayingOff" => ForeshadowStatus::PayingOff,
        "Resolved" => ForeshadowStatus::Resolved,
        _ => ForeshadowStatus::Planted,
    }
}

fn parse_timeline_event_type(s: &str) -> TimelineEventType {
    match s {
        "CharacterDeath" => TimelineEventType::CharacterDeath,
        "LocationIntro" => TimelineEventType::LocationIntro,
        "ForeshadowPlanted" => TimelineEventType::ForeshadowPlanted,
        "ForeshadowResolved" => TimelineEventType::ForeshadowResolved,
        "MajorPlotPoint" => TimelineEventType::MajorPlotPoint,
        "WorldRuleChange" => TimelineEventType::WorldRuleChange,
        _ => TimelineEventType::CharacterIntro,
    }
}

// =========================================================================
// 角色 CRUD
// =========================================================================

pub fn insert_character(conn: &Connection, c: &Character) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO characters (id, project_id, name, aliases, status, current_location,
         role, summary, first_appearance_chapter, source, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![
            c.id,
            c.project_id,
            c.name,
            ser_vec(&c.aliases),
            format!("{:?}", c.status),
            c.current_location,
            c.role,
            c.summary,
            c.first_appearance_chapter,
            c.source,
            c.created_at,
            c.updated_at,
        ],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn list_characters_by_project(conn: &Connection, project_id: &str) -> CoreResult<Vec<Character>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, name, aliases, status, current_location,
             role, summary, first_appearance_chapter, source, created_at, updated_at
             FROM characters WHERE project_id = ?1 ORDER BY name ASC",
        )
        .map_err(map_err)?;
    let rows = stmt
        .query_map(params![project_id], |row| {
            let aliases_str: String = row.get(3)?;
            let status_str: String = row.get(4)?;
            Ok(Character {
                id: row.get(0)?,
                project_id: row.get(1)?,
                name: row.get(2)?,
                aliases: de_vec(&aliases_str),
                status: parse_status(&status_str),
                current_location: row.get(5)?,
                role: row.get(6)?,
                summary: row.get(7)?,
                first_appearance_chapter: row.get(8)?,
                source: row.get(9)?,
                created_at: row.get(10)?,
                updated_at: row.get(11)?,
            })
        })
        .map_err(map_err)?;
    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn get_character(conn: &Connection, id: &str) -> CoreResult<Option<Character>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, name, aliases, status, current_location,
             role, summary, first_appearance_chapter, source, created_at, updated_at
             FROM characters WHERE id = ?1",
        )
        .map_err(map_err)?;
    let mut rows = stmt
        .query_map(params![id], |row| {
            let aliases_str: String = row.get(3)?;
            let status_str: String = row.get(4)?;
            Ok(Character {
                id: row.get(0)?,
                project_id: row.get(1)?,
                name: row.get(2)?,
                aliases: de_vec(&aliases_str),
                status: parse_status(&status_str),
                current_location: row.get(5)?,
                role: row.get(6)?,
                summary: row.get(7)?,
                first_appearance_chapter: row.get(8)?,
                source: row.get(9)?,
                created_at: row.get(10)?,
                updated_at: row.get(11)?,
            })
        })
        .map_err(map_err)?;
    match rows.next() {
        Some(Ok(ch)) => Ok(Some(ch)),
        Some(Err(e)) => Err(map_err(e)),
        None => Ok(None),
    }
}

pub fn update_character(conn: &Connection, c: &Character) -> CoreResult<()> {
    let affected = conn
        .execute(
            "UPDATE characters SET name = ?1, aliases = ?2, status = ?3,
             current_location = ?4, role = ?5, summary = ?6,
             first_appearance_chapter = ?7, source = ?8, updated_at = ?9
             WHERE id = ?10",
            params![
                c.name,
                ser_vec(&c.aliases),
                format!("{:?}", c.status),
                c.current_location,
                c.role,
                c.summary,
                c.first_appearance_chapter,
                c.source,
                c.updated_at,
                c.id,
            ],
        )
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("character {}", c.id)));
    }
    Ok(())
}

pub fn delete_character(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM characters WHERE id = ?1", params![id])
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("character {id}")));
    }
    Ok(())
}

// =========================================================================
// 角色关系 CRUD
// =========================================================================

pub fn insert_character_relation(conn: &Connection, r: &CharacterRelation) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO character_relations (id, character_a, character_b, relation_type, description, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![r.id, r.character_a, r.character_b, r.relation_type, r.description, r.created_at],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn list_character_relations(conn: &Connection, character_id: &str) -> CoreResult<Vec<CharacterRelation>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, character_a, character_b, relation_type, description, created_at
             FROM character_relations WHERE character_a = ?1 OR character_b = ?1
             ORDER BY created_at ASC",
        )
        .map_err(map_err)?;
    let rows = stmt
        .query_map(params![character_id], |row| {
            Ok(CharacterRelation {
                id: row.get(0)?,
                character_a: row.get(1)?,
                character_b: row.get(2)?,
                relation_type: row.get(3)?,
                description: row.get(4)?,
                created_at: row.get(5)?,
            })
        })
        .map_err(map_err)?;
    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn delete_character_relation(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM character_relations WHERE id = ?1", params![id])
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("character_relation {id}")));
    }
    Ok(())
}

// =========================================================================
// 地点 CRUD
// =========================================================================

pub fn insert_location(conn: &Connection, loc: &Location) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO locations (id, project_id, name, aliases, location_type,
         parent_location, description, features, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![
            loc.id,
            loc.project_id,
            loc.name,
            ser_vec(&loc.aliases),
            loc.location_type,
            loc.parent_location,
            loc.description,
            ser_vec(&loc.features),
            loc.created_at,
            loc.updated_at,
        ],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn list_locations_by_project(conn: &Connection, project_id: &str) -> CoreResult<Vec<Location>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, name, aliases, location_type, parent_location,
             description, features, created_at, updated_at
             FROM locations WHERE project_id = ?1 ORDER BY name ASC",
        )
        .map_err(map_err)?;
    let rows = stmt
        .query_map(params![project_id], |row| {
            let aliases_str: String = row.get(3)?;
            let features_str: String = row.get(7)?;
            Ok(Location {
                id: row.get(0)?,
                project_id: row.get(1)?,
                name: row.get(2)?,
                aliases: de_vec(&aliases_str),
                location_type: row.get(4)?,
                parent_location: row.get(5)?,
                description: row.get(6)?,
                features: de_vec(&features_str),
                created_at: row.get(8)?,
                updated_at: row.get(9)?,
            })
        })
        .map_err(map_err)?;
    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn get_location(conn: &Connection, id: &str) -> CoreResult<Option<Location>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, name, aliases, location_type, parent_location,
             description, features, created_at, updated_at
             FROM locations WHERE id = ?1",
        )
        .map_err(map_err)?;
    let mut rows = stmt
        .query_map(params![id], |row| {
            let aliases_str: String = row.get(3)?;
            let features_str: String = row.get(7)?;
            Ok(Location {
                id: row.get(0)?,
                project_id: row.get(1)?,
                name: row.get(2)?,
                aliases: de_vec(&aliases_str),
                location_type: row.get(4)?,
                parent_location: row.get(5)?,
                description: row.get(6)?,
                features: de_vec(&features_str),
                created_at: row.get(8)?,
                updated_at: row.get(9)?,
            })
        })
        .map_err(map_err)?;
    match rows.next() {
        Some(Ok(loc)) => Ok(Some(loc)),
        Some(Err(e)) => Err(map_err(e)),
        None => Ok(None),
    }
}

pub fn update_location(conn: &Connection, loc: &Location) -> CoreResult<()> {
    let affected = conn
        .execute(
            "UPDATE locations SET name = ?1, aliases = ?2, location_type = ?3,
             parent_location = ?4, description = ?5, features = ?6, updated_at = ?7
             WHERE id = ?8",
            params![
                loc.name,
                ser_vec(&loc.aliases),
                loc.location_type,
                loc.parent_location,
                loc.description,
                ser_vec(&loc.features),
                loc.updated_at,
                loc.id,
            ],
        )
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("location {}", loc.id)));
    }
    Ok(())
}

pub fn delete_location(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM locations WHERE id = ?1", params![id])
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("location {id}")));
    }
    Ok(())
}

// =========================================================================
// 伏笔 CRUD
// =========================================================================

pub fn insert_foreshadow(conn: &Connection, f: &ForeshadowEntry) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO foreshadow_entries (id, project_id, title, description, quote,
         setup_chapter_id, payoff_chapter_id, status, related_characters,
         related_locations, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![
            f.id,
            f.project_id,
            f.title,
            f.description,
            f.quote,
            f.setup_chapter_id,
            f.payoff_chapter_id,
            format!("{:?}", f.status),
            ser_vec(&f.related_characters),
            ser_vec(&f.related_locations),
            f.created_at,
            f.updated_at,
        ],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn list_foreshadows_by_project(conn: &Connection, project_id: &str) -> CoreResult<Vec<ForeshadowEntry>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, title, description, quote, setup_chapter_id,
             payoff_chapter_id, status, related_characters, related_locations,
             created_at, updated_at
             FROM foreshadow_entries WHERE project_id = ?1 ORDER BY created_at ASC",
        )
        .map_err(map_err)?;
    let rows = stmt
        .query_map(params![project_id], |row| {
            let rel_chars_str: String = row.get(8)?;
            let rel_locs_str: String = row.get(9)?;
            let status_str: String = row.get(7)?;
            Ok(ForeshadowEntry {
                id: row.get(0)?,
                project_id: row.get(1)?,
                title: row.get(2)?,
                description: row.get(3)?,
                quote: row.get(4)?,
                setup_chapter_id: row.get(5)?,
                payoff_chapter_id: row.get(6)?,
                status: parse_foreshadow_status(&status_str),
                related_characters: de_vec(&rel_chars_str),
                related_locations: de_vec(&rel_locs_str),
                created_at: row.get(10)?,
                updated_at: row.get(11)?,
            })
        })
        .map_err(map_err)?;
    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn get_foreshadow(conn: &Connection, id: &str) -> CoreResult<Option<ForeshadowEntry>> {
    let mut stmt = conn
        .prepare(
            "SELECT id, project_id, title, description, quote, setup_chapter_id,
             payoff_chapter_id, status, related_characters, related_locations,
             created_at, updated_at
             FROM foreshadow_entries WHERE id = ?1",
        )
        .map_err(map_err)?;
    let mut rows = stmt
        .query_map(params![id], |row| {
            let rel_chars_str: String = row.get(8)?;
            let rel_locs_str: String = row.get(9)?;
            let status_str: String = row.get(7)?;
            Ok(ForeshadowEntry {
                id: row.get(0)?,
                project_id: row.get(1)?,
                title: row.get(2)?,
                description: row.get(3)?,
                quote: row.get(4)?,
                setup_chapter_id: row.get(5)?,
                payoff_chapter_id: row.get(6)?,
                status: parse_foreshadow_status(&status_str),
                related_characters: de_vec(&rel_chars_str),
                related_locations: de_vec(&rel_locs_str),
                created_at: row.get(10)?,
                updated_at: row.get(11)?,
            })
        })
        .map_err(map_err)?;
    match rows.next() {
        Some(Ok(f)) => Ok(Some(f)),
        Some(Err(e)) => Err(map_err(e)),
        None => Ok(None),
    }
}

pub fn update_foreshadow(conn: &Connection, f: &ForeshadowEntry) -> CoreResult<()> {
    let affected = conn
        .execute(
            "UPDATE foreshadow_entries SET title = ?1, description = ?2, quote = ?3,
             payoff_chapter_id = ?4, status = ?5, related_characters = ?6,
             related_locations = ?7, updated_at = ?8
             WHERE id = ?9",
            params![
                f.title,
                f.description,
                f.quote,
                f.payoff_chapter_id,
                format!("{:?}", f.status),
                ser_vec(&f.related_characters),
                ser_vec(&f.related_locations),
                f.updated_at,
                f.id,
            ],
        )
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("foreshadow {}", f.id)));
    }
    Ok(())
}

pub fn delete_foreshadow(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM foreshadow_entries WHERE id = ?1", params![id])
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("foreshadow {id}")));
    }
    Ok(())
}

// =========================================================================
// 时间线 CRUD（只读 list，事件由分析写入）
// =========================================================================

pub fn insert_timeline_event(conn: &Connection, e: &TimelineEvent) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO timeline_events (id, chapter_id, chapter_title, event_type,
         description, related_entities, sort_order)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![
            e.id,
            e.chapter_id,
            e.chapter_title,
            format!("{:?}", e.event_type),
            e.description,
            ser_vec(&e.related_entities),
            e.sort_order,
        ],
    )
    .map_err(map_err)?;
    Ok(())
}

pub fn list_timeline_by_project(
    conn: &Connection,
    project_id: &str,
) -> CoreResult<Vec<TimelineEvent>> {
    let mut stmt = conn
        .prepare(
            "SELECT te.id, te.chapter_id, te.chapter_title, te.event_type,
             te.description, te.related_entities, te.sort_order
             FROM timeline_events te
             JOIN chapters c ON c.id = te.chapter_id
             WHERE c.project_id = ?1
             ORDER BY te.sort_order ASC",
        )
        .map_err(map_err)?;
    let rows = stmt
        .query_map(params![project_id], |row| {
            let entities_str: String = row.get(5)?;
            let et_str: String = row.get(3)?;
            Ok(TimelineEvent {
                id: row.get(0)?,
                chapter_id: row.get(1)?,
                chapter_title: row.get(2)?,
                event_type: parse_timeline_event_type(&et_str),
                description: row.get(4)?,
                related_entities: de_vec(&entities_str),
                sort_order: row.get(6)?,
            })
        })
        .map_err(map_err)?;
    rows.collect::<SqlResult<Vec<_>>>().map_err(map_err)
}

pub fn delete_timeline_event(conn: &Connection, id: &str) -> CoreResult<()> {
    let affected = conn
        .execute("DELETE FROM timeline_events WHERE id = ?1", params![id])
        .map_err(map_err)?;
    if affected == 0 {
        return Err(CoreError::NotFound(format!("timeline_event {id}")));
    }
    Ok(())
}

/// 记录一次 LLM 调用成本。
pub fn log_cost(conn: &Connection, entry: &CostEntry) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO cost_log (timestamp, agent_id, task_type, model,
         input_tokens, output_tokens, cost_usd, latency_ms)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            entry.timestamp,
            entry.agent_id,
            entry.task_type,
            entry.model,
            entry.input_tokens,
            entry.output_tokens,
            entry.cost_usd,
            entry.latency_ms,
        ],
    )
    .map_err(map_err)?;

    // 同步更新月度预算实际支出
    // 从 timestamp 提取年/月（假设 ISO 8601 格式 "2026-06-01T12:00:00"）
    if entry.timestamp.len() >= 7 {
        let year: i32 = entry.timestamp[..4].parse().unwrap_or(0);
        let month: i32 = entry.timestamp[5..7].parse().unwrap_or(0);
        if year > 0 && month > 0 {
            upsert_monthly_spent(conn, year, month, entry.cost_usd)?;
        }
    }
    Ok(())
}

/// 获取指定月份的总花费。
/// 该月份没有任何消费记录时返回 0.0。
pub fn get_monthly_cost(conn: &Connection, year: i32, month: i32) -> CoreResult<f64> {
    match conn.query_row(
        "SELECT spent_usd FROM monthly_budget WHERE year = ?1 AND month = ?2",
        params![year, month],
        |row| row.get(0),
    ) {
        Ok(spent) => Ok(spent),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(0.0),
        Err(e) => Err(map_err(e)),
    }
}

/// 获取月度预算上限（默认 $20）。
/// 该月份没有设置预算时返回默认值 $20。
pub fn get_monthly_budget(conn: &Connection, year: i32, month: i32) -> CoreResult<f64> {
    match conn.query_row(
        "SELECT budget_usd FROM monthly_budget WHERE year = ?1 AND month = ?2",
        params![year, month],
        |row| row.get(0),
    ) {
        Ok(budget) => Ok(budget),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(20.0),
        Err(e) => Err(map_err(e)),
    }
}

/// 设置月度预算上限。
pub fn set_monthly_budget(conn: &Connection, year: i32, month: i32, budget_usd: f64) -> CoreResult<()> {
    conn.execute(
        "INSERT INTO monthly_budget (year, month, budget_usd, spent_usd)
         VALUES (?1, ?2, ?3, 0.0)
         ON CONFLICT(year, month) DO UPDATE SET budget_usd = ?3",
        params![year, month, budget_usd],
    )
    .map_err(map_err)?;
    Ok(())
}

/// 检查当前熔断级别。
///
/// 三层熔断：
/// - Normal:  < 50%
/// - ProOnly: 50%–80%（仅 Pro 级 Agent 可调用）
/// - RuleOnly: 80%–95%（仅规则引擎可用）
/// - Fused: ≥ 95%（禁止所有 LLM 调用）
pub fn check_budget_fuse(conn: &Connection) -> CoreResult<BudgetFuseLevel> {
    // 获取当前月份
    // 使用 chrono 获取当前 UTC 时间作为 fallback
    let now = chrono::Utc::now();
    let year = now.year();
    let month = now.month() as i32;

    let spent = get_monthly_cost(conn, year, month)?;
    let budget = get_monthly_budget(conn, year, month)?;

    if budget <= 0.0 {
        return Ok(BudgetFuseLevel::Fused);
    }

    let ratio = spent / budget;

    if ratio >= 0.95 {
        Ok(BudgetFuseLevel::Fused)
    } else if ratio >= 0.80 {
        Ok(BudgetFuseLevel::RuleOnly)
    } else if ratio >= 0.50 {
        Ok(BudgetFuseLevel::ProOnly)
    } else {
        Ok(BudgetFuseLevel::Normal)
    }
}

// =========================================================================
// 内部辅助
// =========================================================================

fn upsert_monthly_spent(conn: &Connection, year: i32, month: i32, delta: f64) -> CoreResult<()> {
    // 确保行存在
    conn.execute(
        "INSERT INTO monthly_budget (year, month, budget_usd, spent_usd)
         VALUES (?1, ?2, 20.0, 0.0)
         ON CONFLICT(year, month) DO NOTHING",
        params![year, month],
    )
    .map_err(map_err)?;

    conn.execute(
        "UPDATE monthly_budget SET spent_usd = spent_usd + ?1
         WHERE year = ?2 AND month = ?3",
        params![delta, year, month],
    )
    .map_err(map_err)?;

    Ok(())
}

// =========================================================================
// Tests
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> Connection {
        let conn = Connection::open_in_memory().expect("in-memory db");
        conn.execute("PRAGMA foreign_keys=ON", []).expect("fk on");
        run_migrations(&conn).expect("migrations");
        conn
    }

    fn sample_project(id: &str, name: &str) -> ProjectMeta {
        ProjectMeta {
            id: id.into(),
            name: name.into(),
            created_at: "2026-06-01T00:00:00Z".into(),
            updated_at: "2026-06-01T00:00:00Z".into(),
            chapter_count: 0,
            total_words: 0,
        }
    }

    fn sample_chapter(id: &str, project_id: &str, sort_order: u32) -> ChapterData {
        ChapterData {
            id: id.into(),
            project_id: project_id.into(),
            title: format!("Chapter {id}"),
            text: "Sample text content.".into(),
            word_count: 3,
            sort_order,
            created_at: "2026-06-01T00:00:00Z".into(),
            updated_at: "2026-06-01T00:00:00Z".into(),
        }
    }

    // ── 数据库初始化 ──

    #[test]
    fn test_init_db_in_memory() {
        let conn = init_db(":memory:").expect("init_db");
        // 验证所有表存在
        let tables: Vec<String> = conn
            .prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            .unwrap()
            .query_map([], |row| row.get(0))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        for expected in &[
            "projects",
            "project_settings",
            "chapters",
            "cost_log",
            "monthly_budget",
            "pad_history",
            "analysis_history",
            "characters",
            "character_relations",
            "locations",
            "foreshadow_entries",
            "timeline_events",
        ] {
            assert!(
                tables.contains(&expected.to_string()),
                "table {expected} missing"
            );
        }
    }

    #[test]
    fn test_migrations_idempotent() {
        let conn = setup();
        // 第二次 run_migrations 不应该失败
        assert!(run_migrations(&conn).is_ok());
    }

    // ── 项目 CRUD ──

    #[test]
    fn test_insert_and_get_project() {
        let conn = setup();
        let p = sample_project("p1", "My Project");
        insert_project(&conn, &p).unwrap();

        let got = get_project(&conn, "p1").unwrap().expect("should exist");
        assert_eq!(got.name, "My Project");
    }

    #[test]
    fn test_get_nonexistent_project() {
        let conn = setup();
        let got = get_project(&conn, "no-such").unwrap();
        assert!(got.is_none());
    }

    #[test]
    fn test_list_projects() {
        let conn = setup();
        insert_project(&conn, &sample_project("a", "A")).unwrap();
        insert_project(&conn, &sample_project("b", "B")).unwrap();

        let list = list_projects(&conn).unwrap();
        assert_eq!(list.len(), 2);
    }

    #[test]
    fn test_update_project() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "Old")).unwrap();

        let mut updated = get_project(&conn, "p1").unwrap().unwrap();
        updated.name = "New".into();
        updated.updated_at = "2026-06-02T00:00:00Z".into();
        update_project(&conn, &updated).unwrap();

        let got = get_project(&conn, "p1").unwrap().unwrap();
        assert_eq!(got.name, "New");
    }

    #[test]
    fn test_update_nonexistent_project() {
        let conn = setup();
        let err = update_project(&conn, &sample_project("ghost", "Ghost")).unwrap_err();
        assert!(matches!(err, CoreError::NotFound(_)));
    }

    #[test]
    fn test_delete_project() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "X")).unwrap();
        delete_project(&conn, "p1").unwrap();
        assert!(get_project(&conn, "p1").unwrap().is_none());
    }

    #[test]
    fn test_delete_project_cascades_chapters() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "X")).unwrap();
        insert_chapter(&conn, &sample_chapter("ch1", "p1", 0)).unwrap();
        delete_project(&conn, "p1").unwrap();

        // 章节应级联删除
        assert!(get_chapter(&conn, "ch1").unwrap().is_none());
    }

    // ── 章节 CRUD ──

    #[test]
    fn test_insert_and_get_chapter() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        let ch = sample_chapter("ch1", "p1", 0);
        insert_chapter(&conn, &ch).unwrap();

        let got = get_chapter(&conn, "ch1").unwrap().expect("should exist");
        assert_eq!(got.title, "Chapter ch1");
        assert_eq!(got.sort_order, 0);
    }

    #[test]
    fn test_list_chapters_sorted() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_chapter(&conn, &sample_chapter("ch2", "p1", 2)).unwrap();
        insert_chapter(&conn, &sample_chapter("ch1", "p1", 1)).unwrap();
        insert_chapter(&conn, &sample_chapter("ch0", "p1", 0)).unwrap();

        let list = list_chapters(&conn, "p1").unwrap();
        assert_eq!(list.len(), 3);
        // 按 sort_order ASC 排序
        assert_eq!(list[0].id, "ch0");
        assert_eq!(list[1].id, "ch1");
        assert_eq!(list[2].id, "ch2");
    }

    #[test]
    fn test_update_chapter() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_chapter(&conn, &sample_chapter("ch1", "p1", 0)).unwrap();

        let mut ch = get_chapter(&conn, "ch1").unwrap().unwrap();
        ch.title = "Updated Title".into();
        ch.sort_order = 99;
        update_chapter(&conn, &ch).unwrap();

        let got = get_chapter(&conn, "ch1").unwrap().unwrap();
        assert_eq!(got.title, "Updated Title");
        assert_eq!(got.sort_order, 99);
    }

    #[test]
    fn test_delete_chapter() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_chapter(&conn, &sample_chapter("ch1", "p1", 0)).unwrap();
        delete_chapter(&conn, "ch1").unwrap();
        assert!(get_chapter(&conn, "ch1").unwrap().is_none());
    }

    #[test]
    fn test_chapter_count_and_total_words() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();

        let ch1 = ChapterData {
            word_count: 100,
            ..sample_chapter("ch1", "p1", 0)
        };
        let ch2 = ChapterData {
            word_count: 200,
            ..sample_chapter("ch2", "p1", 1)
        };
        insert_chapter(&conn, &ch1).unwrap();
        insert_chapter(&conn, &ch2).unwrap();

        assert_eq!(chapter_count_for_project(&conn, "p1").unwrap(), 2);
        assert_eq!(total_words_for_project(&conn, "p1").unwrap(), 300);
    }

    // ── 成本追踪 ──

    #[test]
    fn test_log_cost_and_get_monthly() {
        let conn = setup();

        let entry = CostEntry {
            timestamp: "2026-06-15T12:00:00Z".into(),
            agent_id: "Character".into(),
            task_type: "pad_compute".into(),
            model: "deepseek-v4-pro".into(),
            input_tokens: 500,
            output_tokens: 200,
            cost_usd: 0.015,
            latency_ms: 1200,
        };
        log_cost(&conn, &entry).unwrap();

        let spent = get_monthly_cost(&conn, 2026, 6).unwrap();
        assert!((spent - 0.015).abs() < 0.001);
    }

    #[test]
    fn test_budget_fuse_levels() {
        let conn = setup();

        // 0% spent → Normal
        assert_eq!(
            check_budget_fuse(&conn).unwrap(),
            BudgetFuseLevel::Normal
        );

        // 手动设置 55% spent → ProOnly
        conn.execute(
            "INSERT INTO monthly_budget (year, month, budget_usd, spent_usd)
             VALUES (2026, ?, 20.0, 11.0)
             ON CONFLICT(year, month) DO UPDATE SET spent_usd = 11.0",
            params![chrono::Utc::now().month()],
        )
        .unwrap();
        assert_eq!(
            check_budget_fuse(&conn).unwrap(),
            BudgetFuseLevel::ProOnly
        );

        // 85% → RuleOnly
        conn.execute(
            "UPDATE monthly_budget SET spent_usd = 17.0 WHERE year = 2026 AND month = ?",
            params![chrono::Utc::now().month()],
        )
        .unwrap();
        assert_eq!(
            check_budget_fuse(&conn).unwrap(),
            BudgetFuseLevel::RuleOnly
        );

        // 96% → Fused
        conn.execute(
            "UPDATE monthly_budget SET spent_usd = 19.2 WHERE year = 2026 AND month = ?",
            params![chrono::Utc::now().month()],
        )
        .unwrap();
        assert_eq!(
            check_budget_fuse(&conn).unwrap(),
            BudgetFuseLevel::Fused
        );
    }

    #[test]
    fn test_set_monthly_budget() {
        let conn = setup();
        set_monthly_budget(&conn, 2026, 7, 30.0).unwrap();
        let budget = get_monthly_budget(&conn, 2026, 7).unwrap();
        assert!((budget - 30.0).abs() < 0.001);
    }

    // ── 角色 CRUD ──

    fn sample_character(id: &str, project_id: &str, name: &str) -> Character {
        Character {
            id: id.into(),
            project_id: project_id.into(),
            name: name.into(),
            aliases: vec![],
            status: CharacterStatus::Alive,
            current_location: None,
            role: "protagonist".into(),
            summary: "A test character".into(),
            first_appearance_chapter: None,
            source: "manual".into(),
            created_at: "2026-07-01T00:00:00Z".into(),
            updated_at: "2026-07-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn test_insert_and_get_character() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        let c = sample_character("c1", "p1", "张三");
        insert_character(&conn, &c).unwrap();
        let got = get_character(&conn, "c1").unwrap().expect("should exist");
        assert_eq!(got.name, "张三");
        assert_eq!(got.status, CharacterStatus::Alive);
    }

    #[test]
    fn test_list_characters_by_project() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_character(&conn, &sample_character("c1", "p1", "B")).unwrap();
        insert_character(&conn, &sample_character("c2", "p1", "A")).unwrap();
        let list = list_characters_by_project(&conn, "p1").unwrap();
        assert_eq!(list.len(), 2);
        // sorted by name ASC
        assert_eq!(list[0].name, "A");
        assert_eq!(list[1].name, "B");
    }

    #[test]
    fn test_update_character() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_character(&conn, &sample_character("c1", "p1", "Old")).unwrap();
        let mut c = get_character(&conn, "c1").unwrap().unwrap();
        c.name = "New".into();
        c.status = CharacterStatus::Dead;
        update_character(&conn, &c).unwrap();
        let got = get_character(&conn, "c1").unwrap().unwrap();
        assert_eq!(got.name, "New");
        assert_eq!(got.status, CharacterStatus::Dead);
    }

    #[test]
    fn test_delete_character() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_character(&conn, &sample_character("c1", "p1", "X")).unwrap();
        delete_character(&conn, "c1").unwrap();
        assert!(get_character(&conn, "c1").unwrap().is_none());
    }

    #[test]
    fn test_character_aliases_roundtrip() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        let mut c = sample_character("c1", "p1", "主角");
        c.aliases = vec!["大侠".into(), "英雄".into()];
        insert_character(&conn, &c).unwrap();
        let got = get_character(&conn, "c1").unwrap().unwrap();
        assert_eq!(got.aliases, vec!["大侠", "英雄"]);
    }

    // ── 角色关系 CRUD ──

    #[test]
    fn test_insert_and_list_relations() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_character(&conn, &sample_character("c1", "p1", "A")).unwrap();
        insert_character(&conn, &sample_character("c2", "p1", "B")).unwrap();
        let rel = CharacterRelation {
            id: "r1".into(),
            character_a: "c1".into(),
            character_b: "c2".into(),
            relation_type: "friend".into(),
            description: "好友".into(),
            created_at: "2026-07-01T00:00:00Z".into(),
        };
        insert_character_relation(&conn, &rel).unwrap();
        let list = list_character_relations(&conn, "c1").unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].relation_type, "friend");
    }

    // ── 地点 CRUD ──

    fn sample_location(id: &str, project_id: &str, name: &str) -> Location {
        Location {
            id: id.into(),
            project_id: project_id.into(),
            name: name.into(),
            aliases: vec![],
            location_type: "city".into(),
            parent_location: None,
            description: "A test location".into(),
            features: vec![],
            created_at: "2026-07-01T00:00:00Z".into(),
            updated_at: "2026-07-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn test_insert_and_get_location() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        let loc = sample_location("l1", "p1", "长安城");
        insert_location(&conn, &loc).unwrap();
        let got = get_location(&conn, "l1").unwrap().expect("should exist");
        assert_eq!(got.name, "长安城");
    }

    #[test]
    fn test_update_location() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_location(&conn, &sample_location("l1", "p1", "Old")).unwrap();
        let mut loc = get_location(&conn, "l1").unwrap().unwrap();
        loc.name = "New".into();
        loc.features = vec!["large".into(), "ancient".into()];
        update_location(&conn, &loc).unwrap();
        let got = get_location(&conn, "l1").unwrap().unwrap();
        assert_eq!(got.name, "New");
        assert_eq!(got.features, vec!["large", "ancient"]);
    }

    #[test]
    fn test_delete_location() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_location(&conn, &sample_location("l1", "p1", "X")).unwrap();
        delete_location(&conn, "l1").unwrap();
        assert!(get_location(&conn, "l1").unwrap().is_none());
    }

    // ── 伏笔 CRUD ──

    fn sample_foreshadow(id: &str, project_id: &str) -> ForeshadowEntry {
        ForeshadowEntry {
            id: id.into(),
            project_id: project_id.into(),
            title: "神秘信件".into(),
            description: "主角收到一封神秘信件".into(),
            quote: Some("\"你已被选中\"".into()),
            setup_chapter_id: "ch1".into(),
            payoff_chapter_id: None,
            status: ForeshadowStatus::Planted,
            related_characters: vec!["c1".into()],
            related_locations: vec![],
            created_at: "2026-07-01T00:00:00Z".into(),
            updated_at: "2026-07-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn test_insert_and_get_foreshadow() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        let f = sample_foreshadow("f1", "p1");
        insert_foreshadow(&conn, &f).unwrap();
        let got = get_foreshadow(&conn, "f1").unwrap().expect("should exist");
        assert_eq!(got.title, "神秘信件");
        assert_eq!(got.status, ForeshadowStatus::Planted);
    }

    #[test]
    fn test_update_foreshadow_status() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_foreshadow(&conn, &sample_foreshadow("f1", "p1")).unwrap();
        let mut f = get_foreshadow(&conn, "f1").unwrap().unwrap();
        f.status = ForeshadowStatus::Resolved;
        f.payoff_chapter_id = Some("ch5".into());
        update_foreshadow(&conn, &f).unwrap();
        let got = get_foreshadow(&conn, "f1").unwrap().unwrap();
        assert_eq!(got.status, ForeshadowStatus::Resolved);
        assert_eq!(got.payoff_chapter_id, Some("ch5".into()));
    }

    #[test]
    fn test_delete_foreshadow() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_foreshadow(&conn, &sample_foreshadow("f1", "p1")).unwrap();
        delete_foreshadow(&conn, "f1").unwrap();
        assert!(get_foreshadow(&conn, "f1").unwrap().is_none());
    }

    // ── 时间线 CRUD ──

    #[test]
    fn test_insert_and_list_timeline() {
        let conn = setup();
        insert_project(&conn, &sample_project("p1", "P")).unwrap();
        insert_chapter(&conn, &sample_chapter("ch1", "p1", 0)).unwrap();
        let ev = TimelineEvent {
            id: "t1".into(),
            chapter_id: "ch1".into(),
            chapter_title: "第一章".into(),
            event_type: TimelineEventType::CharacterIntro,
            description: "主角出场".into(),
            related_entities: vec!["c1".into()],
            sort_order: 0,
        };
        insert_timeline_event(&conn, &ev).unwrap();
        let list = list_timeline_by_project(&conn, "p1").unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].description, "主角出场");
        assert!(matches!(list[0].event_type, TimelineEventType::CharacterIntro));
    }
}
