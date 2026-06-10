"""
语料自扩充器 (Enricher) — Phase 1 M6

职责：将 LLM 分析结果转化为可检索的扩充切片，存入动态索引。
每个项目独立存储，不污染公共语料库。

回路逻辑：
1. LLM 分析产生高置信度 (>0.6) 结果
2. Enricher 将场景文本 + LLM 分析融合为扩充切片
3. 切片写入 projects/<project_id>/enriched/
4. Retriever 在下一次检索时搜索静态 + 动态双索引
"""

from __future__ import annotations

import json
import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .slice_manager import CorpusSlice, SliceMetadata


# ---------------------------------------------------------------------------
# 扩充切片数据模型
# ---------------------------------------------------------------------------

@dataclass
class EnrichedSliceRecord:
    """扩充切片的持久化记录"""
    slice_id: str
    source: str          # "enriched"
    project_id: str
    scene_text: str      # 用户原始场景文本（截取 500 字）
    analysis_text: str   # LLM 分析文本（融合入切片正文）
    pad: dict[str, float]  # PAD 情感坐标
    behavior: str        # 行为预测
    confidence: float
    characters: list[str] = field(default_factory=list)
    scene_type: str = "unknown"
    emotion: str = "neutral"
    tags: list[str] = field(default_factory=list)
    created: str = ""    # ISO timestamp


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _pad_to_emotion_label(pad_state: Any) -> str:
    """将 PAD 状态映射为情感标签

    Args:
        pad_state: 包含 pleasure/arousal/dominance 的对象

    Returns:
        情感标签字符串
    """
    p = getattr(pad_state, "pleasure", 0.0)
    a = getattr(pad_state, "arousal", 0.0)
    d = getattr(pad_state, "dominance", 0.0)

    # 基于 PAD 空间的简单分类
    if p > 0.5 and a > 0.3:
        return "joyful"
    elif p > 0.3 and a > 0.5:
        return "lively"
    elif p > 0.3 and a < -0.3:
        return "reflective"
    elif p < -0.5 and a > 0.3:
        return "tense"
    elif p < -0.3 and a < -0.3:
        return "melancholic"
    elif p < -0.5 and a > 0.5 and d > 0.3:
        return "angry"
    elif p < -0.3 and d < -0.3:
        return "afraid"
    elif d > 0.5:
        return "triumphant"
    elif d < -0.5:
        return "confused"
    else:
        return "neutral"


def _infer_scene_type_from_behavior(behavior_text: str) -> str:
    """从行为描述推断场景类型

    Args:
        behavior_text: 行为预测文本

    Returns:
        场景类型
    """
    dialogue_keywords = {"说", "道", "问", "答", "谈", "讲", "聊", "叫", "喊"}
    action_keywords = {"走", "跑", "跳", "打", "拿", "放", "推", "拉", "抱", "踢"}

    for kw in dialogue_keywords:
        if kw in behavior_text:
            return "dialogue"
    for kw in action_keywords:
        if kw in behavior_text:
            return "action"
    return "narration"


def _extract_enriched_tags(
    character_result: Any,
    world_result: Optional[Any] = None,
) -> list[str]:
    """从分析结果中提取扩充标签

    Args:
        character_result: 角色引擎结果
        world_result: 世界引擎结果（可选）

    Returns:
        标签列表
    """
    tags: list[str] = []

    # 从角色引擎提取
    triggers = getattr(character_result, "implicit_triggers", []) or []
    for t in triggers:
        if isinstance(t, str) and not t.startswith("emotion:") and not t.startswith("scene:"):
            tags.append(t)

    # 从行为预测提取关键词
    behavior = getattr(character_result, "behavior_prediction", None)
    if behavior:
        action = getattr(behavior, "predicted_action", "") or ""
        # 提取 2-4 字的关键片段作为标签
        if len(action) >= 2:
            tags.append(action[:8])

    return list(set(tags))[:10]  # 去重，最多 10 个标签


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------

class Enricher:
    """语料自扩充器

    将 LLM 分析结果转化为可检索的扩充切片。
    每个项目独立存储，质量门控 confidence > 0.6。
    """

    def __init__(
        self,
        project_id: str,
        base_dir: Optional[str] = None,
        quality_threshold: float = 0.6,
        max_dynamic_slices: int = 100,
    ) -> None:
        """初始化扩充器

        Args:
            project_id: 项目 ID
            base_dir: 项目根目录（默认 projects/<project_id>）
            quality_threshold: 质量阈值，低于此值不入库
            max_dynamic_slices: 动态索引最大切片数（防止膨胀）
        """
        self._project_id = project_id
        self._threshold = quality_threshold
        self._max_slices = max_dynamic_slices

        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path("projects") / project_id

        self._enriched_dir = self._base_dir / "enriched"
        self._enriched_dir.mkdir(parents=True, exist_ok=True)

        self._dynamic_slices: dict[str, CorpusSlice] = {}

    def enrich(
        self,
        scene_text: str,
        character_id: str,
        engine_results: dict[str, Any],
        guardian_output: Any,
    ) -> Optional[CorpusSlice]:
        """将一次分析结果转化为扩充切片

        Args:
            scene_text: 用户场景文本
            character_id: 主要角色 ID
            engine_results: 编排器返回的引擎结果 dict
            guardian_output: 守卫输出

        Returns:
            CorpusSlice 如果质量达标，否则 None
        """
        # 1. 质量门控
        char_result = engine_results.get("character_engine")
        if not char_result:
            return None

        confidence = getattr(char_result, "confidence", 0.0)
        if confidence < self._threshold:
            return None

        # 2. 提取数据
        pad_state = getattr(char_result, "pad_state", None)
        behavior = getattr(char_result, "behavior_prediction", None)
        predicted_action = getattr(behavior, "predicted_action", "未知行为") if behavior else "未知行为"
        implicit_triggers = getattr(char_result, "implicit_triggers", []) or []

        # 3. 确定情感标签
        emotion = "neutral"
        if pad_state:
            emotion = _pad_to_emotion_label(pad_state)

        # 4. 确定场景类型
        scene_type = _infer_scene_type_from_behavior(predicted_action)

        # 5. 构建扩充文本（原文 + LLM 分析融合）
        text_snippet = scene_text[:500] if len(scene_text) > 500 else scene_text
        analysis_header = f"\n[行为分析] {predicted_action}"
        if pad_state:
            p = getattr(pad_state, "pleasure", 0.0)
            a = getattr(pad_state, "arousal", 0.0)
            d = getattr(pad_state, "dominance", 0.0)
            analysis_header += f" | PAD({p:.1f},{a:.1f},{d:.1f})"
        enriched_text = text_snippet + analysis_header

        # 6. 提取元数据
        characters = [character_id] + [
            t for t in implicit_triggers
            if isinstance(t, str) and not t.startswith(("emotion:", "scene:"))
        ]

        tags = _extract_enriched_tags(char_result)

        metadata = SliceMetadata(
            characters=list(set(characters))[:8],
            scene_type=scene_type,
            emotion=emotion,
            tags=tags,
        )

        # 7. 创建切片
        slice_id = f"enr_{self._project_id.split('-')[-1][:8]}_{uuid.uuid4().hex[:6]}"
        slice_obj = CorpusSlice(
            slice_id=slice_id,
            source="enriched",
            chapter="",
            text=enriched_text,
            metadata=metadata,
        )

        # 8. 写入动态索引
        self._dynamic_slices[slice_id] = slice_obj

        # 9. 持久化
        self._persist(slice_obj, predicted_action, pad_state, confidence)

        # 10. 容量控制：超出上限时移除最旧的切片
        if len(self._dynamic_slices) > self._max_slices:
            oldest_id = next(iter(self._dynamic_slices))
            del self._dynamic_slices[oldest_id]
            old_file = self._enriched_dir / f"{oldest_id}.json"
            if old_file.exists():
                old_file.unlink()

        return slice_obj

    def get_dynamic_slices(self) -> list[CorpusSlice]:
        """获取所有动态扩充切片，供 Retriever 检索"""
        return list(self._dynamic_slices.values())

    def load_existing(self) -> int:
        """从磁盘加载已有扩充切片

        Returns:
            加载的切片数量
        """
        if not self._enriched_dir.exists():
            return 0

        loaded = 0
        for slice_file in self._enriched_dir.glob("*.json"):
            try:
                data = json.loads(slice_file.read_text(encoding="utf-8"))

                metadata = SliceMetadata(
                    characters=data.get("metadata", {}).get("characters", []),
                    scene_type=data.get("metadata", {}).get("scene_type", "unknown"),
                    emotion=data.get("metadata", {}).get("emotion", "neutral"),
                    tags=data.get("metadata", {}).get("tags", []),
                )

                slice_obj = CorpusSlice(
                    slice_id=data["slice_id"],
                    source=data.get("source", "enriched"),
                    chapter=data.get("chapter", ""),
                    text=data["text"],
                    metadata=metadata,
                )

                self._dynamic_slices[slice_obj.slice_id] = slice_obj
                loaded += 1

            except (json.JSONDecodeError, KeyError):
                continue

        return loaded

    def clear(self) -> int:
        """清空所有动态扩充切片

        Returns:
            清除的切片数量
        """
        count = len(self._dynamic_slices)
        self._dynamic_slices.clear()

        if self._enriched_dir.exists():
            for f in self._enriched_dir.glob("*.json"):
                f.unlink()

        return count

    @property
    def dynamic_slice_count(self) -> int:
        """动态扩充切片数量"""
        return len(self._dynamic_slices)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _persist(
        self,
        slice_obj: CorpusSlice,
        predicted_action: str,
        pad_state: Any,
        confidence: float,
    ) -> None:
        """持久化扩充切片到磁盘"""
        pad_dict = {}
        if pad_state:
            pad_dict = {
                "pleasure": getattr(pad_state, "pleasure", 0.0),
                "arousal": getattr(pad_state, "arousal", 0.0),
                "dominance": getattr(pad_state, "dominance", 0.0),
            }

        data = {
            "slice_id": slice_obj.slice_id,
            "source": slice_obj.source,
            "project_id": self._project_id,
            "chapter": slice_obj.chapter,
            "text": slice_obj.text,
            "metadata": {
                "characters": slice_obj.metadata.characters,
                "scene_type": slice_obj.metadata.scene_type,
                "emotion": slice_obj.metadata.emotion,
                "tags": slice_obj.metadata.tags,
            },
            "analysis": {
                "behavior": predicted_action,
                "pad": pad_dict,
                "confidence": confidence,
            },
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        file_path = self._enriched_dir / f"{slice_obj.slice_id}.json"
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
