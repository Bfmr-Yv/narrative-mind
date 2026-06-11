"""
文辞引擎 (Prose Engine) — Phase 2

职责：检测文风一致性（语域、句式、修辞密度），标记风格漂移。

契约（来源：02-CONTRACTS.md）：
- 不直接修改记忆，只返回建议
- 记忆更新由编排器统一写入
- 置信度 < 0.5 时必须返回 needs_human_review=True
- 只检测和报告，不做自动改写
- 风格建议仅供参考

依赖：LLM 客户端（风格分析 + 语域检测）、工作记忆（作者指纹基线）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class StyleMetrics:
    """风格量化指标

    从给定文本中提取的量化风格特征。
    """

    avg_sentence_length: float = 0.0
    """平均句长（字符数）"""

    dialogue_ratio: float = 0.0
    """对话占比 0-1（引导内文本 / 总文本）"""

    vocabulary_richness: float = 0.0
    """词汇丰富度（unique / total，0-1）"""

    register_level: str = "neutral"
    """语域层级：casual | informal | neutral | formal | literary"""

    rhetoric_density: float = 0.0
    """修辞密度 0-1（比喻/拟人/排比等修辞格的出现频率）"""


@dataclass
class StyleDeviation:
    """风格偏离

    标记某段文本与整体风格基线的不一致之处。
    """

    paragraph_index: int = 0
    """偏离发生的段落序号（0-based）"""

    snippet: str = ""
    """偏离文本片段（≤80 字）"""

    deviation_type: str = ""
    """偏离类型：register | dialogue_ratio | sentence_length | vocabulary | rhetoric"""

    severity: float = 0.0
    """偏离严重程度 0-1（1=严重偏离基线）"""

    suggestion: str = ""
    """修正建议（30 字以内）"""


@dataclass
class ProseQuery:
    """文辞引擎查询输入"""

    text: str
    """待检测文本（≤4000 字）"""

    baseline_texts: list[str] = field(default_factory=list)
    """用于建立风格基线的历史章节文本（最近 2-3 章）"""

    chapter_id: str = ""
    """当前章节标识"""


@dataclass
class ProseResponse:
    """文辞引擎查询输出"""

    style_metrics: Optional[StyleMetrics] = None
    """当前文本的风格量化指标"""

    deviations: list[StyleDeviation] = field(default_factory=list)
    """偏离基线的段落列表"""

    register_consistency: float = 0.0
    """语域一致性 0-1（1=与基线完全一致）"""

    character_voice_issues: list[str] = field(default_factory=list)
    """角色用语一致性问题（如"某角色突然使用不符合其身份的措辞"）"""

    confidence: float = 0.0
    """整体置信度 0-1"""

    needs_human_review: bool = False
    """置信度 < 0.5 时为 True"""


# ---------------------------------------------------------------------------
# 关键词 fallback 字典
# ---------------------------------------------------------------------------

# 语域特征词
REGISTER_MARKERS: dict[str, list[str]] = {
    "casual": ["啦", "吧", "嘛", "呗", "咋", "啥", "咋的", "得了", "算了"],
    "informal": ["的", "了", "呢", "啊", "哦", "哈", "嗯", "哎"],
    "formal": ["阁下", "大人", "殿下", "君", "公", "卿", "诸位", "尔等", "吾等"],
    "literary": ["之乎者也", "呜呼", "嗟乎", "矣", "哉", "兮", "嗟", "噫"],
}

# 修辞标记（关键词概览，精确检测依赖 LLM）
RHETORIC_MARKERS: dict[str, list[str]] = {
    "metaphor": ["如", "像", "仿佛", "好似", "犹如", "宛如", "宛若", "恰似"],
    "personification": ["风在", "月儿", "花儿", "阳光洒", "时间流逝"],
    "parallelism": [],  # 排比需结构分析，LLM-only
    "hyperbole": ["万万", "绝无", "从未", "天下第一", "无人能及"],
}


# ---------------------------------------------------------------------------
# 引擎实现
# ---------------------------------------------------------------------------

class ProseEngine:
    """文辞引擎 — Phase 2

    检测文风一致性：语域、句式、修辞密度，标记风格漂移。
    基于 LLM 分析，辅以关键词 fallback。
    """

    def __init__(self, llm_client: Optional[object] = None) -> None:
        """初始化文辞引擎

        Args:
            llm_client: LLM 客户端实例（可选，未配置时使用关键词 fallback）
        """
        self._llm = llm_client
        # 作者指纹基线缓存
        self._baseline_metrics: Optional[StyleMetrics] = None

    def analyze(self, query: ProseQuery) -> ProseResponse:
        """分析文本的风格特征

        执行三步分析：
        1. 提取当前文本的风格量化指标
        2. 与基线对比，检测风格偏离
        3. 检查语域一致性和角色用语

        Args:
            query: 包含当前文本和基线文本的查询

        Returns:
            ProseResponse: 风格指标、偏离列表、语域一致性
        """
        # 1. 风格指标提取
        style_metrics = self._extract_style_metrics(query)

        # 2. 更新/建立基线
        self._update_baseline(style_metrics, query.baseline_texts)

        # 3. 风格偏离检测
        deviations = self._detect_deviations(query, style_metrics)

        # 4. 语域一致性检查
        register_consistency = self._check_register_consistency(query, style_metrics)

        # 5. 角色用语检查
        character_voice_issues = self._check_character_voice(query)

        # 6. 计算整体置信度
        confidence = self._compute_confidence(style_metrics, deviations)

        needs_human_review = confidence < 0.5

        return ProseResponse(
            style_metrics=style_metrics,
            deviations=deviations,
            register_consistency=register_consistency,
            character_voice_issues=character_voice_issues,
            confidence=confidence,
            needs_human_review=needs_human_review,
        )

    def get_baseline(self) -> Optional[StyleMetrics]:
        """获取当前基线指标

        Returns:
            基线风格指标，未建立时返回 None
        """
        return self._baseline_metrics

    # ------------------------------------------------------------------
    # 风格指标提取
    # ------------------------------------------------------------------

    def _extract_style_metrics(self, query: ProseQuery) -> StyleMetrics:
        """从文本中提取风格量化指标

        Fallback 链：LLM 分析 → 规则统计

        Args:
            query: 文辞查询

        Returns:
            StyleMetrics 实例
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    STYLE_CHECK_SYSTEM,
                    format_style_prompt,
                )

                user_message = format_style_prompt(
                    text=query.text,
                    chapter_id=query.chapter_id,
                )

                result = self._llm.call(
                    system_prompt=STYLE_CHECK_SYSTEM,
                    user_message=user_message,
                    task_type="style_check",
                )

                if result:
                    return StyleMetrics(
                        avg_sentence_length=float(result.get("avg_sentence_length", 0)),
                        dialogue_ratio=float(result.get("dialogue_ratio", 0)),
                        vocabulary_richness=float(result.get("vocabulary_richness", 0)),
                        register_level=str(result.get("register_level", "neutral")),
                        rhetoric_density=float(result.get("rhetoric_density", 0)),
                    )
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 规则统计 fallback
        return self._rule_based_style_metrics(query.text)

    def _rule_based_style_metrics(self, text: str) -> StyleMetrics:
        """基于规则统计风格指标（fallback）

        Args:
            text: 待分析文本

        Returns:
            StyleMetrics 实例
        """
        if not text.strip():
            return StyleMetrics()

        # 1. 平均句长
        sentences = [s.strip() for s in text.replace("！", "。").replace("？", "。").replace("……", "。").split("。") if s.strip()]
        avg_sentence_length = (
            sum(len(s) for s in sentences) / len(sentences)
            if sentences else 0.0
        )

        # 2. 对话占比（检测引号内文本）
        import re
        dialogue_text = "".join(re.findall(r'["""]([^"」""」]*)["」""」]', text))
        dialogue_ratio = len(dialogue_text) / len(text) if text else 0.0

        # 3. 词汇丰富度
        chars = [c for c in text if c.strip() and '一' <= c <= '鿿']
        unique_chars = set(chars)
        vocabulary_richness = len(unique_chars) / len(chars) if chars else 0.0

        # 4. 语域层级（基于关键词密度）
        register_level = self._guess_register(text)

        # 5. 修辞密度（基于关键词检测）
        rhetoric_count = 0
        for category, markers in RHETORIC_MARKERS.items():
            for marker in markers:
                rhetoric_count += text.count(marker)
        rhetoric_density = min(rhetoric_count / max(len(text) / 100, 1), 1.0)

        return StyleMetrics(
            avg_sentence_length=round(avg_sentence_length, 1),
            dialogue_ratio=round(dialogue_ratio, 2),
            vocabulary_richness=round(vocabulary_richness, 2),
            register_level=register_level,
            rhetoric_density=round(rhetoric_density, 2),
        )

    @staticmethod
    def _guess_register(text: str) -> str:
        """基于关键词推测语域层级

        Args:
            text: 文本

        Returns:
            语域层级字符串
        """
        scores = {}
        for level, markers in REGISTER_MARKERS.items():
            score = sum(text.count(m) for m in markers)
            scores[level] = score

        if not scores or max(scores.values()) == 0:
            return "neutral"

        # 取最高分的层级
        best = max(scores, key=lambda k: scores[k])
        return best

    # ------------------------------------------------------------------
    # 基线管理
    # ------------------------------------------------------------------

    def _update_baseline(
        self,
        metrics: StyleMetrics,
        baseline_texts: list[str],
    ) -> None:
        """更新作者指纹基线

        首次建立基线时直接设置；后续用移动平均更新。
        基线文本用于建立初始基线。

        Args:
            metrics: 当前文本的风格指标
            baseline_texts: 历史章节文本
        """
        if baseline_texts and not self._baseline_metrics:
            # 从基线文本建立初始基线
            combined = "\n".join(baseline_texts)
            self._baseline_metrics = self._rule_based_style_metrics(combined)

        # 如果已有基线，用移动平均缓慢更新
        if self._baseline_metrics:
            alpha = 0.3  # 新文本权重
            old = self._baseline_metrics
            self._baseline_metrics = StyleMetrics(
                avg_sentence_length=round(
                    old.avg_sentence_length * (1 - alpha) + metrics.avg_sentence_length * alpha, 1
                ),
                dialogue_ratio=round(
                    old.dialogue_ratio * (1 - alpha) + metrics.dialogue_ratio * alpha, 2
                ),
                vocabulary_richness=round(
                    old.vocabulary_richness * (1 - alpha) + metrics.vocabulary_richness * alpha, 2
                ),
                register_level=metrics.register_level,  # 语域不取平均，以最新为准
                rhetoric_density=round(
                    old.rhetoric_density * (1 - alpha) + metrics.rhetoric_density * alpha, 2
                ),
            )

    # ------------------------------------------------------------------
    # 风格偏离检测
    # ------------------------------------------------------------------

    def _detect_deviations(
        self,
        query: ProseQuery,
        metrics: StyleMetrics,
    ) -> list[StyleDeviation]:
        """检测当前文本与基线的风格偏离

        Fallback 链：LLM 分析 → 规则对比

        Args:
            query: 文辞查询
            metrics: 当前文本的风格指标

        Returns:
            偏离列表
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available and self._baseline_metrics:
            try:
                from ..llm.prompts import (
                    REGISTER_CHECK_SYSTEM,
                    format_register_prompt,
                )

                baseline = self._baseline_metrics
                user_message = format_register_prompt(
                    text=query.text,
                    baseline_register=baseline.register_level,
                    baseline_summary=(
                        f"平均句长 {baseline.avg_sentence_length} 字，"
                        f"对话占比 {baseline.dialogue_ratio}，"
                        f"词汇丰富度 {baseline.vocabulary_richness}"
                    ),
                )

                result = self._llm.call(
                    system_prompt=REGISTER_CHECK_SYSTEM,
                    user_message=user_message,
                    task_type="register_check",
                )

                if result and "deviations" in result:
                    return [
                        StyleDeviation(
                            paragraph_index=int(d.get("paragraph_index", 0)),
                            snippet=str(d.get("snippet", "")[:80]),
                            deviation_type=str(d.get("deviation_type", "register")),
                            severity=float(d.get("severity", 0.3)),
                            suggestion=str(d.get("suggestion", "")[:30]),
                        )
                        for d in result["deviations"]
                    ]
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 规则对比 fallback
        return self._rule_based_deviation_detect(metrics)

    def _rule_based_deviation_detect(
        self,
        metrics: StyleMetrics,
    ) -> list[StyleDeviation]:
        """基于规则检测风格偏离（fallback）

        Args:
            metrics: 当前文本的风格指标

        Returns:
            风格偏离列表
        """
        if not self._baseline_metrics:
            return []

        deviations = []
        baseline = self._baseline_metrics

        # 句长偏离检测
        sent_diff = abs(metrics.avg_sentence_length - baseline.avg_sentence_length)
        if sent_diff > 15:
            severity = min(sent_diff / 30, 1.0)
            direction = "变长" if metrics.avg_sentence_length > baseline.avg_sentence_length else "变短"
            deviations.append(StyleDeviation(
                paragraph_index=0,
                snippet=f"平均句长从 {baseline.avg_sentence_length} {direction}为 {metrics.avg_sentence_length}",
                deviation_type="sentence_length",
                severity=severity,
                suggestion=f"注意句长{direction}趋势，保持与前文一致" if severity > 0.5 else "",
            ))

        # 对话占比偏离检测
        dialog_diff = abs(metrics.dialogue_ratio - baseline.dialogue_ratio)
        if dialog_diff > 0.2:
            severity = min(dialog_diff / 0.4, 1.0)
            direction = "增多" if metrics.dialogue_ratio > baseline.dialogue_ratio else "减少"
            deviations.append(StyleDeviation(
                paragraph_index=0,
                snippet=f"对话占比从 {baseline.dialogue_ratio} {direction}为 {metrics.dialogue_ratio}",
                deviation_type="dialogue_ratio",
                severity=severity,
                suggestion=f"对话密度{direction}可能影响节奏" if severity > 0.5 else "",
            ))

        # 语域偏离检测
        if (metrics.register_level != baseline.register_level
                and metrics.register_level != "neutral"
                and baseline.register_level != "neutral"):
            deviations.append(StyleDeviation(
                paragraph_index=0,
                snippet=f"语域从 '{baseline.register_level}' 变为 '{metrics.register_level}'",
                deviation_type="register",
                severity=0.6,
                suggestion="检查本节叙述视角或氛围是否需要调整语域",
            ))

        return deviations

    # ------------------------------------------------------------------
    # 语域一致性
    # ------------------------------------------------------------------

    def _check_register_consistency(
        self,
        query: ProseQuery,
        metrics: StyleMetrics,
    ) -> float:
        """检查语域一致性

        LLM 模式下返回 LLM 评分，fallback 模式对比基线语域。

        Args:
            query: 文辞查询
            metrics: 当前风格指标

        Returns:
            语域一致性 0-1
        """
        # LLM 结果已在 _detect_deviations 中获取，这里做综合评分
        if not self._baseline_metrics:
            return 0.8  # 无基线时默认较高

        baseline = self._baseline_metrics

        # 语域相同时一致性高
        if metrics.register_level == baseline.register_level:
            return 0.9

        # 相邻语域层级（如 neutral↔formal）降分
        register_order = ["casual", "informal", "neutral", "formal", "literary"]
        try:
            idx_cur = register_order.index(metrics.register_level)
            idx_base = register_order.index(baseline.register_level)
            distance = abs(idx_cur - idx_base)
            return max(0.3, 1.0 - distance * 0.2)
        except ValueError:
            return 0.5

    # ------------------------------------------------------------------
    # 角色用语检查
    # ------------------------------------------------------------------

    def _check_character_voice(self, query: ProseQuery) -> list[str]:
        """检查角色用语一致性

        检测对话中角色用语是否与其身份/前文一致。
        当前为规则基础版本，Phase 2+ 可升级为 LLM 驱动。

        Args:
            query: 文辞查询

        Returns:
            角色用语问题列表
        """
        issues = []

        # 规则基础：检查同一角色在不同段落中的对话风格是否一致
        import re
        dialogues = re.findall(r'["「]([^"」]{10,})["」]', query.text)

        if len(dialogues) >= 3:
            # 计算各段对话的句长分布
            dialog_lengths = [len(d) for d in dialogues]
            avg_len = sum(dialog_lengths) / len(dialog_lengths)

            # 检测异常长的对话
            for i, (d, length) in enumerate(zip(dialogues, dialog_lengths)):
                if length > avg_len * 2.5 and length > 60:
                    issues.append(
                        f"第 {i+1} 段对话异常长（{length} 字），"
                        f"可能破坏角色对话节奏"
                    )

        return issues

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        metrics: StyleMetrics,
        deviations: list[StyleDeviation],
    ) -> float:
        """计算整体置信度

        Args:
            metrics: 风格指标
            deviations: 风格偏离列表

        Returns:
            整体置信度 0-1
        """
        # LLM 模式下指标值更可信
        if self._llm and self._llm.is_available:
            base = 0.8
            # 偏离越多置信度越低
            penalty = min(len(deviations) * 0.1, 0.5)
            return max(base - penalty, 0.3)

        # Fallback 模式置信度较低
        base = 0.5
        penalty = min(len(deviations) * 0.05, 0.3)
        return max(base - penalty, 0.2)
