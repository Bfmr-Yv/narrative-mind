"""
叙事引擎 (Narrative Engine) — Phase 2

职责：追踪伏笔、构建因果链、检测未回收伏笔和叙事矛盾。

契约（来源：02-CONTRACTS.md）：
- 不直接修改记忆，只返回建议
- 记忆更新由编排器统一写入
- 置信度 < 0.5 时必须返回 needs_human_review=True
- 跨章节分析依赖工作记忆提供前文章节摘要

依赖：LLM 客户端（伏笔检测 + 因果抽取）、工作记忆（前文章节摘要）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Foreshadowing:
    """伏笔

    表示文本中埋下的一个伏笔——可能是一句暗示、一个未解释的细节、
    一个角色的异常行为等。伏笔有生命周期：planted → partial → resolved。
    """

    foreshadow_id: str  # 唯一标识
    chapter_id: str  # 出现的章节
    description: str  # 伏笔内容描述（人类可读）
    hint_text: str  # 原文中的暗示片段（≤100 字）
    category: str = "unknown"  # 类型：character / event / object / dialogue / setting
    status: str = "planted"  # planted | partial | resolved
    resolved_in: Optional[str] = None  # 回收该伏笔的章节 ID
    related_characters: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 伏笔检测置信度


@dataclass
class CausalLink:
    """因果链

    连接两个事件：cause 导致/触发 effect。
    多条因果链可构成因果图谱。
    """

    cause_event: str  # 原因事件描述
    effect_event: str  # 结果事件描述
    strength: float = 0.5  # 因果强度 0-1（1=必然导致，0=微弱相关）
    description: str = ""  # 因果关系的简要说明
    chapter_id: str = ""  # 因果关系所在的章节


@dataclass
class NarrativeQuery:
    """叙事引擎查询输入"""

    chapter_text: str  # 当前章节文本（≤4000 字）
    chapter_id: str  # 当前章节标识
    previous_chapters: list[dict] = field(default_factory=list)
    # previous_chapters: [{"chapter_id": str, "summary": str, "key_events": [str]}, ...]
    known_foreshadowings: list[Foreshadowing] = field(default_factory=list)
    # 已知的未回收伏笔（来自工作记忆）


@dataclass
class NarrativeResponse:
    """叙事引擎查询输出"""

    foreshadowings: list[Foreshadowing] = field(default_factory=list)
    causal_links: list[CausalLink] = field(default_factory=list)
    unresolved_foreshadowings: list[Foreshadowing] = field(default_factory=list)
    narrative_issues: list[str] = field(default_factory=list)
    event_prediction: str = ""  # 基于因果链的短期情节推演
    confidence: float = 0.0
    needs_human_review: bool = False


# ---------------------------------------------------------------------------
# 关键词 fallback 字典
# ---------------------------------------------------------------------------

# 伏笔提示词（用于关键词 fallback）
FORESHADOW_KEYWORDS: dict[str, list[str]] = {
    "object": ["物", "玉", "剑", "镜", "珠", "符", "印", "书", "信", "盒", "锁", "药"],
    "dialogue": ["预言", "天机", "不可说", "日后", "将来", "必有", "定数", "因果", "命数"],
    "character": ["似曾相识", "熟悉的感觉", "来历不明", "不简单", "隐藏", "深不可测"],
    "event": ["异象", "征兆", "异常", "奇怪", "不对劲", "变化", "预兆"],
    "setting": ["禁地", "秘境", "封印", "阵法", "机关"],
}

# 因果关键词（用于关键词 fallback）
CAUSAL_KEYWORDS = ["因为", "所以", "因此", "于是", "导致", "引起", "使得", "造成", "因而", "之所以"]


# ---------------------------------------------------------------------------
# 引擎实现
# ---------------------------------------------------------------------------

class NarrativeEngine:
    """叙事引擎 — Phase 2

    伏笔追踪、因果链构建、未回收伏笔检测。
    基于 LLM 分析，辅以关键词 fallback。
    """

    def __init__(self, llm_client: Optional[object] = None) -> None:
        """初始化叙事引擎

        Args:
            llm_client: LLM 客户端实例（可选，未配置时使用关键词 fallback）
        """
        self._llm = llm_client
        self._foreshadowing_registry: dict[str, Foreshadowing] = {}
        # 跨章节因果链缓存
        self._causal_graph: dict[str, list[CausalLink]] = {}

    def analyze(self, query: NarrativeQuery) -> NarrativeResponse:
        """分析章节的叙事元素

        执行三步分析：
        1. 检测当前章节中的新伏笔
        2. 提取事件间的因果关系
        3. 检查已知伏笔是否被回收

        Args:
            query: 包含章节文本和前文上下文的查询

        Returns:
            NarrativeResponse: 伏笔列表、因果链、未回收伏笔、叙事问题
        """
        # 1. 伏笔检测
        new_foreshadowings = self._detect_foreshadowings(query)

        # 2. 因果链提取
        causal_links = self._extract_causal_links(query)

        # 3. 跨章节伏笔回收检查
        resolved, unresolved = self._check_foreshadowing_resolution(
            query.known_foreshadowings, query
        )

        # 4. 叙事问题检测
        narrative_issues = self._detect_issues(
            query, new_foreshadowings, causal_links, unresolved
        )

        # 5. 短期情节推演
        event_prediction = self._predict_events(query, causal_links)

        # 6. 计算整体置信度
        confidence = self._compute_confidence(new_foreshadowings, causal_links)

        # 7. 注册新伏笔
        for fs in new_foreshadowings:
            self._foreshadowing_registry[fs.foreshadow_id] = fs

        needs_human_review = confidence < 0.5

        return NarrativeResponse(
            foreshadowings=new_foreshadowings + resolved,
            causal_links=causal_links,
            unresolved_foreshadowings=unresolved,
            narrative_issues=narrative_issues,
            event_prediction=event_prediction,
            confidence=confidence,
            needs_human_review=needs_human_review,
        )

    def get_unresolved_foreshadowings(self) -> list[Foreshadowing]:
        """获取所有未回收的伏笔

        Returns:
            未回收伏笔列表
        """
        return [
            fs for fs in self._foreshadowing_registry.values()
            if fs.status != "resolved"
        ]

    def mark_resolved(self, foreshadow_id: str, chapter_id: str) -> bool:
        """标记伏笔为已回收

        Args:
            foreshadow_id: 伏笔 ID
            chapter_id: 回收伏笔的章节

        Returns:
            是否成功标记
        """
        fs = self._foreshadowing_registry.get(foreshadow_id)
        if not fs:
            return False

        fs.status = "resolved"
        fs.resolved_in = chapter_id
        return True

    # ------------------------------------------------------------------
    # 伏笔检测
    # ------------------------------------------------------------------

    def _detect_foreshadowings(self, query: NarrativeQuery) -> list[Foreshadowing]:
        """检测当前章节中的伏笔

        Fallback 链：LLM 分析 → 关键词匹配

        Args:
            query: 叙事查询

        Returns:
            检测到的伏笔列表
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    FORESHADOW_DETECT_SYSTEM,
                    format_foreshadow_prompt,
                )

                user_message = format_foreshadow_prompt(
                    chapter_text=query.chapter_text,
                    chapter_id=query.chapter_id,
                )

                result = self._llm.call(
                    system_prompt=FORESHADOW_DETECT_SYSTEM,
                    user_message=user_message,
                    task_type="foreshadow_detect",
                )

                if result and "foreshadowings" in result:
                    return [
                        Foreshadowing(
                            foreshadow_id=f"{query.chapter_id}_fs_{i}",
                            chapter_id=query.chapter_id,
                            description=fs.get("description", ""),
                            hint_text=fs.get("hint_text", ""),
                            category=fs.get("category", "unknown"),
                            status="planted",
                            related_characters=fs.get("related_characters", []),
                            confidence=float(fs.get("confidence", 0.5)),
                        )
                        for i, fs in enumerate(result["foreshadowings"])
                    ]
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 关键词匹配 fallback
        return self._keyword_foreshadow_detect(query)

    def _keyword_foreshadow_detect(self, query: NarrativeQuery) -> list[Foreshadowing]:
        """基于关键词检测伏笔（fallback）

        Args:
            query: 叙事查询

        Returns:
            检测到的伏笔列表
        """
        text = query.chapter_text
        found = []

        for category, keywords in FORESHADOW_KEYWORDS.items():
            for kw in keywords:
                idx = text.find(kw)
                if idx >= 0:
                    start = max(0, idx - 20)
                    end = min(len(text), idx + 80)
                    found.append(Foreshadowing(
                        foreshadow_id=f"{query.chapter_id}_kw_{len(found)}",
                        chapter_id=query.chapter_id,
                        description=f"文本中出现关键词「{kw}」，可能暗示{category}类伏笔",
                        hint_text=text[start:end],
                        category=category,
                        status="planted",
                        confidence=0.3,  # 关键词匹配置信度低
                    ))
                    break  # 每类只取第一个

        return found

    # ------------------------------------------------------------------
    # 因果链提取
    # ------------------------------------------------------------------

    def _extract_causal_links(self, query: NarrativeQuery) -> list[CausalLink]:
        """从章节文本中提取因果链

        Fallback 链：LLM 分析 → 关键词匹配

        Args:
            query: 叙事查询

        Returns:
            因果链列表
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    CAUSAL_EXTRACT_SYSTEM,
                    format_causal_prompt,
                )

                user_message = format_causal_prompt(
                    chapter_text=query.chapter_text,
                    chapter_id=query.chapter_id,
                )

                result = self._llm.call(
                    system_prompt=CAUSAL_EXTRACT_SYSTEM,
                    user_message=user_message,
                    task_type="causal_extract",
                )

                if result and "causal_links" in result:
                    links = []
                    for link in result["causal_links"]:
                        cl = CausalLink(
                            cause_event=link.get("cause", ""),
                            effect_event=link.get("effect", ""),
                            strength=float(link.get("strength", 0.5)),
                            description=link.get("description", ""),
                            chapter_id=query.chapter_id,
                        )
                        links.append(cl)
                    return links
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 关键词匹配 fallback
        return self._keyword_causal_extract(query)

    def _keyword_causal_extract(self, query: NarrativeQuery) -> list[CausalLink]:
        """基于关键词提取因果链（fallback）

        Args:
            query: 叙事查询

        Returns:
            因果链列表
        """
        text = query.chapter_text
        links = []
        sentences = text.replace("！", "。").replace("？", "。").split("。")

        for kw in CAUSAL_KEYWORDS:
            for i, sent in enumerate(sentences):
                if kw in sent and i > 0:
                    links.append(CausalLink(
                        cause_event=sentences[i - 1][:80].strip(),
                        effect_event=sent[:120].strip(),
                        strength=0.3,
                        description=f"关键词「{kw}」连接",
                        chapter_id=query.chapter_id,
                    ))
                    if len(links) >= 5:
                        return links

        return links

    # ------------------------------------------------------------------
    # 跨章节伏笔回收检查
    # ------------------------------------------------------------------

    def _check_foreshadowing_resolution(
        self,
        known_foreshadowings: list[Foreshadowing],
        query: NarrativeQuery,
    ) -> tuple[list[Foreshadowing], list[Foreshadowing]]:
        """检查已知伏笔是否在当前章节被回收

        LLM 模式下：让 LLM 判断已知伏笔是否在本章得到呼应
        Fallback 模式：检查关键词是否有重叠

        Args:
            known_foreshadowings: 已知的未回收伏笔
            query: 当前章节的叙事查询

        Returns:
            (已回收伏笔列表, 仍未回收伏笔列表)
        """
        if not known_foreshadowings:
            return [], []

        resolved = []
        unresolved = []

        for fs in known_foreshadowings:
            resolved_flag = False

            # Tier 1: LLM 判断
            if self._llm and self._llm.is_available:
                try:
                    from ..llm.prompts import (
                        RESOLUTION_CHECK_SYSTEM,
                        format_resolution_check_prompt,
                    )

                    user_message = format_resolution_check_prompt(
                        foreshadowing_desc=fs.description,
                        foreshadowing_hint=fs.hint_text,
                        chapter_text=query.chapter_text,
                    )

                    result = self._llm.call(
                        system_prompt=RESOLUTION_CHECK_SYSTEM,
                        user_message=user_message,
                        task_type="resolution_check",
                    )

                    if result and "resolved" in result:
                        if result["resolved"]:
                            fs.status = "resolved"
                            fs.resolved_in = query.chapter_id
                            fs.confidence = float(result.get("confidence", 0.5))
                            resolved.append(fs)
                            resolved_flag = True
                except Exception:
                    pass  # Fall through to fallback

            # Tier 2: 关键词匹配 fallback
            if not resolved_flag:
                # 检查伏笔的关键词是否在本章出现
                hint_words = set(fs.hint_text)
                chapter_words = set(query.chapter_text)
                overlap = hint_words & chapter_words if hint_words else set()

                if len(overlap) > 5:
                    fs.status = "partial"
                    fs.confidence = 0.3
                    resolved.append(fs)
                else:
                    unresolved.append(fs)

        return resolved, unresolved

    # ------------------------------------------------------------------
    # 叙事问题检测
    # ------------------------------------------------------------------

    def _detect_issues(
        self,
        query: NarrativeQuery,
        new_foreshadowings: list[Foreshadowing],
        causal_links: list[CausalLink],
        unresolved_foreshadowings: list[Foreshadowing],
    ) -> list[str]:
        """检测叙事问题

        检查以下问题类型：
        1. 矛盾：因果链中的循环依赖
        2. 遗忘：长时间未回收的伏笔
        3. 断层：缺乏因果连接的连续事件
        4. 重复：同一类型伏笔被重复埋设

        Args:
            query: 叙事查询
            new_foreshadowings: 新检测到的伏笔
            causal_links: 提取的因果链
            unresolved_foreshadowings: 仍未回收的伏笔

        Returns:
            叙事问题描述列表
        """
        issues = []

        # 1. 因果循环检测
        causes = {link.cause_event for link in causal_links}
        effects = {link.effect_event for link in causal_links}
        circular = causes & effects
        if len(circular) >= 2:
            issues.append(f"可能存在因果循环：{len(circular)} 个事件同时是原因和结果")

        # 2. 长期未回收伏笔提醒
        if len(unresolved_foreshadowings) >= 3:
            oldest = unresolved_foreshadowings[0]
            issues.append(
                f"有 {len(unresolved_foreshadowings)} 个伏笔尚未回收，"
                f"最早的是「{oldest.description[:30]}...」（{oldest.chapter_id}）"
            )

        # 3. 因果缺失检查
        if query.previous_chapters and not causal_links:
            issues.append("当前章节未检测到与前文的明确因果连接，可能导致叙事断层")

        # 4. 伏笔类型集中检查
        categories = [fs.category for fs in new_foreshadowings]
        if categories.count("object") >= 3:
            issues.append("当前章节埋设了多个物品类伏笔，避免过度依赖同一手法")

        return issues

    # ------------------------------------------------------------------
    # 短期情节推演
    # ------------------------------------------------------------------

    def _predict_events(
        self,
        query: NarrativeQuery,
        causal_links: list[CausalLink],
    ) -> str:
        """基于当前因果链推演短期情节发展

        Fallback 链：LLM 分析 → 因果链拼接

        Args:
            query: 叙事查询
            causal_links: 当前章节的因果链

        Returns:
            情节推演文本
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    EVENT_PREDICT_SYSTEM,
                    format_event_predict_prompt,
                )

                user_message = format_event_predict_prompt(
                    chapter_text=query.chapter_text,
                    causal_summary=self._summarize_causal_links(causal_links),
                )

                result = self._llm.call(
                    system_prompt=EVENT_PREDICT_SYSTEM,
                    user_message=user_message,
                    task_type="event_predict",
                )

                if result and "prediction" in result:
                    return result["prediction"]
            except Exception:
                pass

        # Tier 2: 因果链拼接 fallback
        if causal_links:
            parts = ["基于当前因果链的推演："]
            for link in causal_links[:3]:
                parts.append(f"因为 {link.cause_event[:40]}，可能导致 {link.effect_event[:60]}")
            return "；".join(parts)

        return "无法生成情节推演（因果链不足）"

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize_causal_links(links: list[CausalLink]) -> str:
        """将因果链列表格式化为文本摘要"""
        if not links:
            return "（当前章节未检测到明确因果链）"

        parts = []
        for link in links[:5]:
            parts.append(
                f"「{link.cause_event[:50]}」→「{link.effect_event[:50]}」"
                f"（强度: {link.strength:.2f}）"
            )
        return "\n".join(parts)

    def _compute_confidence(
        self,
        foreshadowings: list[Foreshadowing],
        causal_links: list[CausalLink],
    ) -> float:
        """计算整体置信度

        Args:
            foreshadowings: 检测到的伏笔
            causal_links: 提取的因果链

        Returns:
            整体置信度 0-1
        """
        # LLM 模式：伏笔和因果链都有结果时置信度高
        if foreshadowings and causal_links:
            fs_conf = sum(fs.confidence for fs in foreshadowings) / len(foreshadowings)
            cl_conf = sum(link.strength for link in causal_links) / len(causal_links)
            return min(fs_conf * 0.6 + cl_conf * 0.4, 1.0)

        # 仅伏笔
        if foreshadowings:
            return min(
                sum(fs.confidence for fs in foreshadowings) / len(foreshadowings),
                0.8,
            )

        # 仅因果链
        if causal_links:
            return min(
                sum(link.strength for link in causal_links) / len(causal_links),
                0.6,
            )

        return 0.1  # 无结果
