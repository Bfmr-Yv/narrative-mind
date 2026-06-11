"""
Narrative Mind v3.1 — Memory System Package

三层模型：
- 工作记忆 (Working Memory): 会话级，内存存储 — Phase 1
- 情节记忆 (Episodic Memory): 章节级，SQLite — Phase 2
- 永久记忆 (Permanent Memory): 跨书级，SQLite — Phase 2

契约（来源：02-CONTRACTS.md）：
- 只有编排器有写入权限
- 读取无限制，返回数据必须带 last_modified 时间戳
- 工作记忆不持久化
"""

from .working_memory import WorkingMemory, MemoryWrite, MemoryQuery, MemoryEntry
from .episodic_memory import (
    EpisodicMemory,
    EpisodicEntry,
    EpisodicQuery,
    EpisodicStats,
)
from .permanent_memory import (
    PermanentMemory,
    AuthorFingerprint,
    CharacterArchetype,
    WorldRulePattern,
    PermanentQuery,
)

__all__ = [
    # Working
    "WorkingMemory", "MemoryWrite", "MemoryQuery", "MemoryEntry",
    # Episodic
    "EpisodicMemory", "EpisodicEntry", "EpisodicQuery", "EpisodicStats",
    # Permanent
    "PermanentMemory", "AuthorFingerprint", "CharacterArchetype",
    "WorldRulePattern", "PermanentQuery",
]
