"""
情节记忆 (Episodic Memory) — Phase 2

职责：章节级持久化存储，SQLite 后端。
热数据：近 10 章（内存缓存 + SQLite）
冷数据：10 章前（SQLite only）

契约（来源：02-CONTRACTS.md, 05-MEMORY-SYSTEM.md）：
- 只有编排器有写入权限
- 读取无限制
- 返回数据必须带 last_modified 时间戳
- 10 章后下沉冷存储
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class EpisodicEntry:
    """情节记忆单条记录"""

    id: str
    chapter_id: str
    memory_type: str  # behavior_log | world_event | pad_history | chapter_summary | conflict_resolution
    character_id: Optional[str] = None
    data: dict = field(default_factory=dict)
    confidence: float = 0.5
    created_at: str = ""
    last_modified: str = ""


@dataclass
class EpisodicQuery:
    """情节记忆查询"""

    chapter_id: Optional[str] = None
    chapter_range: Optional[tuple[str, str]] = None
    character_id: Optional[str] = None
    memory_type: Optional[str] = None
    min_confidence: float = 0.0
    top_k: int = 10
    include_cold: bool = False  # 是否包含冷数据


@dataclass
class EpisodicStats:
    """情节记忆统计"""

    total_entries: int = 0
    hot_entries: int = 0
    cold_entries: int = 0
    chapters_covered: int = 0
    db_size_bytes: int = 0


# ---------------------------------------------------------------------------
# 热数据缓存
# ---------------------------------------------------------------------------

class HotCache:
    """近 10 章热数据缓存（LRU 按章节）"""

    def __init__(self, max_chapters: int = 10) -> None:
        self._max = max_chapters
        self._cache: dict[str, list[EpisodicEntry]] = {}  # chapter_id → entries

    def get(self, chapter_id: str) -> list[EpisodicEntry]:
        """从缓存读取某章节的所有条目"""
        return self._cache.get(chapter_id, [])

    def put(self, chapter_id: str, entries: list[EpisodicEntry]) -> None:
        """写入缓存，超量时淘汰最旧章节"""
        self._cache[chapter_id] = entries
        if len(self._cache) > self._max:
            # 按 chapter_id 排序，淘汰最小的（近似最旧）
            oldest = sorted(self._cache.keys())[0]
            del self._cache[oldest]

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    @property
    def chapter_ids(self) -> list[str]:
        return list(self._cache.keys())


# ---------------------------------------------------------------------------
# 情节记忆实现
# ---------------------------------------------------------------------------

class EpisodicMemory:
    """情节记忆 — Phase 2

    章节级持久化存储，SQLite 后端。
    热数据缓存近 10 章在内存中。
    """

    def __init__(self, db_path: str = "projects/memory/episodic.db") -> None:
        """初始化情节记忆

        Args:
            db_path: SQLite 数据库路径
        """
        self._db_path = db_path
        self._hot_cache = HotCache(max_chapters=10)

        # 确保目录存在
        import os
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化数据库
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 表结构"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id TEXT PRIMARY KEY,
                    chapter_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    character_id TEXT,
                    data TEXT NOT NULL DEFAULT '{}',
                    confidence REAL DEFAULT 0.5,
                    created_at TEXT DEFAULT (datetime('now')),
                    last_modified TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ep_chapter
                ON episodic_memory(chapter_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ep_character
                ON episodic_memory(character_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ep_type
                ON episodic_memory(memory_type)
            """)

            # Phase 2: 因果图谱表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS causality_graph (
                    id TEXT PRIMARY KEY,
                    chapter_id TEXT NOT NULL,
                    cause_event TEXT NOT NULL,
                    effect_event TEXT NOT NULL,
                    strength REAL DEFAULT 0.5,
                    description TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cg_chapter
                ON causality_graph(chapter_id)
            """)

            # Phase 2: 伏笔登记表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS foreshadowing_registry (
                    foreshadow_id TEXT PRIMARY KEY,
                    chapter_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    hint_text TEXT DEFAULT '',
                    category TEXT DEFAULT 'unknown',
                    status TEXT DEFAULT 'planted',
                    resolved_in TEXT,
                    related_characters TEXT DEFAULT '[]',
                    confidence REAL DEFAULT 0.5,
                    created_at TEXT DEFAULT (datetime('now')),
                    last_modified TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fs_status
                ON foreshadowing_registry(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fs_chapter
                ON foreshadowing_registry(chapter_id)
            """)

            conn.commit()

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def write(
        self,
        chapter_id: str,
        memory_type: str,
        data: dict,
        character_id: Optional[str] = None,
        confidence: float = 0.5,
    ) -> str:
        """写入一条情节记忆

        Args:
            chapter_id: 章节标识
            memory_type: 记忆类型
            data: 载荷数据
            character_id: 关联角色（可选）
            confidence: 置信度

        Returns:
            条目 ID
        """
        entry_id = str(uuid.uuid4())[:12]
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # 写入 SQLite
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO episodic_memory
                   (id, chapter_id, memory_type, character_id, data, confidence, created_at, last_modified)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, chapter_id, memory_type, character_id,
                 json.dumps(data, ensure_ascii=False), confidence, now, now),
            )
            conn.commit()

        # 更新热缓存
        self._refresh_hot_cache(chapter_id)

        return entry_id

    def read(self, query: EpisodicQuery) -> list[EpisodicEntry]:
        """读取情节记忆

        Args:
            query: 查询条件

        Returns:
            匹配的条目列表
        """
        # 1. 尝试从热缓存读取
        if query.chapter_id and query.chapter_id in self._hot_cache.chapter_ids:
            cached = self._hot_cache.get(query.chapter_id)
            results = self._filter_entries(cached, query)
            if results:
                return results[:query.top_k]

        # 2. SQLite 查询
        sql = "SELECT id, chapter_id, memory_type, character_id, data, confidence, created_at, last_modified FROM episodic_memory WHERE 1=1"
        params: list = []

        if query.chapter_id:
            sql += " AND chapter_id = ?"
            params.append(query.chapter_id)

        if query.chapter_range:
            sql += " AND chapter_id >= ? AND chapter_id <= ?"
            params.extend(query.chapter_range)

        if query.character_id:
            sql += " AND character_id = ?"
            params.append(query.character_id)

        if query.memory_type:
            sql += " AND memory_type = ?"
            params.append(query.memory_type)

        if query.min_confidence > 0:
            sql += " AND confidence >= ?"
            params.append(query.min_confidence)

        sql += " ORDER BY last_modified DESC"
        sql += f" LIMIT {query.top_k}"

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

        entries = [self._row_to_entry(r) for r in rows]

        # 缓存热数据
        if query.chapter_id and entries:
            self._hot_cache.put(query.chapter_id, entries)

        return entries

    def get_chapter_summary(self, chapter_id: str) -> Optional[dict]:
        """获取章节摘要

        Args:
            chapter_id: 章节 ID

        Returns:
            摘要数据字典，未找到返回 None
        """
        entries = self.read(EpisodicQuery(
            chapter_id=chapter_id,
            memory_type="chapter_summary",
            top_k=1,
        ))
        return entries[0].data if entries else None

    def get_character_history(
        self,
        character_id: str,
        top_k: int = 10,
    ) -> list[EpisodicEntry]:
        """获取角色相关历史

        Args:
            character_id: 角色 ID
            top_k: 最大返回数

        Returns:
            该角色相关的记忆条目
        """
        return self.read(EpisodicQuery(
            character_id=character_id,
            top_k=top_k,
            include_cold=True,
        ))

    def get_chapters_since(self, chapter_id: str, limit: int = 10) -> list[str]:
        """获取指定章节之前的章节 ID 列表

        Args:
            chapter_id: 参考章节
            limit: 最大返回数

        Returns:
            章节 ID 列表（按时间倒序）
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """SELECT DISTINCT chapter_id FROM episodic_memory
                   WHERE chapter_id < ?
                   ORDER BY chapter_id DESC
                   LIMIT ?""",
                (chapter_id, limit),
            )
            return [r[0] for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 因果图谱操作 (Phase 2)
    # ------------------------------------------------------------------

    def add_causal_link(
        self,
        chapter_id: str,
        cause_event: str,
        effect_event: str,
        strength: float = 0.5,
        description: str = "",
    ) -> str:
        """添加一条因果链

        Args:
            chapter_id: 章节 ID
            cause_event: 原因事件
            effect_event: 结果事件
            strength: 因果强度
            description: 说明

        Returns:
            因果链 ID
        """
        link_id = str(uuid.uuid4())[:12]
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO causality_graph
                   (id, chapter_id, cause_event, effect_event, strength, description)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (link_id, chapter_id, cause_event, effect_event, strength, description),
            )
            conn.commit()
        return link_id

    def get_causal_links(
        self,
        chapter_id: Optional[str] = None,
        top_k: int = 20,
    ) -> list[dict]:
        """获取因果链

        Args:
            chapter_id: 限定章节（可选）
            top_k: 最大返回数

        Returns:
            因果链字典列表
        """
        sql = "SELECT id, chapter_id, cause_event, effect_event, strength, description FROM causality_graph"
        params: list = []

        if chapter_id:
            sql += " WHERE chapter_id = ?"
            params.append(chapter_id)

        sql += " ORDER BY chapter_id DESC, strength DESC LIMIT ?"
        params.append(top_k)

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 伏笔登记表操作 (Phase 2)
    # ------------------------------------------------------------------

    def register_foreshadowing(
        self,
        foreshadow_id: str,
        chapter_id: str,
        description: str,
        hint_text: str = "",
        category: str = "unknown",
        related_characters: Optional[list[str]] = None,
        confidence: float = 0.5,
    ) -> str:
        """注册一个伏笔

        Args:
            foreshadow_id: 伏笔标识
            chapter_id: 出现章节
            description: 描述
            hint_text: 原文片段
            category: 类型
            related_characters: 关联角色
            confidence: 置信度

        Returns:
            伏笔 ID
        """
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        chars = json.dumps(related_characters or [], ensure_ascii=False)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO foreshadowing_registry
                   (foreshadow_id, chapter_id, description, hint_text, category, status,
                    related_characters, confidence, last_modified)
                   VALUES (?, ?, ?, ?, ?, 'planted', ?, ?, ?)""",
                (foreshadow_id, chapter_id, description, hint_text, category,
                 chars, confidence, now),
            )
            conn.commit()
        return foreshadow_id

    def resolve_foreshadowing(self, foreshadow_id: str, resolved_in: str) -> bool:
        """标记伏笔为已回收

        Args:
            foreshadow_id: 伏笔 ID
            resolved_in: 回收伏笔的章节 ID

        Returns:
            是否成功
        """
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """UPDATE foreshadowing_registry
                   SET status = 'resolved', resolved_in = ?, last_modified = ?
                   WHERE foreshadow_id = ?""",
                (resolved_in, now, foreshadow_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_unresolved_foreshadowings(self) -> list[dict]:
        """获取所有未回收的伏笔

        Returns:
            未回收伏笔列表
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM foreshadowing_registry
                   WHERE status != 'resolved'
                   ORDER BY chapter_id DESC"""
            )
            return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 维护操作
    # ------------------------------------------------------------------

    def get_stats(self) -> EpisodicStats:
        """获取统计信息

        Returns:
            EpisodicStats 实例
        """
        with sqlite3.connect(self._db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM episodic_memory"
            ).fetchone()[0]
            chapters = conn.execute(
                "SELECT COUNT(DISTINCT chapter_id) FROM episodic_memory"
            ).fetchone()[0]

        import os
        db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0

        return EpisodicStats(
            total_entries=total,
            hot_entries=sum(len(v) for v in self._hot_cache._cache.values()),
            cold_entries=total - sum(len(v) for v in self._hot_cache._cache.values()),
            chapters_covered=chapters,
            db_size_bytes=db_size,
        )

    def flush_cache(self, chapter_id: str) -> None:
        """刷新特定章节的缓存（写入后调用）

        Args:
            chapter_id: 章节 ID
        """
        self._refresh_hot_cache(chapter_id)

    def _refresh_hot_cache(self, chapter_id: str) -> None:
        """从 SQLite 刷新指定章节的热缓存"""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT id, chapter_id, memory_type, character_id, data, confidence, created_at, last_modified
                   FROM episodic_memory WHERE chapter_id = ?
                   ORDER BY last_modified DESC LIMIT 100""",
                (chapter_id,),
            )
            rows = cursor.fetchall()

        if rows:
            self._hot_cache.put(chapter_id, [self._row_to_entry(r) for r in rows])

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> EpisodicEntry:
        """将 SQLite 行转换为 EpisodicEntry"""
        data_raw = row["data"]
        if isinstance(data_raw, str):
            try:
                data = json.loads(data_raw)
            except json.JSONDecodeError:
                data = {}
        else:
            data = data_raw or {}

        return EpisodicEntry(
            id=row["id"],
            chapter_id=row["chapter_id"],
            memory_type=row["memory_type"],
            character_id=row["character_id"],
            data=data,
            confidence=row["confidence"],
            created_at=row["created_at"] or "",
            last_modified=row["last_modified"] or "",
        )

    @staticmethod
    def _filter_entries(
        entries: list[EpisodicEntry],
        query: EpisodicQuery,
    ) -> list[EpisodicEntry]:
        """在内存中过滤条目"""
        results = []
        for e in entries:
            if query.character_id and e.character_id != query.character_id:
                continue
            if query.memory_type and e.memory_type != query.memory_type:
                continue
            if query.min_confidence and e.confidence < query.min_confidence:
                continue
            results.append(e)

        results.sort(key=lambda x: x.last_modified, reverse=True)
        return results
