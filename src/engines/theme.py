"""
主题引擎 (Theme Engine) — Phase 3

职责：从文本中提取主题、追踪主题演变、检测主题一致性。

契约（来源：02-CONTRACTS.md）：
- 不直接修改记忆，只返回建议
- 记忆更新由编排器统一写入
- 置信度 < 0.5 时必须返回 needs_human_review=True
- 主题提取结果供作者参考，不强制对齐预设主题

依赖：LLM 客户端（主题提取）、情节记忆（章节内容摘要）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Theme:
    """识别到的主题"""

    theme_id: str = ""
    """主题唯一标识"""

    name: str = ""
    """主题名称（如"命运无常"、"成长与蜕变"、"权力腐蚀"）"""

    strength: float = 0.5
    """主题在本章的强度 0-1"""

    keywords: list[str] = field(default_factory=list)
    """主题关联关键词"""

    related_characters: list[str] = field(default_factory=list)
    """与主题相关的角色"""

    supporting_evidence: str = ""
    """文本中的支撑证据（≤100 字）"""

    category: str = "general"
    """主题类别：character_growth | social_critique | love | power | fate | morality | general"""


@dataclass
class ThemeChange:
    """主题演变记录"""

    theme_name: str = ""
    """主题名称"""

    from_chapter: str = ""
    """起始章节"""

    to_chapter: str = ""
    """目标章节"""

    change_type: str = "stable"
    """演变类型：emerged | intensified | faded | transformed | resolved | stable"""

    strength_delta: float = 0.0
    """强度变化量（正=增强，负=减弱）"""

    description: str = ""
    """演变说明（30 字以内）"""


@dataclass
class ThemeAlert:
    """主题一致性警告"""

    alert_type: str = ""
    """警告类型：disappearance | contradiction | overload | underdevelopment"""

    theme_name: str = ""
    """相关主题"""

    detail: str = ""
    """警告详情"""

    suggestion: str = ""
    """建议"""


@dataclass
class ThemeQuery:
    """主题引擎查询输入"""

    chapter_text: str = ""
    """当前章节文本（≤4000 字）"""

    chapter_id: str = ""
    """当前章节标识"""

    previous_themes: list[dict] = field(default_factory=list)
    """前文章节的主题数据
    [{"chapter_id": "ch_01", "themes": [{"name": "...", "strength": 0.7}, ...]}, ...]
    """

    author_hints: list[str] = field(default_factory=list)
    """作者预设主题（可选，不强制对齐）"""


@dataclass
class ThemeResponse:
    """主题引擎查询输出"""

    identified_themes: list[Theme] = field(default_factory=list)
    """本章识别到的主题"""

    theme_evolution: list[ThemeChange] = field(default_factory=list)
    """与前文的主题演变"""

    consistency_alerts: list[ThemeAlert] = field(default_factory=list)
    """主题一致性警告"""

    dominant_theme: str = ""
    """本章主导主题名称"""

    confidence: float = 0.0
    """整体置信度"""

    needs_human_review: bool = False
    """置信度 < 0.5 时为 True"""


# ---------------------------------------------------------------------------
# 关键词 fallback 字典
# ---------------------------------------------------------------------------

# 中文文学主题关键词（用于 fallback 模式）
THEME_KEYWORDS: dict[str, dict] = {
    "fate": {
        "name": "命运无常",
        "keywords": ["命", "运", "天意", "注定", "劫数", "定数", "因果", "造化", "缘", "宿命"],
        "category": "fate",
    },
    "love": {
        "name": "情爱纠葛",
        "keywords": ["情", "爱", "相思", "痴情", "眷属", "姻缘", "倾心", "缠绵", "魂牵梦萦"],
        "category": "love",
    },
    "power": {
        "name": "权力争夺",
        "keywords": ["权", "势", "地位", "掌控", "争夺", "斗争", "胜者为王", "强者", "统治"],
        "category": "power",
    },
    "growth": {
        "name": "成长蜕变",
        "keywords": ["成长", "蜕变", "觉醒", "突破", "进阶", "修炼", "脱胎换骨", "涅槃", "新生"],
        "category": "character_growth",
    },
    "morality": {
        "name": "善恶道德",
        "keywords": ["善", "恶", "正", "邪", "道义", "良善", "黑", "白", "赎罪", "报应"],
        "category": "morality",
    },
    "social": {
        "name": "世态炎凉",
        "keywords": ["贫", "富", "贵", "贱", "官", "民", "世道", "人心", "冷暖", "炎凉"],
        "category": "social_critique",
    },
    "revenge": {
        "name": "复仇雪恨",
        "keywords": ["仇", "恨", "复仇", "雪恨", "血债", "报仇", "讨回", "清算"],
        "category": "general",
    },
    "sacrifice": {
        "name": "牺牲与守护",
        "keywords": ["牺牲", "守护", "奉献", "舍身", "换取", "代价", "成全"],
        "category": "general",
    },
}


# ---------------------------------------------------------------------------
# 引擎实现
# ---------------------------------------------------------------------------

class ThemeEngine:
    """主题引擎 — Phase 3

    从章节文本提取主题、追踪跨章节主题演变、检测一致性问题。
    基于 LLM 分析，辅以关键词 fallback。
    """

    def __init__(self, llm_client: Optional[object] = None) -> None:
        """初始化主题引擎

        Args:
            llm_client: LLM 客户端（可选）
        """
        self._llm = llm_client
        # 主题历史追踪
        self._theme_history: dict[str, list[Theme]] = {}  # chapter_id → themes

    def analyze(self, query: ThemeQuery) -> ThemeResponse:
        """分析章节主题

        执行三步分析：
        1. 从文本中提取主题
        2. 与历史主题对比，追踪演变
        3. 检测一致性问题

        Args:
            query: 主题查询

        Returns:
            ThemeResponse: 主题列表 + 演变记录 + 一致性警告
        """
        # 1. 主题提取
        themes = self._extract_themes(query)

        # 2. 记录到历史
        self._theme_history[query.chapter_id] = themes

        # 3. 主题演变分析
        evolution = self._analyze_evolution(query, themes)

        # 4. 一致性检查
        alerts = self._check_consistency(query, themes, evolution)

        # 5. 主导主题
        dominant = self._find_dominant_theme(themes)

        # 6. 置信度
        confidence = self._compute_confidence(themes)

        needs_human_review = confidence < 0.5

        return ThemeResponse(
            identified_themes=themes,
            theme_evolution=evolution,
            consistency_alerts=alerts,
            dominant_theme=dominant,
            confidence=confidence,
            needs_human_review=needs_human_review,
        )

    def get_theme_history(self) -> dict[str, list[Theme]]:
        """获取已分析的主题历史"""
        return dict(self._theme_history)

    # ------------------------------------------------------------------
    # 主题提取
    # ------------------------------------------------------------------

    def _extract_themes(self, query: ThemeQuery) -> list[Theme]:
        """从文本中提取主题

        Fallback 链：LLM 分析 → 关键词匹配

        Args:
            query: 主题查询

        Returns:
            主题列表
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    THEME_EXTRACT_SYSTEM,
                    format_theme_prompt,
                )

                user_message = format_theme_prompt(
                    text=query.chapter_text,
                    chapter_id=query.chapter_id,
                    author_hints=query.author_hints,
                )

                result = self._llm.call(
                    system_prompt=THEME_EXTRACT_SYSTEM,
                    user_message=user_message,
                    task_type="theme_extract",
                )

                if result and "themes" in result:
                    themes = []
                    for i, th in enumerate(result["themes"]):
                        themes.append(Theme(
                            theme_id=f"{query.chapter_id}_th_{i}",
                            name=th.get("name", ""),
                            strength=float(th.get("strength", 0.5)),
                            keywords=th.get("keywords", []),
                            related_characters=th.get("related_characters", []),
                            supporting_evidence=th.get("supporting_evidence", "")[:100],
                            category=th.get("category", "general"),
                        ))
                    return themes
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 关键词匹配
        return self._keyword_theme_detect(query)

    def _keyword_theme_detect(self, query: ThemeQuery) -> list[Theme]:
        """基于关键词检测主题（fallback）

        Args:
            query: 主题查询

        Returns:
            主题列表
        """
        text = query.chapter_text
        found = []

        for theme_key, theme_def in THEME_KEYWORDS.items():
            score = 0
            matched_kw = []
            for kw in theme_def["keywords"]:
                count = text.count(kw)
                if count > 0:
                    score += count
                    matched_kw.append(kw)

            if score >= 2:  # 至少 2 次命中
                # 归一化强度（最高 1.0）
                strength = min(score / 10, 1.0)
                found.append(Theme(
                    theme_id=f"{query.chapter_id}_th_{len(found)}",
                    name=theme_def["name"],
                    strength=strength,
                    keywords=matched_kw,
                    related_characters=[],
                    supporting_evidence="",
                    category=theme_def["category"],
                ))

        # 按强度降序
        found.sort(key=lambda t: t.strength, reverse=True)
        return found[:5]  # 最多 5 个主题

    # ------------------------------------------------------------------
    # 主题演变分析
    # ------------------------------------------------------------------

    def _analyze_evolution(
        self,
        query: ThemeQuery,
        current_themes: list[Theme],
    ) -> list[ThemeChange]:
        """对比前文主题，分析演变

        检测：新出现、增强、减弱、消失、转变

        Args:
            query: 主题查询
            current_themes: 当前章节提取的主题

        Returns:
            主题演变列表
        """
        if not query.previous_themes:
            return []

        changes = []
        current_names = {t.name for t in current_themes}
        current_strengths = {t.name: t.strength for t in current_themes}

        # 收集前文所有主题
        prev_themes: dict[str, list[dict]] = {}
        for prev_ch in query.previous_themes:
            ch_id = prev_ch.get("chapter_id", "")
            for th in prev_ch.get("themes", []):
                name = th.get("name", "")
                if name not in prev_themes:
                    prev_themes[name] = []
                prev_themes[name].append({
                    "chapter_id": ch_id,
                    "strength": th.get("strength", 0.5),
                })

        # 对比每个主题
        for name, appearances in prev_themes.items():
            prev_avg = sum(a["strength"] for a in appearances) / len(appearances)
            last_ch = appearances[-1]["chapter_id"]

            if name in current_names:
                # 主题延续
                cur_strength = current_strengths[name]
                delta = cur_strength - prev_avg

                if abs(delta) < 0.15:
                    change_type = "stable"
                elif delta > 0:
                    change_type = "intensified" if delta > 0.3 else "stable"
                else:
                    change_type = "faded" if delta < -0.3 else "stable"

                if change_type != "stable":
                    changes.append(ThemeChange(
                        theme_name=name,
                        from_chapter=last_ch,
                        to_chapter=query.chapter_id,
                        change_type=change_type,
                        strength_delta=round(delta, 2),
                        description=f"从强度 {prev_avg:.2f} 变为 {cur_strength:.2f}",
                    ))
            else:
                # 主题消失（前文有、本章无）
                if prev_avg > 0.4:  # 只有较强主题消失才告警（演变层不做告警，留给一致性层）
                    changes.append(ThemeChange(
                        theme_name=name,
                        from_chapter=last_ch,
                        to_chapter=query.chapter_id,
                        change_type="faded",
                        strength_delta=-prev_avg,
                        description=f"前文强度 {prev_avg:.2f} 的主题在本章未出现",
                    ))

        # 新出现的主题
        for th in current_themes:
            if th.name not in prev_themes:
                changes.append(ThemeChange(
                    theme_name=th.name,
                    from_chapter="",
                    to_chapter=query.chapter_id,
                    change_type="emerged",
                    strength_delta=th.strength,
                    description=f"新主题 '{th.name}' 在本章首次出现",
                ))

        return changes

    # ------------------------------------------------------------------
    # 一致性检查
    # ------------------------------------------------------------------

    def _check_consistency(
        self,
        query: ThemeQuery,
        themes: list[Theme],
        evolution: list[ThemeChange],
    ) -> list[ThemeAlert]:
        """检测主题一致性问题

        检查：
        1. 主题过载（一次出现过多主题）
        2. 核心主题突然消失
        3. 主题发展不足
        4. 与作者预设偏差

        Args:
            query: 主题查询
            themes: 当前主题
            evolution: 演变记录

        Returns:
            警告列表
        """
        alerts = []

        # 1. 主题过载检测
        if len(themes) > 5:
            alerts.append(ThemeAlert(
                alert_type="overload",
                theme_name="",
                detail=f"本章识别到 {len(themes)} 个主题，可能过于分散",
                suggestion="建议聚焦 2-3 个核心主题，避免叙事焦点分散",
            ))

        # 2. 重要主题消失
        for change in evolution:
            if change.change_type == "faded" and change.strength_delta < -0.3:
                alerts.append(ThemeAlert(
                    alert_type="disappearance",
                    theme_name=change.theme_name,
                    detail=f"主题 '{change.theme_name}' 在本章（{query.chapter_id}）强度骤降",
                    suggestion=f"如非有意为之，考虑在后续章节回收该主题",
                ))

        # 3. 主题发展不足（持续稳定但强度低）
        for th in themes:
            if th.strength < 0.3:
                # 检查前文是否也低
                prev_low = all(
                    prev_th.get("strength", 0) < 0.3
                    for prev_ch in query.previous_themes
                    for prev_th in prev_ch.get("themes", [])
                    if prev_th.get("name") == th.name
                )
                if prev_low and query.previous_themes:
                    alerts.append(ThemeAlert(
                        alert_type="underdevelopment",
                        theme_name=th.name,
                        detail=f"主题 '{th.name}' 持续低强度，可能发展不足",
                        suggestion="考虑加强该主题的文本支撑，或确认是否为次要主题",
                    ))

        # 4. 与作者预设对比（不强制，仅提醒）
        if query.author_hints:
            current_names = {t.name for t in themes}
            for hint in query.author_hints:
                # 简单关键词匹配
                matched = any(hint[:2] in name for name in current_names)
                if not matched:
                    alerts.append(ThemeAlert(
                        alert_type="disappearance",
                        theme_name=hint,
                        detail=f"作者预设主题 '{hint}' 在当前章节未检测到",
                        suggestion="可忽略，此提醒仅供作者参考",
                    ))

        return alerts

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _find_dominant_theme(themes: list[Theme]) -> str:
        """找出主导主题（强度最高）"""
        if not themes:
            return ""
        return max(themes, key=lambda t: t.strength).name

    def _compute_confidence(self, themes: list[Theme]) -> float:
        """计算整体置信度

        Args:
            themes: 主题列表

        Returns:
            置信度 0-1
        """
        if self._llm and self._llm.is_available:
            base = 0.75
            # 主题越多置信度越低
            penalty = max(0, (len(themes) - 5) * 0.1)
            return max(base - penalty, 0.3)

        # Fallback 模式
        base = 0.45
        if themes:
            # 有主题检测到，稍高
            base = 0.5
            # 关键词命中越多，可能越准确（但上限低）
            total_kw = sum(len(t.keywords) for t in themes)
            base = min(base + total_kw * 0.02, 0.65)
        return base
