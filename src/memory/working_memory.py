"""
工作记忆 (Working Memory) — Phase 1

职责：会话级临时记忆存储，会话结束后清空。

契约（来源：02-CONTRACTS.md）：
- 容量：当前会话
- 保留策略：会话结束清空
- 存储：内存（不持久化）
- 写入权限：仅供编排器调用
- 读取：所有引擎可读
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class MemoryWrite:
    """记忆写入请求（仅供编排器调用）

    契约（来源：02-CONTRACTS.md §全局记忆系统）：
    - source_engine: 来源引擎标识
    - target_tier: 目标层级（"working" | "episodic" | "permanent"）
    - memory_type: 类型（"pad_state" | "behavior_log" | "world_event" | "plot_event"）
    - confidence: 置信度标签 0.0 – 1.0
    """

    source_engine: str
    target_tier: str
    memory_type: str
    data: dict = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryQuery:
    """记忆读取请求（所有引擎可读）

    契约（来源：02-CONTRACTS.md §全局记忆系统）：
    - tier: 查询层级
    - 可选过滤: character_id, chapter_range, time_range, memory_type
    """

    tier: str = "all"
    character_id: Optional[str] = None
    chapter_range: Optional[tuple[str, str]] = None
    time_range: Optional[tuple[datetime, datetime]] = None
    memory_type: Optional[str] = None
    top_k: int = 10


@dataclass
class MemoryEntry:
    """单条记忆记录"""

    key: str
    data: dict
    source_engine: str
    memory_type: str
    confidence: float
    last_modified: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# 工作记忆实现
# ---------------------------------------------------------------------------

class WorkingMemory:
    """工作记忆 — Phase 1

    会话级临时存储，基于 dict 实现。
    会话结束后数据自动清空（不持久化）。
    """

    def __init__(self) -> None:
        """初始化空的工作记忆"""
        self._store: dict[str, MemoryEntry] = {}

    def write(self, entry: MemoryWrite) -> None:
        """写入记忆条目

        Args:
            entry: 记忆写入请求
        """
        # 生成唯一键
        key = self._generate_key(entry)

        # 创建记忆条目
        memory_entry = MemoryEntry(
            key=key,
            data=entry.data,
            source_engine=entry.source_engine,
            memory_type=entry.memory_type,
            confidence=entry.confidence,
            last_modified=entry.timestamp,
        )

        # 写入存储
        self._store[key] = memory_entry

    def read(self, query: MemoryQuery) -> list[MemoryEntry]:
        """读取记忆条目

        Args:
            query: 记忆查询参数

        Returns:
            匹配的记忆条目列表，按 last_modified 降序排列
        """
        results = []

        for entry in self._store.values():
            # 过滤层级
            if query.tier != "all":
                # 工作记忆只有 working 层级
                if query.tier != "working":
                    continue

            # 过滤角色
            if query.character_id:
                entry_char_id = entry.data.get("character_id")
                if entry_char_id != query.character_id:
                    continue

            # 过滤记忆类型
            if query.memory_type:
                if entry.memory_type != query.memory_type:
                    continue

            # 过滤时间范围
            if query.time_range:
                start, end = query.time_range
                if not (start <= entry.last_modified <= end):
                    continue

            results.append(entry)

        # 按时间降序排序
        results.sort(key=lambda e: e.last_modified, reverse=True)

        # 限制返回数量
        return results[:query.top_k]

    def clear(self) -> None:
        """清空当前工作记忆"""
        self._store.clear()

    def size(self) -> int:
        """返回当前记忆条目数"""
        return len(self._store)

    def _generate_key(self, entry: MemoryWrite) -> str:
        """生成唯一键

        Args:
            entry: 记忆写入请求

        Returns:
            唯一键字符串
        """
        # 使用时间戳和来源引擎生成键
        timestamp = entry.timestamp.strftime("%Y%m%d%H%M%S%f")
        return f"{entry.source_engine}_{entry.memory_type}_{timestamp}"
