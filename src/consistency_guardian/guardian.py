"""
一致性守卫 (Consistency Guardian) — Phase 2

职责：交叉验证引擎输出，检测冲突，决定是否允许写入记忆。

契约（来源：06-CONSISTENCY-GUARDIAN.md）：
- Phase 1 激活 3 维：角色行为、世界规则、空间一致
- Phase 2 新增 3 维：伏笔回收、因果逻辑、叙事一致
- 守卫返回 CRITICAL → 阻断记忆写入，返回冲突报告
- 守卫返回 WARN → 写入记忆 + 附带提醒标记
- 守卫通过 → 正常写入记忆
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class AlarmLevel(Enum):
    """警报级别"""
    INFO = "info"      # 提醒，无冲突
    WARN = "warn"      # 软冲突，可能是创作意图
    CRITICAL = "critical"  # 硬冲突，必须处理


class ActionRequired(Enum):
    """所需动作"""
    NONE = "none"      # 无需操作
    REVIEW = "review"  # 建议审查
    BLOCK = "block"    # 阻断流程


@dataclass
class Conflict:
    """冲突详情"""
    dimension: str  # 检查维度
    level: AlarmLevel
    detail: str
    suggestion: Optional[str] = None


@dataclass
class DimensionResult:
    """单维度检查结果"""
    dimension: str
    passed: bool
    conflicts: list[Conflict] = field(default_factory=list)


@dataclass
class GuardianInput:
    """守卫输入"""
    engine_results: dict[str, Any]  # 各引擎的返回结果
    active_dimensions: list[str] = field(default_factory=lambda: [
        "character", "world_rule", "spatial",
        "foreshadowing", "causal", "narrative_consistency",  # Phase 2
    ])


@dataclass
class GuardianOutput:
    """守卫输出"""
    is_consistent: bool
    dimension_results: dict[str, DimensionResult]
    alarm_level: AlarmLevel
    conflicts: list[Conflict]
    action_required: ActionRequired


# ---------------------------------------------------------------------------
# 守卫实现
# ---------------------------------------------------------------------------

class ConsistencyGuardian:
    """一致性守卫 — Phase 2

    交叉验证引擎输出，检测冲突。
    Phase 1: 角色行为、世界规则、空间一致（3 维）
    Phase 2: +伏笔回收、因果逻辑、叙事一致（6 维）
    """

    def __init__(self) -> None:
        """初始化守卫"""
        pass

    def check(self, input_data: GuardianInput) -> GuardianOutput:
        """执行一致性检查

        Args:
            input_data: 守卫输入（引擎结果 + 激活维度）

        Returns:
            GuardianOutput: 检查结果、冲突详情、警报级别
        """
        dimension_results: dict[str, DimensionResult] = {}
        all_conflicts: list[Conflict] = []

        # 检查每个激活维度
        for dimension in input_data.active_dimensions:
            result = self._check_dimension(
                dimension,
                input_data.engine_results
            )
            dimension_results[dimension] = result
            all_conflicts.extend(result.conflicts)

        # 确定最高警报级别
        alarm_level = self._determine_alarm_level(all_conflicts)

        # 确定所需动作
        action_required = self._determine_action(alarm_level)

        # 整体是否一致
        is_consistent = alarm_level != AlarmLevel.CRITICAL

        return GuardianOutput(
            is_consistent=is_consistent,
            dimension_results=dimension_results,
            alarm_level=alarm_level,
            conflicts=all_conflicts,
            action_required=action_required,
        )

    def _check_dimension(
        self,
        dimension: str,
        engine_results: dict[str, Any]
    ) -> DimensionResult:
        """检查单个维度

        Args:
            dimension: 维度名称
            engine_results: 引擎结果

        Returns:
            DimensionResult: 维度检查结果
        """
        if dimension == "character":
            return self._check_character(engine_results)
        elif dimension == "world_rule":
            return self._check_world_rule(engine_results)
        elif dimension == "spatial":
            return self._check_spatial(engine_results)
        elif dimension == "foreshadowing":
            return self._check_foreshadowing(engine_results)
        elif dimension == "causal":
            return self._check_causal(engine_results)
        elif dimension == "narrative_consistency":
            return self._check_narrative_consistency(engine_results)
        else:
            # Phase 3+ 维度，暂不实现
            return DimensionResult(
                dimension=dimension,
                passed=True,
                conflicts=[],
            )

    def _check_character(self, engine_results: dict[str, Any]) -> DimensionResult:
        """检查角色行为一致性

        Args:
            engine_results: 引擎结果

        Returns:
            DimensionResult: 角色维度检查结果
        """
        conflicts = []
        character_result = engine_results.get("character_engine")

        if character_result:
            # 检查置信度
            confidence = getattr(character_result, "confidence", 1.0)
            if confidence < 0.5:
                conflicts.append(Conflict(
                    dimension="character",
                    level=AlarmLevel.WARN,
                    detail=f"角色行为预测置信度过低 ({confidence:.2f})",
                    suggestion="建议人工审查该角色的行为是否合理",
                ))

            # 检查是否需要人工审核
            needs_review = getattr(character_result, "needs_human_review", False)
            if needs_review:
                conflicts.append(Conflict(
                    dimension="character",
                    level=AlarmLevel.WARN,
                    detail="角色引擎标记为需要人工审查",
                    suggestion="请检查角色行为是否符合预期",
                ))

        return DimensionResult(
            dimension="character",
            passed=len(conflicts) == 0,
            conflicts=conflicts,
        )

    def _check_world_rule(self, engine_results: dict[str, Any]) -> DimensionResult:
        """检查世界规则一致性

        Args:
            engine_results: 引擎结果

        Returns:
            DimensionResult: 世界规则维度检查结果
        """
        conflicts = []
        world_result = engine_results.get("world_engine")

        if world_result:
            # 检查规则校验结果
            rule_checks = getattr(world_result, "rule_checks", [])
            for check in rule_checks:
                if not getattr(check, "passed", True):
                    conflict_desc = getattr(check, "conflict_description", None)
                    level = AlarmLevel.CRITICAL if conflict_desc else AlarmLevel.WARN
                    conflicts.append(Conflict(
                        dimension="world_rule",
                        level=level,
                        detail=f"规则 '{getattr(check, 'rule_name', 'unknown')}' 未通过: {getattr(check, 'detail', '')}",
                        suggestion=conflict_desc,
                    ))

            # 检查力量等级验证
            power_level = getattr(world_result, "power_level_validation", None)
            if power_level and hasattr(power_level, "value"):
                if power_level.value == "conflict":
                    conflicts.append(Conflict(
                        dimension="world_rule",
                        level=AlarmLevel.CRITICAL,
                        detail="力量等级验证冲突",
                        suggestion="需要作者裁决力量等级是否合理",
                    ))

        return DimensionResult(
            dimension="world_rule",
            passed=len(conflicts) == 0,
            conflicts=conflicts,
        )

    def _check_spatial(self, engine_results: dict[str, Any]) -> DimensionResult:
        """检查空间一致性

        Args:
            engine_results: 引擎结果

        Returns:
            DimensionResult: 空间维度检查结果
        """
        conflicts = []
        world_result = engine_results.get("world_engine")

        if world_result:
            # 检查空间一致性
            spatial_ok = getattr(world_result, "spatial_consistency", True)
            if not spatial_ok:
                conflicts.append(Conflict(
                    dimension="spatial",
                    level=AlarmLevel.WARN,
                    detail="空间一致性检查未通过",
                    suggestion="请检查地点是否正确或添加到设定库",
                ))

        return DimensionResult(
            dimension="spatial",
            passed=len(conflicts) == 0,
            conflicts=conflicts,
        )

    # ------------------------------------------------------------------
    # Phase 2 维度
    # ------------------------------------------------------------------

    def _check_foreshadowing(self, engine_results: dict[str, Any]) -> DimensionResult:
        """检查伏笔回收一致性 (Phase 2)

        检查叙事引擎输出的伏笔状态：
        1. 长期未回收伏笔过多 → WARN
        2. 伏笔检测置信度过低 → WARN
        3. 叙事引擎整体置信度过低 → CRITICAL

        Args:
            engine_results: 引擎结果

        Returns:
            DimensionResult: 伏笔维度检查结果
        """
        conflicts = []
        narrative_result = engine_results.get("narrative_engine")

        if narrative_result:
            # 检查叙事引擎整体置信度
            confidence = getattr(narrative_result, "confidence", 1.0)
            if confidence < 0.3:
                conflicts.append(Conflict(
                    dimension="foreshadowing",
                    level=AlarmLevel.CRITICAL,
                    detail=f"叙事引擎置信度过低 ({confidence:.2f})，伏笔分析可能不可靠",
                    suggestion="建议人工审查本章叙事元素",
                ))
            elif confidence < 0.5:
                conflicts.append(Conflict(
                    dimension="foreshadowing",
                    level=AlarmLevel.WARN,
                    detail=f"叙事引擎置信度偏低 ({confidence:.2f})",
                    suggestion="伏笔检测结果仅供参考",
                ))

            # 检查未回收伏笔数量
            unresolved = getattr(narrative_result, "unresolved_foreshadowings", []) or []
            if len(unresolved) >= 5:
                conflicts.append(Conflict(
                    dimension="foreshadowing",
                    level=AlarmLevel.WARN,
                    detail=f"有 {len(unresolved)} 个伏笔长期未回收，可能被遗忘",
                    suggestion=f"考虑在近期章节回收或确认以下伏笔是否已废弃: "
                              f"{', '.join(fs.description[:20] for fs in unresolved[:3] if hasattr(fs, 'description'))}",
                ))

            # 检查伏笔类型集中度
            foreshadowings = getattr(narrative_result, "foreshadowings", []) or []
            categories = [getattr(fs, "category", "unknown") for fs in foreshadowings]
            for cat in ("object", "character", "event"):
                if categories.count(cat) >= 3:
                    conflicts.append(Conflict(
                        dimension="foreshadowing",
                        level=AlarmLevel.WARN,
                        detail=f"'{cat}' 类伏笔集中出现 {categories.count(cat)} 次",
                        suggestion="避免过度依赖同一类型的伏笔手法",
                    ))
                    break

        return DimensionResult(
            dimension="foreshadowing",
            passed=len(conflicts) == 0,
            conflicts=conflicts,
        )

    def _check_causal(self, engine_results: dict[str, Any]) -> DimensionResult:
        """检查因果逻辑一致性 (Phase 2)

        检查叙事引擎输出的因果链质量：
        1. 因果链强度普遍过低 → WARN
        2. 检测到叙事问题中的因果循环 → CRITICAL

        Args:
            engine_results: 引擎结果

        Returns:
            DimensionResult: 因果维度检查结果
        """
        conflicts = []
        narrative_result = engine_results.get("narrative_engine")

        if narrative_result:
            # 检查因果链强度
            causal_links = getattr(narrative_result, "causal_links", []) or []
            if causal_links:
                avg_strength = sum(
                    getattr(link, "strength", 0.5) for link in causal_links
                ) / len(causal_links)
                if avg_strength < 0.3:
                    conflicts.append(Conflict(
                        dimension="causal",
                        level=AlarmLevel.WARN,
                        detail=f"因果链平均强度过低 ({avg_strength:.2f})，事件间因果关系较弱",
                        suggestion="检查章节事件间的逻辑连接是否充分",
                    ))

            # 检查叙事问题中是否有因果相关告警
            issues = getattr(narrative_result, "narrative_issues", []) or []
            for issue in issues:
                if "因果循环" in str(issue):
                    conflicts.append(Conflict(
                        dimension="causal",
                        level=AlarmLevel.CRITICAL,
                        detail=str(issue),
                        suggestion="需要作者梳理事件因果顺序，打破循环依赖",
                    ))
                elif "因果" in str(issue):
                    conflicts.append(Conflict(
                        dimension="causal",
                        level=AlarmLevel.WARN,
                        detail=str(issue),
                        suggestion="建议审查因果关系是否合理",
                    ))

            # 无因果链但有叙事事件 → 可能遗漏
            if not causal_links and getattr(narrative_result, "event_prediction", ""):
                conflicts.append(Conflict(
                    dimension="causal",
                    level=AlarmLevel.WARN,
                    detail="叙事引擎未提取到因果链，但检测到情节事件",
                    suggestion="章节可能缺少明确的事件因果连接",
                ))

        return DimensionResult(
            dimension="causal",
            passed=len(conflicts) == 0,
            conflicts=conflicts,
        )

    def _check_narrative_consistency(self, engine_results: dict[str, Any]) -> DimensionResult:
        """检查叙事整体一致性 (Phase 2)

        交叉验证叙事引擎与其他引擎输出：
        1. 叙事引擎 vs 角色引擎：角色行为是否与情节推演一致
        2. 叙事引擎 needs_human_review 标记

        Args:
            engine_results: 引擎结果

        Returns:
            DimensionResult: 叙事一致性检查结果
        """
        conflicts = []
        narrative_result = engine_results.get("narrative_engine")
        character_result = engine_results.get("character_engine")

        if narrative_result:
            # 检查是否需要人工审查
            needs_review = getattr(narrative_result, "needs_human_review", False)
            if needs_review:
                conflicts.append(Conflict(
                    dimension="narrative_consistency",
                    level=AlarmLevel.WARN,
                    detail="叙事引擎标记为需要人工审查",
                    suggestion="请检查叙事分析结果（伏笔、因果链、情节推演）是否符合预期",
                ))

        # 交叉验证：叙事引擎和角色引擎都有结果时
        if narrative_result and character_result:
            n_confidence = getattr(narrative_result, "confidence", 0.5)
            c_confidence = getattr(character_result, "confidence", 0.5)

            # 两者置信度都低 → 数据质量存疑
            if n_confidence < 0.4 and c_confidence < 0.4:
                conflicts.append(Conflict(
                    dimension="narrative_consistency",
                    level=AlarmLevel.CRITICAL,
                    detail=f"叙事引擎 ({n_confidence:.2f}) 和角色引擎 ({c_confidence:.2f}) 置信度均偏低",
                    suggestion="当前章节文本可能过短或质量不足以支撑可靠分析",
                ))

            # 叙事置信度显著低于角色 → 叙事结构可能有问题
            elif n_confidence < 0.4 and c_confidence > 0.6:
                conflicts.append(Conflict(
                    dimension="narrative_consistency",
                    level=AlarmLevel.WARN,
                    detail=f"角色行为分析置信度较高 ({c_confidence:.2f})，"
                           f"但叙事分析置信度偏低 ({n_confidence:.2f})",
                    suggestion="角色行为合理但章节叙事结构可能需要加强",
                ))

        return DimensionResult(
            dimension="narrative_consistency",
            passed=len(conflicts) == 0,
            conflicts=conflicts,
        )

    # ------------------------------------------------------------------
    # 警报判定
    # ------------------------------------------------------------------

    def _determine_alarm_level(self, conflicts: list[Conflict]) -> AlarmLevel:
        """确定最高警报级别

        Args:
            conflicts: 所有冲突列表

        Returns:
            AlarmLevel: 最高警报级别
        """
        if not conflicts:
            return AlarmLevel.INFO

        # 检查是否有 CRITICAL
        has_critical = any(
            c.level == AlarmLevel.CRITICAL for c in conflicts
        )
        if has_critical:
            return AlarmLevel.CRITICAL

        # 检查是否有 WARN
        has_warn = any(
            c.level == AlarmLevel.WARN for c in conflicts
        )
        if has_warn:
            return AlarmLevel.WARN

        return AlarmLevel.INFO

    def _determine_action(self, alarm_level: AlarmLevel) -> ActionRequired:
        """确定所需动作

        Args:
            alarm_level: 警报级别

        Returns:
            ActionRequired: 所需动作
        """
        if alarm_level == AlarmLevel.CRITICAL:
            return ActionRequired.BLOCK
        elif alarm_level == AlarmLevel.WARN:
            return ActionRequired.REVIEW
        else:
            return ActionRequired.NONE
