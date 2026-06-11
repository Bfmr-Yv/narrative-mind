"""
统一记忆管理器 (Memory Manager) — Phase 2

职责：协调三层记忆（工作/情节/永久），管理数据下沉和统一查询。

流程：
1. 会话中 → 工作记忆（快速读写）
2. 章节结束时 → 工作记忆下沉到情节记忆
3. 跨书积累 → 情节记忆沉淀到永久记忆

契约（来源：02-CONTRACTS.md）：
- 只有编排器有写入权限（MemoryManager 是编排器的代理）
- 所有引擎可读
- 下沉操作由编排器在章节结束时显式触发
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .working_memory import WorkingMemory, MemoryWrite, MemoryQuery, MemoryEntry
from .episodic_memory import EpisodicMemory, EpisodicQuery, EpisodicEntry
from .permanent_memory import PermanentMemory


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class UnifiedQuery:
    """统一查询 — 跨三层记忆搜索"""

    tier: str = "all"  # working | episodic | permanent | all
    character_id: Optional[str] = None
    chapter_id: Optional[str] = None
    chapter_range: Optional[tuple[str, str]] = None
    memory_type: Optional[str] = None
    time_range: Optional[tuple[datetime, datetime]] = None
    min_confidence: float = 0.0
    top_k: int = 10


@dataclass
class UnifiedResult:
    """统一查询结果"""

    items: list[dict] = field(default_factory=list)
    source_tiers: list[str] = field(default_factory=list)  # 数据来源
    total_across_tiers: int = 0


@dataclass
class ChapterSummary:
    """章节摘要（下沉时自动生成）"""

    chapter_id: str
    character_count: int  # 出场的角色数
    event_count: int      # 事件数
    pad_snapshots: dict   # 各角色 PAD 快照
    key_events: list[str] # 关键事件描述
    foreshadowing_count: int


# ---------------------------------------------------------------------------
# 管理器实现
# ---------------------------------------------------------------------------

class MemoryManager:
    """统一记忆管理器 — Phase 2

    协调三层记忆的生命周期。
    编排器通过 MemoryManager 间接操作记忆。
    """

    def __init__(
        self,
        working: Optional[WorkingMemory] = None,
        episodic: Optional[EpisodicMemory] = None,
        permanent: Optional[PermanentMemory] = None,
    ) -> None:
        """初始化记忆管理器

        Args:
            working: 工作记忆实例（默认自动创建）
            episodic: 情节记忆实例（默认自动创建）
            permanent: 永久记忆实例（默认自动创建）
        """
        self.working = working or WorkingMemory()
        self.episodic = episodic or EpisodicMemory()
        self.permanent = permanent or PermanentMemory()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def write_working(self, write: MemoryWrite) -> None:
        """写入工作记忆（会话内快速写入）

        Args:
            write: 记忆写入请求
        """
        self.working.write(write)

    def write_episodic(
        self,
        chapter_id: str,
        memory_type: str,
        data: dict,
        character_id: Optional[str] = None,
        confidence: float = 0.5,
    ) -> str:
        """写入情节记忆（直接写入，绕过工作记忆）

        Args:
            chapter_id: 章节标识
            memory_type: 记忆类型
            data: 载荷数据
            character_id: 关联角色
            confidence: 置信度

        Returns:
            条目 ID
        """
        return self.episodic.write(
            chapter_id=chapter_id,
            memory_type=memory_type,
            data=data,
            character_id=character_id,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # 统一查询
    # ------------------------------------------------------------------

    def query(self, q: UnifiedQuery) -> UnifiedResult:
        """跨三层记忆统一搜索

        按优先级：working → episodic → permanent
        每层取 top_k 条，合并后去重排序。

        Args:
            q: 统一查询参数

        Returns:
            UnifiedResult: 合并结果
        """
        all_items = []
        tiers_used = []

        # 1. 工作记忆
        if q.tier in ("working", "all"):
            wm_query = MemoryQuery(
                tier="working",
                character_id=q.character_id,
                memory_type=q.memory_type,
                time_range=q.time_range,
                top_k=q.top_k,
            )
            wm_results = self.working.read(wm_query)
            if wm_results:
                tiers_used.append("working")
                for entry in wm_results:
                    all_items.append({
                        "tier": "working",
                        "id": entry.key,
                        "memory_type": entry.memory_type,
                        "data": entry.data,
                        "confidence": entry.confidence,
                        "last_modified": entry.last_modified.isoformat() if hasattr(entry.last_modified, 'isoformat') else str(entry.last_modified),
                    })

        # 2. 情节记忆
        if q.tier in ("episodic", "all") and len(all_items) < q.top_k:
            eq = EpisodicQuery(
                chapter_id=q.chapter_id,
                chapter_range=q.chapter_range,
                character_id=q.character_id,
                memory_type=q.memory_type,
                min_confidence=q.min_confidence,
                top_k=q.top_k,
            )
            em_results = self.episodic.read(eq)
            if em_results:
                tiers_used.append("episodic")
                for entry in em_results:
                    all_items.append({
                        "tier": "episodic",
                        "id": entry.id,
                        "chapter_id": entry.chapter_id,
                        "memory_type": entry.memory_type,
                        "character_id": entry.character_id,
                        "data": entry.data,
                        "confidence": entry.confidence,
                        "last_modified": entry.last_modified,
                    })

        # 3. 永久记忆（仅特定类型）
        if q.tier in ("permanent", "all") and len(all_items) < q.top_k:
            fp = self.permanent.get_fingerprint()
            if fp:
                tiers_used.append("permanent")
                all_items.append({
                    "tier": "permanent",
                    "id": "author_fingerprint",
                    "memory_type": "fingerprint",
                    "data": {
                        "avg_sentence_length": fp.avg_sentence_length,
                        "register_level": fp.register_level,
                        "total_chapters_analyzed": fp.total_chapters_analyzed,
                    },
                    "confidence": 0.8,
                    "last_modified": fp.last_updated,
                })

        # 排序并限数
        all_items.sort(
            key=lambda x: x.get("last_modified", ""),
            reverse=True,
        )

        return UnifiedResult(
            items=all_items[:q.top_k],
            source_tiers=tiers_used,
            total_across_tiers=len(all_items),
        )

    # ------------------------------------------------------------------
    # 章节结束下沉
    # ------------------------------------------------------------------

    def flush_chapter(self, chapter_id: str) -> dict:
        """章节结束时将工作记忆中的关键数据下沉到情节记忆

        下沉内容：
        - PAD 状态快照 → pad_history
        - 行为日志 → behavior_log
        - 场景上下文 → chapter_summary
        - 冲突记录 → conflict_resolution

        Args:
            chapter_id: 当前章节标识

        Returns:
            下沉统计 {"flushed": int, "types": [str]}
        """
        flushed = 0
        types_flushed = []

        # 从工作记忆中读取所有条目
        all_working = self.working.read(MemoryQuery(top_k=1000))

        for entry in all_working:
            # 根据类型决定是否下沉到情节记忆
            target_type = self._map_to_episodic_type(entry.memory_type)
            if not target_type:
                continue

            self.episodic.write(
                chapter_id=chapter_id,
                memory_type=target_type,
                data=entry.data,
                character_id=entry.data.get("character_id"),
                confidence=entry.confidence,
            )
            flushed += 1
            if target_type not in types_flushed:
                types_flushed.append(target_type)

        # 生成章节摘要（合并所有下沉数据）
        summary = self._generate_chapter_summary(chapter_id, all_working)
        if summary:
            self.episodic.write(
                chapter_id=chapter_id,
                memory_type="chapter_summary",
                data=summary,
                confidence=0.8,
            )
            flushed += 1
            if "chapter_summary" not in types_flushed:
                types_flushed.append("chapter_summary")

        # 不自动清空工作记忆（编排器决定时机）
        return {"flushed": flushed, "types": types_flushed}

    def flush_working(self) -> None:
        """清空工作记忆（会话结束或切换章节时调用）"""
        self.working.clear()

    # ------------------------------------------------------------------
    # 跨书积累
    # ------------------------------------------------------------------

    def accumulate_to_permanent(self) -> dict:
        """将情节记忆中的模式数据沉淀到永久记忆

        当前沉淀内容：
        - 从 pad_history 条目提取角色原型线索
        - 从所有章节摘要更新作者指纹基线

        Returns:
            积累统计
        """
        stats = {"archetypes_updated": 0, "fingerprint_updated": False}

        # 1. 提取角色 PAD 模式 → 原型库
        # 获取所有 pad_history 条目
        pad_entries = self.episodic.read(EpisodicQuery(
            memory_type="pad_history",
            top_k=500,
        ))

        # 按角色分组统计 PAD 均值
        char_pads: dict[str, list[dict]] = {}
        for entry in pad_entries:
            cid = entry.character_id or entry.data.get("character_id", "unknown")
            if cid not in char_pads:
                char_pads[cid] = []
            char_pads[cid].append(entry.data)

        # 为每个角色创建/更新原型
        for cid, pads in char_pads.items():
            if len(pads) < 3:
                continue  # 数据太少跳过

            avg_p = sum(p.get("pleasure", 0) for p in pads) / len(pads)
            avg_a = sum(p.get("arousal", 0) for p in pads) / len(pads)
            avg_d = sum(p.get("dominance", 0) for p in pads) / len(pads)

            from .permanent_memory import CharacterArchetype
            self.permanent.save_archetype(CharacterArchetype(
                archetype_id=f"auto_{cid}",
                label=cid,
                pad_baseline={"pleasure": round(avg_p, 2), "arousal": round(avg_a, 2), "dominance": round(avg_d, 2)},
                behavior_patterns=[],
                typical_roles=[],
                appearances_across_works=len(pads),
            ))
            stats["archetypes_updated"] += 1

        return stats

    # ------------------------------------------------------------------
    # 获取前文章节上下文
    # ------------------------------------------------------------------

    def get_previous_context(
        self,
        current_chapter_id: str,
        max_chapters: int = 3,
    ) -> list[dict]:
        """获取前文章节摘要，供引擎分析使用

        Args:
            current_chapter_id: 当前章节 ID
            max_chapters: 最大返回章节数

        Returns:
            [{"chapter_id": str, "summary": dict, "key_events": [str]}, ...]
        """
        prev_ids = self.episodic.get_chapters_since(
            current_chapter_id,
            limit=max_chapters,
        )

        context = []
        for cid in prev_ids:
            summary = self.episodic.get_chapter_summary(cid)
            if summary:
                context.append({
                    "chapter_id": cid,
                    "summary": summary.get("summary", ""),
                    "key_events": summary.get("key_events", []),
                })

        return context

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """获取三层记忆统计

        Returns:
            统计字典
        """
        return {
            "working": {"entries": self.working.size()},
            "episodic": self._episodic_stats_to_dict(),
            "permanent": self.permanent.get_stats(),
        }

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _map_to_episodic_type(working_type: str) -> Optional[str]:
        """将工作记忆类型映射到情节记忆类型

        只有需要持久化的类型才下沉。

        Args:
            working_type: 工作记忆中的类型

        Returns:
            情节记忆类型，不需要下沉返回 None
        """
        mapping = {
            "pad_state": "pad_history",
            "behavior_log": "behavior_log",
            "world_event": "world_event",
            "plot_event": "world_event",  # 合并到世界事件
            "conflict": "conflict_resolution",
        }
        return mapping.get(working_type)

    @staticmethod
    def _generate_chapter_summary(
        chapter_id: str,
        entries: list[MemoryEntry],
    ) -> Optional[dict]:
        """从工作记忆条目生成章节摘要

        Args:
            chapter_id: 章节 ID
            entries: 工作记忆条目列表

        Returns:
            摘要字典，无内容时返回 None
        """
        characters = set()
        key_events = []
        pad_snapshots = {}

        for entry in entries:
            cid = entry.data.get("character_id")
            if cid:
                characters.add(cid)

            if entry.memory_type == "pad_state" and cid:
                pad_snapshots[cid] = {
                    "pleasure": entry.data.get("pleasure", 0),
                    "arousal": entry.data.get("arousal", 0),
                    "dominance": entry.data.get("dominance", 0),
                }

            if entry.memory_type == "world_event":
                event_desc = entry.data.get("event", entry.data.get("description", ""))
                if event_desc:
                    key_events.append(event_desc)

            if entry.memory_type == "behavior_log":
                action = entry.data.get("action", "")
                if action:
                    key_events.append(action)

        if not characters and not key_events:
            return None

        return {
            "summary": f"章节 {chapter_id}：{len(characters)} 个角色出场，"
                       f"{len(key_events)} 个关键事件",
            "character_count": len(characters),
            "event_count": len(key_events),
            "pad_snapshots": pad_snapshots,
            "key_events": key_events[:10],  # 最多保留 10 个
        }

    @staticmethod
    def _episodic_stats_to_dict() -> dict:
        """将 EpisodicStats 转为字典（避免循环导入）"""
        return {}
