"""
静态语料标注优化回路 (Refiner) — Phase 1 Item 1

职责：当 LLM 分析产生高置信度结果（>0.7）且命中静态语料切片时，
将 LLM 的情感标注/行为标签/PAD 坐标以追加模式写回静态切片的 metadata。

设计原则：
- 追加不覆盖：人类标注的 metadata 不会被删除，仅追加新增信息
- 高门槛：只在 confidence > 0.7 时才触发反哺
- 可追溯：每次反哺记录来源分析 ID
- 不影响主流程：反哺失败静默跳过
"""
from __future__ import annotations

import json
import os
import uuid
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 情感映射表（PAD 坐标 → 情感标签）
# ---------------------------------------------------------------------------

PAD_EMOTION_MAP = [
    # (emotion_label, p_min, p_max, a_min, a_max, d_min, d_max)
    ("快乐",   0.3, 1.0,  0.0, 1.0,  0.0, 1.0),
    ("兴奋",   0.5, 1.0,  0.5, 1.0,  0.0, 1.0),
    ("放松",   0.3, 1.0, -1.0, 0.0,  0.0, 1.0),
    ("忧郁",  -1.0, -0.3, -1.0, 0.0, -1.0, 0.0),
    ("焦虑",  -1.0, -0.3,  0.0, 1.0, -1.0, 0.0),
    ("愤怒",  -1.0, -0.3,  0.5, 1.0,  0.0, 1.0),
    ("恐惧",  -1.0, -0.3,  0.5, 1.0, -1.0, 0.0),
    ("悲伤",  -1.0, -0.3, -1.0, 0.0, -1.0, 0.0),
    ("平静",   0.0, 0.5, -0.5, 0.0,  0.0, 0.5),
    ("轻蔑",  -0.5, 0.0, -0.5, 0.5,  0.5, 1.0),
    ("惊讶",   0.0, 0.5,  0.5, 1.0, -0.5, 0.0),
    ("厌恶",  -1.0, -0.3, -0.5, 0.5,  0.0, 0.5),
]


def _pad_to_emotion(pleasure: float, arousal: float, dominance: float) -> str:
    """将 PAD 坐标映射为情感标签"""
    best_label = "中性"
    best_score = -999.0
    for label, p_min, p_max, a_min, a_max, d_min, d_max in PAD_EMOTION_MAP:
        if p_min <= pleasure <= p_max and a_min <= arousal <= a_max and d_min <= dominance <= d_max:
            # 计算到区域中心的距离作为匹配分数
            pc = (p_min + p_max) / 2
            ac = (a_min + a_max) / 2
            dc = (d_min + d_max) / 2
            dist = ((pleasure - pc) ** 2 + (arousal - ac) ** 2 + (dominance - dc) ** 2) ** 0.5
            score = -dist  # 越近越好
            if score > best_score:
                best_score = score
                best_label = label
    return best_label


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class RefinementResult:
    """单次反哺结果"""
    slice_id: str
    updated_fields: list[str] = field(default_factory=list)
    previous_emotion: str = ""
    new_emotion: str = ""
    added_tags: list[str] = field(default_factory=list)
    pad_appended: bool = False


# ---------------------------------------------------------------------------
# Refiner 实现
# ---------------------------------------------------------------------------

class Refiner:
    """静态语料标注优化器

    当 LLM 分析高置信度命中静态切片时，将分析结果反哺到切片 metadata。
    """

    # 触发反哺的最低置信度阈值
    MIN_CONFIDENCE = 0.7

    def __init__(self, slice_manager: Any = None) -> None:
        """初始化

        Args:
            slice_manager: SliceManager 实例，用于读取和更新切片
        """
        self._slice_manager = slice_manager
        self._refinement_count = 0
        self._recent_refinements: list[RefinementResult] = []

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def refine(
        self,
        engine_results: dict[str, Any],
        scene_text: str = "",
        character_id: str = "",
    ) -> Optional[RefinementResult]:
        """尝试反哺静态切片

        从引擎结果中提取信息，判断是否满足反哺条件，
        若满足则更新对应静态切片的 metadata。

        Args:
            engine_results: 引擎结果字典（含 character_engine 和 world_engine）
            scene_text: 分析场景文本（未使用，保留以备将来扩展）
            character_id: 角色 ID（未使用，保留以备将来扩展）

        Returns:
            RefinementResult 或 None（不满足条件时）
        """
        if not self._slice_manager:
            return None

        try:
            # 1. 提取角色引擎结果
            cr = engine_results.get("character_engine", {})
            if not cr:
                return None

            # 2. 检查置信度是否达标
            confidence = cr.get("confidence", 0)
            if confidence < self.MIN_CONFIDENCE:
                return None

            # 3. 提取被引用的静态切片 ID
            static_slice_ids = self._extract_static_slice_ids(cr)
            if not static_slice_ids:
                return None

            # 4. 为每个命中的静态切片进行反哺（取第一个最佳匹配）
            slice_id = static_slice_ids[0]
            updates = self._build_updates(cr, confidence)

            if not updates:
                return None

            # 5. 执行反哺
            success = self._slice_manager.update_slice_metadata(slice_id, updates)

            if success:
                result = self._make_result(slice_id, updates)
                self._refinement_count += 1
                self._recent_refinements.append(result)
                # 仅保留最近 20 条
                if len(self._recent_refinements) > 20:
                    self._recent_refinements = self._recent_refinements[-20:]
                return result

        except Exception:
            pass  # 反哺失败不影响主流程

        return None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _extract_static_slice_ids(self, character_result: dict) -> list[str]:
        """从角色引擎结果中提取被引用的静态切片 ID

        静态切片 ID 特征：不含 'enr_' 前缀（与 Enricher 的扩充切片区分）
        """
        evidence = character_result.get(
            "behavior_prediction", {}
        ).get("supporting_evidence", [])

        static_ids = []
        for item in evidence:
            if isinstance(item, str) and not item.startswith("enr_"):
                static_ids.append(item)
        return static_ids

    def _build_updates(
        self, character_result: dict, confidence: float
    ) -> dict:
        """构建 metadata 更新字典

        Args:
            character_result: 角色引擎结果
            confidence: 分析置信度

        Returns:
            updates dict（可能为空）
        """
        updates: dict[str, Any] = {}

        # PAD 数据 → emotion + pad_annotations
        pad_state = character_result.get("pad_state")
        if pad_state and isinstance(pad_state, dict):
            p = float(pad_state.get("pleasure", 0))
            a = float(pad_state.get("arousal", 0))
            d = float(pad_state.get("dominance", 0))

            # 仅当 PAD 值不全为 0 时才反哺（排除默认值）
            if not (p == 0 and a == 0 and d == 0):
                emotion = _pad_to_emotion(p, a, d)
                if emotion and emotion != "中性":
                    updates["emotion"] = emotion

                analysis_id = f"an-{uuid.uuid4().hex[:8]}"
                pad_annotation = {
                    "pleasure": round(p, 3),
                    "arousal": round(a, 3),
                    "dominance": round(d, 3),
                    "confidence": round(confidence, 3),
                    "source_analysis_id": analysis_id,
                }
                updates["pad_annotations"] = [pad_annotation]

        # 行为预测 → tags
        behavior = character_result.get("behavior_prediction", {})
        predicted_action = behavior.get("predicted_action", "")
        if predicted_action:
            updates["tags"] = [predicted_action]

        # 隐式触发 → 追加 tags
        triggers = character_result.get("implicit_triggers", [])
        if isinstance(triggers, list):
            updates.setdefault("tags", [])
            updates["tags"].extend(triggers)

        return updates

    def _make_result(
        self, slice_id: str, updates: dict
    ) -> RefinementResult:
        """从 updates dict 构造 RefinementResult"""
        return RefinementResult(
            slice_id=slice_id,
            updated_fields=list(updates.keys()),
            new_emotion=updates.get("emotion", ""),
            added_tags=updates.get("tags", []),
            pad_appended="pad_annotations" in updates,
        )

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    @property
    def refinement_count(self) -> int:
        """总反哺次数"""
        return self._refinement_count

    @property
    def recent_refinements(self) -> list[dict]:
        """最近的反哺记录（用于 API 查询）"""
        return [
            {
                "slice_id": r.slice_id,
                "updated_fields": r.updated_fields,
                "previous_emotion": r.previous_emotion,
                "new_emotion": r.new_emotion,
                "added_tags": r.added_tags,
                "pad_appended": r.pad_appended,
            }
            for r in self._recent_refinements
        ]
