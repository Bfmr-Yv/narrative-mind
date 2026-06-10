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

from ..corpus_anchor.retriever import Retriever


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

    def distance_to(self, other: PADState) -> float:
        """计算两个情感状态的欧氏距离

        Args:
            other: 另一个 PAD 状态

        Returns:
            欧氏距离（0 到 sqrt(12)）
        """
        return (
            (self.pleasure - other.pleasure) ** 2 +
            (self.arousal - other.arousal) ** 2 +
            (self.dominance - other.dominance) ** 2
        ) ** 0.5

    @classmethod
    def neutral(cls) -> PADState:
        """返回中性情感状态"""
        return cls(pleasure=0.0, arousal=0.0, dominance=0.0)


# 情感关键词到 PAD 值的映射
EMOTION_PAD_MAP: dict[str, PADState] = {
    "joyful": PADState(pleasure=0.8, arousal=0.5, dominance=0.3),
    "happy": PADState(pleasure=0.7, arousal=0.4, dominance=0.3),
    "sad": PADState(pleasure=-0.6, arousal=-0.2, dominance=-0.3),
    "melancholic": PADState(pleasure=-0.5, arousal=-0.3, dominance=-0.2),
    "angry": PADState(pleasure=-0.7, arousal=0.8, dominance=0.5),
    "tense": PADState(pleasure=-0.3, arousal=0.7, dominance=0.0),
    "afraid": PADState(pleasure=-0.6, arousal=0.7, dominance=-0.5),
    "mysterious": PADState(pleasure=0.1, arousal=0.3, dominance=0.0),
    "playful": PADState(pleasure=0.6, arousal=0.4, dominance=0.2),
    "lively": PADState(pleasure=0.5, arousal=0.6, dominance=0.3),
    "neutral": PADState(pleasure=0.0, arousal=0.0, dominance=0.0),
    "awkward": PADState(pleasure=-0.3, arousal=0.2, dominance=-0.3),
    "somber": PADState(pleasure=-0.4, arousal=-0.3, dominance=-0.2),
    "triumphant": PADState(pleasure=0.8, arousal=0.7, dominance=0.6),
    "confused": PADState(pleasure=-0.2, arousal=0.3, dominance=-0.4),
    "mixed": PADState(pleasure=0.0, arousal=0.2, dominance=0.0),
    "reflective": PADState(pleasure=0.0, arousal=-0.2, dominance=0.1),
}


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
# 引擎实现
# ---------------------------------------------------------------------------

class CharacterEngine:
    """角色引擎 — Phase 1

    模拟角色在特定情境下的行为反应。
    基于语料行为模式而非标签推理。
    不直接修改记忆，只返回建议。
    """

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        llm_client: Optional[object] = None,
    ) -> None:
        """初始化角色引擎

        Args:
            retriever: 语料检索器实例
            llm_client: LLM 客户端实例（可选，未配置时使用关键词 fallback）
        """
        self._retriever = retriever
        self._llm = llm_client
        self._character_pad_cache: dict[str, PADState] = {}

    def analyze(self, query: CharacterQuery) -> CharacterResponse:
        """分析角色在当前场景中的行为反应

        Args:
            query: 包含角色 ID、场景文本和可选情感上下文的查询

        Returns:
            CharacterResponse: PAD 状态、行为预测、隐性记忆触发
        """
        # 1. 从语料库检索相似情境下的行为模式
        corpus_hits = []
        if self._retriever and self._retriever.is_indexed:
            try:
                response = self._retriever.retrieve_by_character(
                    query_text=query.scene_text,
                    character_id=query.character_id,
                    category="behavior",
                    top_k=3
                )
                corpus_hits = response.hits
            except Exception:
                pass

        # 2. 计算 PAD 情感状态
        pad_state = self._compute_pad(query, corpus_hits)

        # 3. 预测行为
        behavior_prediction = self._predict_behavior(query, corpus_hits)

        # 4. 提取隐性记忆触发
        implicit_triggers = self._extract_triggers(corpus_hits)

        # 5. 计算整体置信度
        confidence = self._compute_confidence(corpus_hits, behavior_prediction.confidence)

        # 6. 判断是否需要人工审核
        needs_human_review = confidence < 0.5

        return CharacterResponse(
            pad_state=pad_state,
            behavior_prediction=behavior_prediction,
            implicit_triggers=implicit_triggers,
            confidence=confidence,
            needs_human_review=needs_human_review,
        )

    def get_pad_state(self, character_id: str) -> Optional[PADState]:
        """获取角色当前 PAD 情感状态

        Args:
            character_id: 角色唯一标识

        Returns:
            当前 PAD 状态，若角色不存在则返回 None
        """
        return self._character_pad_cache.get(character_id)

    def _compute_pad(
        self,
        query: CharacterQuery,
        corpus_hits: list
    ) -> PADState:
        """计算角色的 PAD 情感状态

        Fallback 链：显式 PAD → LLM 分析 → 缓存 → 语料 emotion → neutral

        Args:
            query: 角色查询
            corpus_hits: 语料命中结果

        Returns:
            PAD 情感状态
        """
        # Tier 0: 显式 PAD（零成本快速路径）
        if query.emotion_context and query.emotion_context.current_pad:
            return query.emotion_context.current_pad

        # Tier 1: 缓存命中
        cached_pad = self._character_pad_cache.get(query.character_id)
        if cached_pad:
            return cached_pad

        # Tier 2: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    PAD_COMPUTE_SYSTEM,
                    format_pad_prompt,
                )

                # 构建语料上下文
                corpus_context = ""
                if corpus_hits:
                    for h in corpus_hits[:2]:
                        corpus_context += f"[{h.slice_id}] {h.text[:200]}...\n"

                # 情感标记
                emotion_note = ""
                if query.emotion_context and query.emotion_context.target_emotion:
                    emotion_note = query.emotion_context.target_emotion

                user_message = format_pad_prompt(
                    character_id=query.character_id,
                    scene_text=query.scene_text,
                    corpus_context=corpus_context,
                    emotion_note=emotion_note,
                )

                result = self._llm.call(
                    system_prompt=PAD_COMPUTE_SYSTEM,
                    user_message=user_message,
                    task_type="pad_compute",
                )

                if result and "pleasure" in result:
                    pad = PADState(
                        pleasure=float(result["pleasure"]),
                        arousal=float(result["arousal"]),
                        dominance=float(result["dominance"]),
                    )
                    self._character_pad_cache[query.character_id] = pad
                    return pad
            except Exception:
                pass  # Fall through to fallback

        # Tier 3: 从语料 metadata 推断
        if corpus_hits:
            first_hit = corpus_hits[0]
            emotion = first_hit.metadata.get("emotion", "neutral")
            if emotion in EMOTION_PAD_MAP:
                pad = EMOTION_PAD_MAP[emotion]
                self._character_pad_cache[query.character_id] = pad
                return pad

        # Tier 4: 中性默认
        return PADState.neutral()

    def _predict_behavior(
        self,
        query: CharacterQuery,
        corpus_hits: list
    ) -> BehaviorPrediction:
        """预测角色行为

        LLM 模式：使用 LLM 进行完整行为预测（主体+备选+置信度）
        Fallback 模式：基于 TF-IDF 相似度和关键词匹配

        Args:
            query: 角色查询
            corpus_hits: 语料命中结果

        Returns:
            行为预测结果
        """
        # --- LLM 路径：直接调用 LLM 获取完整行为预测 ---
        if self._llm and self._llm.is_available and query.scene_text:
            try:
                from ..llm.prompts import (
                    ACTION_INFER_SYSTEM,
                    format_action_prompt,
                )

                # 构建语料上下文（取 top-2 命中切片）
                hit_context = ""
                if corpus_hits:
                    for h in corpus_hits[:2]:
                        hit_context += (
                            f"[{h.slice_id}] 来源={h.metadata.get('source', 'N/A')} "
                            f"情感={h.metadata.get('emotion', 'neutral')} "
                            f"角色={', '.join(h.metadata.get('characters', []))}\n"
                            f"文本: {h.text[:300]}\n\n"
                        )

                scene_type = corpus_hits[0].metadata.get("scene_type", "narration") if corpus_hits else "narration"

                user_message = format_action_prompt(
                    scene_text=query.scene_text,
                    hit_context=hit_context or "无可用语料参考",
                    scene_type=scene_type,
                    character_id=query.character_id,
                )

                result = self._llm.call(
                    system_prompt=ACTION_INFER_SYSTEM,
                    user_message=user_message,
                    task_type="action_infer",
                )

                if result and "predicted_action" in result:
                    predicted_action = result.get("predicted_action", "未知行为")
                    alternative_actions = result.get("alternative_actions", [])
                    llm_confidence = float(result.get("confidence", 0.7))

                    # 提取支持证据
                    supporting_evidence = []
                    if result.get("rationale"):
                        supporting_evidence.append(f"[LLM] {result['rationale']}")
                    if corpus_hits:
                        supporting_evidence.append(
                            f"[{corpus_hits[0].slice_id}] {corpus_hits[0].text[:50]}..."
                        )

                    return BehaviorPrediction(
                        predicted_action=predicted_action,
                        confidence=min(llm_confidence, 1.0),
                        supporting_evidence=supporting_evidence,
                        alternative_actions=alternative_actions,
                    )
            except Exception:
                pass  # Fall through to fallback

        # --- Fallback: TF-IDF + 关键词匹配 ---
        if not corpus_hits:
            return BehaviorPrediction(
                predicted_action="unknown",
                confidence=0.0,
                supporting_evidence=[],
                alternative_actions=[],
            )

        primary_hit = corpus_hits[0]
        scene_type = primary_hit.metadata.get("scene_type", "narration")
        predicted_action = self._infer_action(scene_type, primary_hit, query.scene_text)

        supporting_evidence = [
            f"[{hit.slice_id}] {hit.text[:50]}..."
            for hit in corpus_hits[:2]
        ]

        alternative_actions = []
        for hit in corpus_hits[1:3]:
            alt_action = self._infer_action(
                hit.metadata.get("scene_type", "narration"),
                hit,
                query.scene_text,
            )
            if alt_action != predicted_action:
                alternative_actions.append(alt_action)

        confidence = min(primary_hit.similarity * 2, 1.0)

        return BehaviorPrediction(
            predicted_action=predicted_action,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            alternative_actions=alternative_actions,
        )

    def _infer_action(self, scene_type: str, hit, scene_text: str = "") -> str:
        """从场景类型和语料命中推断行为

        Fallback 链：LLM 分析 → 关键词匹配

        Args:
            scene_type: 场景类型
            hit: 语料命中结果
            scene_text: 当前场景文本（LLM 模式需要）

        Returns:
            推断的行为描述
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available and scene_text:
            try:
                from ..llm.prompts import (
                    ACTION_INFER_SYSTEM,
                    format_action_prompt,
                )

                hit_context = f"[{hit.slice_id} | {scene_type}] 文本: {hit.text[:300]}\n"
                hit_context += f"来源: {hit.metadata.get('source', 'N/A')}\n"
                hit_context += f"情感: {hit.metadata.get('emotion', 'neutral')}\n"
                hit_context += f"角色: {', '.join(hit.metadata.get('characters', []))}"

                user_message = format_action_prompt(
                    scene_text=scene_text,
                    hit_context=hit_context,
                    scene_type=scene_type,
                )

                result = self._llm.call(
                    system_prompt=ACTION_INFER_SYSTEM,
                    user_message=user_message,
                    task_type="action_infer",
                )

                if result and "predicted_action" in result:
                    return result["predicted_action"]
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 关键词匹配 fallback
        action_map = {
            "dialogue": "对话交流",
            "narration": "叙述描述",
            "action": "行动执行",
            "description": "场景描写",
        }

        base_action = action_map.get(scene_type, "未知行为")

        # 尝试从文本中提取更具体的行为
        text = hit.text[:100]
        if "笑" in text:
            return "微笑/欢笑"
        elif "哭" in text or "泪" in text:
            return "哭泣/流泪"
        elif "怒" in text or "骂" in text:
            return "发怒/责骂"
        elif "走" in text or "行" in text:
            return "行走/移动"
        elif "说" in text or "道" in text:
            return "说话/交谈"

        return base_action

    def _extract_triggers(self, corpus_hits: list) -> list[str]:
        """提取隐性记忆触发

        Args:
            corpus_hits: 语料命中结果

        Returns:
            触发标签列表
        """
        triggers = set()

        for hit in corpus_hits:
            # 提取角色
            characters = hit.metadata.get("characters", [])
            triggers.update(characters)

            # 提取情感
            emotion = hit.metadata.get("emotion", "")
            if emotion:
                triggers.add(f"emotion:{emotion}")

            # 提取场景类型
            scene_type = hit.metadata.get("scene_type", "")
            if scene_type:
                triggers.add(f"scene:{scene_type}")

        return list(triggers)

    def _compute_confidence(
        self,
        corpus_hits: list,
        behavior_confidence: float
    ) -> float:
        """计算整体置信度

        当行为置信度来自 LLM（≥0.5）时，LLM 的判断占主导；
        否则回退到 TF-IDF 相似度加权。

        Args:
            corpus_hits: 语料命中结果
            behavior_confidence: 行为预测置信度（可能来自 LLM 或 TF-IDF）

        Returns:
            整体置信度（0 到 1）
        """
        # LLM 模式：行为置信度 ≥ 0.5 时，以 LLM 判断为主导
        if behavior_confidence >= 0.5:
            if not corpus_hits:
                return behavior_confidence * 0.9  # LLM 独立判断，略有折扣
            avg_similarity = sum(h.similarity for h in corpus_hits) / len(corpus_hits)
            # LLM 置信度为主，语料相似度为辅
            return behavior_confidence * 0.75 + avg_similarity * 0.25

        # Fallback 模式：综合 TF-IDF 因素
        if not corpus_hits:
            return 0.0

        hit_count_factor = min(len(corpus_hits) / 3, 1.0)
        avg_similarity = sum(h.similarity for h in corpus_hits) / len(corpus_hits)

        confidence = (
            behavior_confidence * 0.4 +
            avg_similarity * 0.4 +
            hit_count_factor * 0.2
        )

        return min(confidence, 1.0)
