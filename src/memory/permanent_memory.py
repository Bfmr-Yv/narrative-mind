"""
永久记忆 (Permanent Memory) — Phase 2

职责：跨作品持久化存储，保存作者指纹、角色原型、世界规则模式。
Phase 2 精简版：SQLite 结构化存储，LanceDB 向量存储留待 Phase 3。

契约（来源：02-CONTRACTS.md, 05-MEMORY-SYSTEM.md）：
- 只有编排器有写入权限（Phase 2+）
- 所有引擎可读
- 支持主动遗忘（30 天未访问自动归档）
- 返回数据必须带 last_modified 时间戳
"""

from __future__ import annotations

import json
import os
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
class AuthorFingerprint:
    """作者风格指纹"""

    # 风格指标（来源：文辞引擎）
    avg_sentence_length: float = 0.0
    dialogue_ratio: float = 0.0
    vocabulary_richness: float = 0.0
    register_level: str = "neutral"
    rhetoric_density: float = 0.0

    # 统计信息
    total_chapters_analyzed: int = 0
    last_updated: str = ""


@dataclass
class CharacterArchetype:
    """角色原型"""

    archetype_id: str = ""
    label: str = ""
    pad_baseline: dict = field(default_factory=dict)  # 典型 PAD 坐标
    behavior_patterns: list[str] = field(default_factory=list)
    typical_roles: list[str] = field(default_factory=list)
    appearances_across_works: int = 0
    last_seen: str = ""


@dataclass
class WorldRulePattern:
    """世界规则模式"""

    pattern_id: str = ""
    rule_category: str = ""  # power_system | spatial | social | economy
    pattern_description: str = ""
    examples: list[str] = field(default_factory=list)
    usage_count: int = 0
    last_used: str = ""


@dataclass
class PermanentQuery:
    """永久记忆查询"""

    category: Optional[str] = None  # fingerprint | archetype | world_rule
    archetype_id: Optional[str] = None
    pattern_id: Optional[str] = None
    min_usage_count: int = 0
    top_k: int = 10


# ---------------------------------------------------------------------------
# 永久记忆实现
# ---------------------------------------------------------------------------

class PermanentMemory:
    """永久记忆 — Phase 2

    跨作品持久化存储。
    Phase 2 精简版：SQLite + JSON，不含向量检索。
    Phase 3 升级：LanceDB 向量索引 + 多级摘要。
    """

    def __init__(self, db_path: str = "projects/memory/permanent.db") -> None:
        """初始化永久记忆

        Args:
            db_path: SQLite 数据库路径
        """
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 表"""
        with sqlite3.connect(self._db_path) as conn:
            # 作者指纹
            conn.execute("""
                CREATE TABLE IF NOT EXISTS author_fingerprint (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    avg_sentence_length REAL DEFAULT 0,
                    dialogue_ratio REAL DEFAULT 0,
                    vocabulary_richness REAL DEFAULT 0,
                    register_level TEXT DEFAULT 'neutral',
                    rhetoric_density REAL DEFAULT 0,
                    total_chapters_analyzed INTEGER DEFAULT 0,
                    last_updated TEXT DEFAULT (datetime('now'))
                )
            """)
            # 确保基线行存在
            conn.execute("""
                INSERT OR IGNORE INTO author_fingerprint (id) VALUES (1)
            """)

            # 角色原型库
            conn.execute("""
                CREATE TABLE IF NOT EXISTS character_archetypes (
                    archetype_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL DEFAULT '',
                    pad_baseline TEXT DEFAULT '{}',
                    behavior_patterns TEXT DEFAULT '[]',
                    typical_roles TEXT DEFAULT '[]',
                    appearances_across_works INTEGER DEFAULT 0,
                    last_seen TEXT DEFAULT (datetime('now'))
                )
            """)

            # 世界规则模式
            conn.execute("""
                CREATE TABLE IF NOT EXISTS world_rule_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    rule_category TEXT NOT NULL DEFAULT '',
                    pattern_description TEXT NOT NULL DEFAULT '',
                    examples TEXT DEFAULT '[]',
                    usage_count INTEGER DEFAULT 0,
                    last_used TEXT DEFAULT (datetime('now'))
                )
            """)

            # 跨作品意象库
            conn.execute("""
                CREATE TABLE IF NOT EXISTS imagery_catalog (
                    image_id TEXT PRIMARY KEY,
                    image_keyword TEXT NOT NULL,
                    associated_themes TEXT DEFAULT '[]',
                    source_works TEXT DEFAULT '[]',
                    usage_count INTEGER DEFAULT 0,
                    last_used TEXT DEFAULT (datetime('now'))
                )
            """)

            # 访问日志（用于主动遗忘）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_log (
                    entry_id TEXT PRIMARY KEY,
                    table_name TEXT NOT NULL,
                    accessed_at TEXT DEFAULT (datetime('now'))
                )
            """)

            conn.commit()

    # ------------------------------------------------------------------
    # 作者指纹
    # ------------------------------------------------------------------

    def update_fingerprint(self, metrics: dict) -> AuthorFingerprint:
        """更新作者风格指纹

        使用移动平均缓慢更新，避免单章异常值干扰基线。

        Args:
            metrics: 风格指标字典（来自 ProseEngine）

        Returns:
            更新后的 AuthorFingerprint
        """
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        with sqlite3.connect(self._db_path) as conn:
            # 读取当前值
            row = conn.execute(
                "SELECT * FROM author_fingerprint WHERE id = 1"
            ).fetchone()

            old_chapters = row[6] if row else 0

            # 首次写入直接赋值，后续使用移动平均
            if old_chapters == 0:
                alpha = 1.0
            else:
                alpha = 0.2  # 新数据权重

            new_values = {
                "avg_sentence_length": (
                    (row[1] or 0) * (1 - alpha) + metrics.get("avg_sentence_length", 0) * alpha
                ),
                "dialogue_ratio": (
                    (row[2] or 0) * (1 - alpha) + metrics.get("dialogue_ratio", 0) * alpha
                ),
                "vocabulary_richness": (
                    (row[3] or 0) * (1 - alpha) + metrics.get("vocabulary_richness", 0) * alpha
                ),
                "register_level": metrics.get("register_level", row[4] or "neutral"),
                "rhetoric_density": (
                    (row[5] or 0) * (1 - alpha) + metrics.get("rhetoric_density", 0) * alpha
                ),
                "total_chapters_analyzed": old_chapters + 1,
                "last_updated": now,
            }

            conn.execute(
                """UPDATE author_fingerprint SET
                   avg_sentence_length = ?, dialogue_ratio = ?, vocabulary_richness = ?,
                   register_level = ?, rhetoric_density = ?,
                   total_chapters_analyzed = ?, last_updated = ? WHERE id = 1""",
                tuple(new_values.values()),
            )
            conn.commit()

            self._log_access("author_fingerprint", "fingerprint_v1")

            return AuthorFingerprint(**new_values)

    def get_fingerprint(self) -> Optional[AuthorFingerprint]:
        """获取作者风格指纹

        Returns:
            AuthorFingerprint 实例，未建立时返回 None
        """
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM author_fingerprint WHERE id = 1"
            ).fetchone()

        if not row or row[6] == 0:  # no chapters analyzed
            return None

        self._log_access("author_fingerprint", "fingerprint_v1")

        return AuthorFingerprint(
            avg_sentence_length=row[1] or 0.0,
            dialogue_ratio=row[2] or 0.0,
            vocabulary_richness=row[3] or 0.0,
            register_level=row[4] or "neutral",
            rhetoric_density=row[5] or 0.0,
            total_chapters_analyzed=row[6] or 0,
            last_updated=row[7] or "",
        )

    # ------------------------------------------------------------------
    # 角色原型
    # ------------------------------------------------------------------

    def save_archetype(self, archetype: CharacterArchetype) -> str:
        """保存角色原型

        Args:
            archetype: 角色原型

        Returns:
            archetype_id
        """
        if not archetype.archetype_id:
            archetype.archetype_id = str(uuid.uuid4())[:12]

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO character_archetypes
                   (archetype_id, label, pad_baseline, behavior_patterns, typical_roles,
                    appearances_across_works, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    archetype.archetype_id,
                    archetype.label,
                    json.dumps(archetype.pad_baseline, ensure_ascii=False),
                    json.dumps(archetype.behavior_patterns, ensure_ascii=False),
                    json.dumps(archetype.typical_roles, ensure_ascii=False),
                    archetype.appearances_across_works,
                    now,
                ),
            )
            conn.commit()

        self._log_access("character_archetypes", archetype.archetype_id)
        return archetype.archetype_id

    def get_archetype(self, archetype_id: str) -> Optional[CharacterArchetype]:
        """获取角色原型

        Args:
            archetype_id: 原型 ID

        Returns:
            CharacterArchetype，未找到返回 None
        """
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM character_archetypes WHERE archetype_id = ?",
                (archetype_id,),
            ).fetchone()

        if not row:
            return None

        self._log_access("character_archetypes", archetype_id)

        return CharacterArchetype(
            archetype_id=row[0],
            label=row[1] or "",
            pad_baseline=json.loads(row[2]) if row[2] else {},
            behavior_patterns=json.loads(row[3]) if row[3] else [],
            typical_roles=json.loads(row[4]) if row[4] else [],
            appearances_across_works=row[5] or 0,
            last_seen=row[6] or "",
        )

    def list_archetypes(
        self,
        min_appearances: int = 0,
        top_k: int = 20,
    ) -> list[CharacterArchetype]:
        """列出角色原型

        Args:
            min_appearances: 最小出现次数
            top_k: 最大返回数

        Returns:
            原型列表
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """SELECT * FROM character_archetypes
                   WHERE appearances_across_works >= ?
                   ORDER BY appearances_across_works DESC LIMIT ?""",
                (min_appearances, top_k),
            )
            rows = cursor.fetchall()

        return [
            CharacterArchetype(
                archetype_id=r[0], label=r[1] or "",
                pad_baseline=json.loads(r[2]) if r[2] else {},
                behavior_patterns=json.loads(r[3]) if r[3] else [],
                typical_roles=json.loads(r[4]) if r[4] else [],
                appearances_across_works=r[5] or 0,
                last_seen=r[6] or "",
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # 世界规则模式
    # ------------------------------------------------------------------

    def save_rule_pattern(self, pattern: WorldRulePattern) -> str:
        """保存世界规则模式

        Args:
            pattern: 规则模式

        Returns:
            pattern_id
        """
        if not pattern.pattern_id:
            pattern.pattern_id = str(uuid.uuid4())[:12]

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO world_rule_patterns
                   (pattern_id, rule_category, pattern_description, examples, usage_count, last_used)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    pattern.pattern_id,
                    pattern.rule_category,
                    pattern.pattern_description,
                    json.dumps(pattern.examples, ensure_ascii=False),
                    pattern.usage_count,
                    now,
                ),
            )
            conn.commit()

        self._log_access("world_rule_patterns", pattern.pattern_id)
        return pattern.pattern_id

    def find_similar_rules(
        self,
        rule_category: Optional[str] = None,
        keyword: str = "",
        top_k: int = 10,
    ) -> list[WorldRulePattern]:
        """搜索相似规则模式

        Args:
            rule_category: 规则类别过滤
            keyword: 关键词搜索（pattern_description LIKE）
            top_k: 最大返回数

        Returns:
            匹配的规则模式列表
        """
        sql = "SELECT * FROM world_rule_patterns WHERE 1=1"
        params: list = []

        if rule_category:
            sql += " AND rule_category = ?"
            params.append(rule_category)
        if keyword:
            sql += " AND pattern_description LIKE ?"
            params.append(f"%{keyword}%")

        sql += " ORDER BY usage_count DESC LIMIT ?"
        params.append(top_k)

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

        return [
            WorldRulePattern(
                pattern_id=r[0], rule_category=r[1] or "",
                pattern_description=r[2] or "",
                examples=json.loads(r[3]) if r[3] else [],
                usage_count=r[4] or 0,
                last_used=r[5] or "",
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # 维护操作
    # ------------------------------------------------------------------

    def prune_stale_data(self, days_threshold: int = 30) -> int:
        """主动遗忘：清理低频访问数据

        Args:
            days_threshold: 超过此天数未访问的数据将被清理

        Returns:
            清理的条目数
        """
        cutoff = datetime.now().timestamp() - days_threshold * 86400
        cutoff_str = datetime.fromtimestamp(cutoff).strftime("%Y-%m-%dT%H:%M:%S")
        total_removed = 0

        with sqlite3.connect(self._db_path) as conn:
            # 查找过期访问条目
            stale = conn.execute(
                "SELECT entry_id, table_name FROM access_log WHERE accessed_at < ?",
                (cutoff_str,),
            ).fetchall()

            for entry_id, table_name in stale:
                if table_name == "character_archetypes":
                    conn.execute(
                        "UPDATE character_archetypes SET appearances_across_works = MAX(0, appearances_across_works - 1) WHERE archetype_id = ?",
                        (entry_id,),
                    )
                elif table_name == "world_rule_patterns":
                    conn.execute(
                        "UPDATE world_rule_patterns SET usage_count = MAX(0, usage_count - 1) WHERE pattern_id = ?",
                        (entry_id,),
                    )

            # 清理访问日志
            conn.execute("DELETE FROM access_log WHERE accessed_at < ?", (cutoff_str,))
            conn.commit()
            total_removed = len(stale)

        return total_removed

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计字典
        """
        with sqlite3.connect(self._db_path) as conn:
            archetypes = conn.execute(
                "SELECT COUNT(*) FROM character_archetypes"
            ).fetchone()[0]
            rules = conn.execute(
                "SELECT COUNT(*) FROM world_rule_patterns"
            ).fetchone()[0]
            images = conn.execute(
                "SELECT COUNT(*) FROM imagery_catalog"
            ).fetchone()[0]

        import os
        db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0

        return {
            "archetypes": archetypes,
            "rule_patterns": rules,
            "imagery_entries": images,
            "db_size_bytes": db_size,
        }

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _log_access(self, table_name: str, entry_id: str) -> None:
        """记录访问（用于主动遗忘）"""
        try:
            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO access_log (entry_id, table_name, accessed_at)
                       VALUES (?, ?, ?)""",
                    (entry_id, table_name, now),
                )
                conn.commit()
        except Exception:
            pass  # 访问日志失败不阻塞主流程
