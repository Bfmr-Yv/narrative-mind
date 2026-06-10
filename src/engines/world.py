"""
世界引擎 (World Engine) — Phase 1

职责：校验事件是否符合世界观设定（力量体系、空间规则、社会结构等）。

契约（来源：02-CONTRACTS.md）：
- 设定库由人类作者维护，引擎只查询不修改
- 规则冲突时返回 conflict 状态 + 冲突详情，不做自动裁决

依赖：无（只读设定库）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class PowerLevel(Enum):
    """力量等级枚举

    具体等级定义由作者在设定库中维护。
    """

    UNRATED = "unrated"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    CONFLICT = "conflict"  # 规则冲突，需人类裁决


@dataclass
class RuleCheck:
    """单条规则校验结果"""

    rule_name: str
    passed: bool
    detail: str = ""
    conflict_description: Optional[str] = None


@dataclass
class WorldQuery:
    """世界引擎查询输入"""

    event_description: str
    location: str
    involved_characters: list[str] = field(default_factory=list)


@dataclass
class WorldResponse:
    """世界引擎查询输出"""

    rule_checks: list[RuleCheck] = field(default_factory=list)
    spatial_consistency: bool = True
    power_level_validation: PowerLevel = PowerLevel.UNRATED


# ---------------------------------------------------------------------------
# 设定库结构
# ---------------------------------------------------------------------------

@dataclass
class PowerSystemRule:
    """力量体系规则"""

    rule_id: str
    description: str
    condition: str  # 条件描述（人类可读）
    effect: str  # 效果描述


@dataclass
class PowerSystemLevel:
    """力量体系等级"""

    name: str
    capabilities: list[str] = field(default_factory=list)


@dataclass
class PowerSystem:
    """力量体系"""

    name: str
    levels: list[PowerSystemLevel] = field(default_factory=list)
    rules: list[PowerSystemRule] = field(default_factory=list)


@dataclass
class SpatialRule:
    """空间规则"""

    rule_id: str
    description: str
    location: str
    constraint: str


@dataclass
class WorldSettings:
    """世界观设定"""

    power_system: Optional[PowerSystem] = None
    spatial_rules: list[SpatialRule] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 引擎实现
# ---------------------------------------------------------------------------

class WorldEngine:
    """世界引擎 — Phase 1

    校验事件是否符合世界观设定。
    只读设定库，不做自动裁决。
    """

    def __init__(self, llm_client: Optional[object] = None) -> None:
        """初始化世界引擎

        Args:
            llm_client: LLM 客户端实例（可选，未配置时使用关键词 fallback）
        """
        self._settings: Optional[WorldSettings] = None
        self._llm = llm_client
        self._character_power_levels: dict[str, str] = {}  # 角色 -> 力量等级名称

    def load_settings(self, settings_path: str) -> None:
        """加载世界观设定库

        Args:
            settings_path: 设定库文件路径（JSON 格式）

        Raises:
            FileNotFoundError: 当文件不存在时
            json.JSONDecodeError: 当 JSON 格式错误时
        """
        path = Path(settings_path)
        if not path.exists():
            raise FileNotFoundError(f"Settings file not found: {settings_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._settings = self._parse_settings(data)

    def load_character_power_levels(self, levels: dict[str, str]) -> None:
        """加载角色力量等级

        Args:
            levels: 角色 ID 到力量等级名称的映射
        """
        self._character_power_levels.update(levels)

    def validate(self, query: WorldQuery) -> WorldResponse:
        """校验事件是否符合世界观设定

        Args:
            query: 包含事件描述、地点、涉及角色的查询

        Returns:
            WorldResponse: 规则校验结果、空间一致性、力量等级
        """
        if not self._settings:
            # 未加载设定，返回默认响应
            return WorldResponse(
                rule_checks=[],
                spatial_consistency=True,
                power_level_validation=PowerLevel.UNRATED,
            )

        # 执行各项校验
        rule_checks = []

        # 1. 力量体系校验
        power_checks = self._check_power_system(query)
        rule_checks.extend(power_checks)

        # 2. 空间一致性校验
        spatial_ok = self._check_spatial_consistency(query)

        # 3. 汇总力量等级验证结果
        power_level = self._aggregate_power_level(power_checks)

        return WorldResponse(
            rule_checks=rule_checks,
            spatial_consistency=spatial_ok,
            power_level_validation=power_level,
        )

    def _check_power_system(self, query: WorldQuery) -> list[RuleCheck]:
        """校验力量体系规则

        Args:
            query: 世界查询

        Returns:
            规则校验结果列表
        """
        checks = []

        if not self._settings or not self._settings.power_system:
            return checks

        power_system = self._settings.power_system

        # 检查涉及角色的力量等级
        for character_id in query.involved_characters:
            char_level = self._character_power_levels.get(character_id)

            if not char_level:
                checks.append(RuleCheck(
                    rule_name="power_level_unknown",
                    passed=False,
                    detail=f"角色 '{character_id}' 力量等级未知",
                    conflict_description="需要作者设定角色力量等级",
                ))
                continue

            # 检查力量体系规则
            for rule in power_system.rules:
                # 简化版规则检查：基于关键词匹配
                if self._check_rule_applies(rule, query.event_description, char_level):
                    checks.append(RuleCheck(
                        rule_name=rule.rule_id,
                        passed=True,
                        detail=rule.description,
                    ))

        return checks

    def _check_rule_applies(
        self,
        rule: PowerSystemRule,
        event_description: str,
        char_level: str
    ) -> bool:
        """检查规则是否适用

        Fallback 链：LLM 分析 → 关键词匹配

        Args:
            rule: 力量体系规则
            event_description: 事件描述
            char_level: 角色力量等级

        Returns:
            规则是否适用
        """
        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    RULE_CHECK_SYSTEM,
                    format_rule_check_prompt,
                )

                user_message = format_rule_check_prompt(
                    rule_description=rule.description,
                    rule_condition=rule.condition,
                    event_description=event_description,
                    char_level=char_level,
                )

                result = self._llm.call(
                    system_prompt=RULE_CHECK_SYSTEM,
                    user_message=user_message,
                    task_type="rule_check",
                )

                if result and "applies" in result:
                    return bool(result["applies"])
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 关键词匹配 fallback
        keywords = self._extract_keywords(rule.description)
        keywords.update(self._extract_keywords(rule.condition))

        event_lower = event_description.lower()
        desc_lower = rule.description.lower()

        perception_keywords = {"感知", "察觉", "发现", "气息", "探测", "探查"}
        fight_keywords = {"战斗", "攻击", "对抗", "挑战", "决斗", "交手"}

        has_perception = any(kw in event_description for kw in perception_keywords)
        has_fight = any(kw in event_description for kw in fight_keywords)

        rule_about_perception = any(kw in rule.description for kw in perception_keywords)
        rule_about_fight = any(kw in rule.description for kw in fight_keywords)

        if rule_about_perception and has_perception:
            return True
        if rule_about_fight and has_fight:
            return True
        if rule_about_perception or rule_about_fight:
            return False

        for kw in keywords:
            if kw in event_lower or kw in desc_lower:
                return True

        return True  # 默认适用，不作过度过滤

    def _check_spatial_consistency(self, query: WorldQuery) -> bool:
        """校验空间一致性

        只在以下情况标记为不一致：
        1. 地点匹配到已知空间规则，且事件违反了规则约束
        2. 不因为"未知地点"就判定不一致（用户可能有自定义地点）

        Args:
            query: 世界查询

        Returns:
            空间是否一致
        """
        if not self._settings:
            return True

        # 检查空间规则（仅当地点匹配已知规则时才检查）
        location_has_rule = False
        for rule in self._settings.spatial_rules:
            if rule.location == query.location:
                location_has_rule = True
                if not self._check_spatial_rule(rule, query.event_description):
                    return False

        # 如果地点不在已知位置中，也不在已知空间规则中 → 不做判定
        # 用户可能有自定义地点，不应视为冲突
        if not location_has_rule and query.location:
            if self._settings.locations and query.location not in self._settings.locations:
                # 未知地点：不判定为不一致（由 guardian 以 INFO 级别提醒）
                pass

        return True

    def _check_spatial_rule(self, rule: SpatialRule, event_description: str) -> bool:
        """检查空间规则

        Fallback 链：LLM 分析 → 关键词匹配

        Args:
            rule: 空间规则
            event_description: 事件描述

        Returns:
            是否符合规则
        """
        constraint = rule.constraint
        if not constraint:
            return True

        # Tier 1: LLM 分析
        if self._llm and self._llm.is_available:
            try:
                from ..llm.prompts import (
                    SPATIAL_CHECK_SYSTEM,
                    format_spatial_check_prompt,
                )

                user_message = format_spatial_check_prompt(
                    constraint=constraint,
                    rule_description=rule.description,
                    event_description=event_description,
                )

                result = self._llm.call(
                    system_prompt=SPATIAL_CHECK_SYSTEM,
                    user_message=user_message,
                    task_type="spatial_check",
                )

                if result and "consistent" in result:
                    return bool(result["consistent"])
            except Exception:
                pass  # Fall through to fallback

        # Tier 2: 关键词匹配 fallback
        only_walk_keywords = {"马", "车", "轿", "骑", "飞", "船", "坐骑"}
        need_announce_keywords = {"通报", "禀报", "告知", "请示", "通传"}

        constraint_lower = constraint.lower()

        if "步行" in constraint_lower or "只能" in constraint_lower:
            for kw in only_walk_keywords:
                if kw in event_description:
                    return False

        if any(kw in constraint_lower for kw in need_announce_keywords):
            has_announce = any(kw in event_description for kw in need_announce_keywords)
            if not has_announce:
                pass

        return True

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """从文本中提取关键词

        Args:
            text: 输入文本

        Returns:
            关键词集合（小写）
        """
        # 提取中文词汇（2-4 字组合）
        keywords: set[str] = set()
        cleaned = text.lower()

        # 常见力量体系关键词
        power_keywords = [
            "境界", "等级", "感知", "气息", "力量", "能力",
            "战斗", "攻击", "防御", "修行", "突破", "压制",
            "跨境界", "低境界", "高境界",
        ]
        for kw in power_keywords:
            if kw in cleaned:
                keywords.add(kw)

        return keywords

    def _aggregate_power_level(self, checks: list[RuleCheck]) -> PowerLevel:
        """汇总力量等级验证结果

        Args:
            checks: 规则校验结果列表

        Returns:
            汇总后的力量等级
        """
        if not checks:
            return PowerLevel.UNRATED

        # 检查是否有冲突
        has_conflict = any(
            check.conflict_description is not None
            for check in checks
        )

        if has_conflict:
            return PowerLevel.CONFLICT

        # 检查是否全部通过
        all_passed = all(check.passed for check in checks)

        if all_passed:
            return PowerLevel.MEDIUM  # 默认中等
        else:
            return PowerLevel.CONFLICT

    def _parse_settings(self, data: dict) -> WorldSettings:
        """解析设定库数据

        Args:
            data: 设定库字典数据

        Returns:
            WorldSettings 实例
        """
        settings = WorldSettings()

        # 解析力量体系
        settings_data = data.get("power_system")
        if settings_data:
            power_system = PowerSystem(
                name=settings_data.get("name", ""),
            )

            # 解析等级
            for level_data in settings_data.get("levels", []):
                level = PowerSystemLevel(
                    name=level_data.get("name", ""),
                    capabilities=level_data.get("capabilities", []),
                )
                power_system.levels.append(level)

            # 解析规则
            for rule_data in settings_data.get("rules", []):
                rule = PowerSystemRule(
                    rule_id=rule_data.get("id", ""),
                    description=rule_data.get("desc", ""),
                    condition=rule_data.get("condition", ""),
                    effect=rule_data.get("effect", ""),
                )
                power_system.rules.append(rule)

            settings.power_system = power_system

        # 解析空间规则
        for rule_data in data.get("spatial_rules", []):
            rule = SpatialRule(
                rule_id=rule_data.get("id", ""),
                description=rule_data.get("desc", ""),
                location=rule_data.get("location", ""),
                constraint=rule_data.get("constraint", ""),
            )
            settings.spatial_rules.append(rule)

        # 解析已知位置
        settings.locations = data.get("locations", [])

        return settings
