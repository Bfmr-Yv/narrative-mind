"""
一致性守卫 (Consistency Guardian) — Phase 1

职责：交叉验证引擎输出，检测冲突，决定是否允许写入记忆。

契约（来源：06-CONSISTENCY-GUARDIAN.md）：
- Phase 1 激活 3 维：角色行为、世界规则、空间一致
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
        "character", "world_rule", "spatial"
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
    """一致性守卫 — Phase 1

    交叉验证引擎输出，检测冲突。
    Phase 1 仅检查 3 个维度：角色行为、世界规则、空间一致。
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
        else:
            # Phase 2+ 维度，暂不实现
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
