"""
角色引擎 (Character Engine) — Phase 1

职责：模拟角色在特定情境下的行为反应，基于语料行为模式而非标签推理。

契约（来源：02-CONTRACTS.md）：
- 不直接修改记忆，只返回建议
- 记忆更新由编排器统一写入
- 置信度 < 0.5 时必须返回 needs_human_review=True

依赖：语料锚定层（行为模式检索）、工作记忆（当前 PAD 状态）、世界引擎（设定规则校验）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class PADState:
    """Pleasure-Arousal-Dominance 三维情感坐标

    PAD 情感模型（ADR-001）将情感映射到三维连续空间：
    - Pleasure (愉悦度): 正值为愉悦，负值为不快
    - Arousal (唤醒度): 正值为兴奋/紧张，负值为平静/困倦
    - Dominance (支配度): 正值为掌控/自信，负值为被支配/顺从
    """

    pleasure: float
    arousal: float
    dominance: float

    def to_tuple(self) -> tuple[float, float, float]:
        """返回 (P, A, D) 三元组"""
        return (self.pleasure, self.arousal, self.dominance)


@dataclass
class EmotionContext:
    """情感上下文（由编排器提供，可选）"""

    current_pad: Optional[PADState] = None
    recent_events: list[str] = field(default_factory=list)
    target_emotion: Optional[str] = None


@dataclass
class BehaviorPrediction:
    """行为预测结果"""

    predicted_action: str
    confidence: float  # 0.0 – 1.0
    supporting_evidence: list[str] = field(default_factory=list)
    alternative_actions: list[str] = field(default_factory=list)


@dataclass
class CharacterQuery:
    """角色引擎查询输入"""

    character_id: str
    scene_text: str
    emotion_context: Optional[EmotionContext] = None


@dataclass
class CharacterResponse:
    """角色引擎查询输出"""

    pad_state: PADState
    behavior_prediction: BehaviorPrediction
    implicit_triggers: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_human_review: bool = False


# ---------------------------------------------------------------------------
# 引擎骨架
# ---------------------------------------------------------------------------

class CharacterEngine:
    """角色引擎 — Phase 1 骨架

    模拟角色在特定情境下的行为反应。
    不直接修改记忆，只返回建议。
    """

    def __init__(self) -> None:
        """初始化角色引擎（Phase 1 无持久化资源）"""
        pass

    def analyze(self, query: CharacterQuery) -> CharacterResponse:
        """分析角色在当前场景中的行为反应

        Args:
            query: 包含角色 ID、场景文本和可选情感上下文的查询

        Returns:
            CharacterResponse: PAD 状态、行为预测、隐性记忆触发
        """
        raise NotImplementedError("Phase 1 骨架 — 待实现")

    def get_pad_state(self, character_id: str) -> Optional[PADState]:
        """获取角色当前 PAD 情感状态

        Args:
            character_id: 角色唯一标识

        Returns:
            当前 PAD 状态，若角色不存在则返回 None
        """
        raise NotImplementedError("Phase 1 骨架 — 待实现")
