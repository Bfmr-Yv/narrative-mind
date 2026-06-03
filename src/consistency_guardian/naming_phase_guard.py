"""
命名+Phase 补充维度守卫

职责：
1. 命名冻结检查（基于 02-CONTRACTS.md 和 10-AGENT-CONSTRAINTS.md）
2. Phase 边界检查（基于 08-MVP-ROADMAP.md）

本模块是一致性守卫的补充维度，不替代八维检查。
"""

from __future__ import annotations

import re
import sys
import argparse
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AlarmLevel(Enum):
    """三级警报"""
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class ActionType(Enum):
    """处理动作"""
    NONE = "none"
    REVIEW = "review"
    BLOCK = "block"


@dataclass
class NamingViolation:
    """命名违规详情"""
    deprecated_name: str
    correct_name: str
    location: str
    context: str


@dataclass
class PhaseViolation:
    """Phase 边界违规详情"""
    module_name: str
    required_phase: str
    current_phase: str
    location: str


@dataclass
class GuardResult:
    """守卫检查结果"""
    is_valid: bool
    alarm_level: AlarmLevel
    action_required: ActionType
    naming_violations: list[NamingViolation]
    phase_violations: list[PhaseViolation]
    summary: str


# 命名冻结表（来源：10-AGENT-CONSTRAINTS.md）
FROZEN_NAMING_TABLE = {
    # 中文名 -> 英文名
    "角色引擎": "Character Engine",
    "世界引擎": "World Engine",
    "语料锚定层": "Corpus Anchor",
    "级联修正器": "Cascade Fixer",
    "编排器": "Orchestrator",
    "叙事引擎": "Narrative Engine",
    "文辞引擎": "Prose Engine",
    "主题引擎": "Theme Engine",
    "经济引擎": "Economy Engine",
    "读者预期引擎": "Reader Expectation Engine",
    "构思引擎": "Conception Engine",
}

# 废弃名称映射（来源：10-AGENT-CONSTRAINTS.md）
DEPRECATED_NAMES = {
    "Style Engine": "Prose Engine",
    "Impact Radar": "Cascade Fixer",
    "影响雷达": "级联修正器",
    "风格引擎": "文辞引擎",
}

# Phase 边界定义（来源：08-MVP-ROADMAP.md）
PHASE_BOUNDARIES = {
    "Phase 1": {
        "active_engines": ["character_engine", "world_engine"],
        "active_dimensions": ["character", "world_rule", "spatial"],
        "excluded_engines": [
            "narrative_engine", "prose_engine", "theme_engine",
            "economy_engine", "reader_expectation_engine", "conception_engine"
        ],
    },
    "Phase 2": {
        "active_engines": [
            "character_engine", "world_engine", "narrative_engine", "prose_engine"
        ],
        "active_dimensions": [
            "character", "world_rule", "spatial", "temporal",
            "power", "relationship", "causality", "style"
        ],
        "excluded_engines": [
            "theme_engine", "economy_engine",
            "reader_expectation_engine", "conception_engine"
        ],
    },
    "Phase 3": {
        "active_engines": [
            "character_engine", "world_engine", "narrative_engine",
            "prose_engine", "theme_engine", "economy_engine",
            "reader_expectation_engine", "conception_engine"
        ],
        "active_dimensions": [
            "character", "world_rule", "spatial", "temporal",
            "power", "relationship", "causality", "style"
        ],
        "excluded_engines": [],
    },
}


def check_naming(text: str, location: str = "unknown") -> list[NamingViolation]:
    """
    检查文本中的命名违规

    Args:
        text: 待检查文本
        location: 文本位置标识

    Returns:
        命名违规列表
    """
    violations = []

    for deprecated, correct in DEPRECATED_NAMES.items():
        # 大小写不敏感匹配
        pattern = re.compile(re.escape(deprecated), re.IGNORECASE)
        matches = pattern.findall(text)

        if matches:
            violations.append(NamingViolation(
                deprecated_name=deprecated,
                correct_name=correct,
                location=location,
                context=f"发现 {len(matches)} 处废弃名称使用"
            ))

    return violations


def check_phase_boundary(
    module_name: str,
    current_phase: str,
    location: str = "unknown"
) -> Optional[PhaseViolation]:
    """
    检查模块是否在当前 Phase 允许范围内

    Args:
        module_name: 模块名称（如 "theme_engine"）
        current_phase: 当前 Phase（如 "Phase 1"）
        location: 检查位置标识

    Returns:
        如果违规返回 PhaseViolation，否则返回 None
    """
    if current_phase not in PHASE_BOUNDARIES:
        return None

    phase_config = PHASE_BOUNDARIES[current_phase]
    excluded = phase_config["excluded_engines"]

    if module_name in excluded:
        # 确定该模块需要的最低 Phase
        required_phase = "Phase 2+"
        for phase_name, config in PHASE_BOUNDARIES.items():
            if module_name not in config["excluded_engines"]:
                required_phase = phase_name
                break

        return PhaseViolation(
            module_name=module_name,
            required_phase=required_phase,
            current_phase=current_phase,
            location=location
        )

    return None


def run_guard(
    text: str,
    current_phase: str = "Phase 1",
    location: str = "unknown"
) -> GuardResult:
    """
    执行命名+Phase 守卫检查

    Args:
        text: 待检查文本
        current_phase: 当前 Phase
        location: 文本位置标识

    Returns:
        守卫检查结果
    """
    # 1. 命名检查
    naming_violations = check_naming(text, location)

    # 2. Phase 边界检查
    phase_violations = []
    phase_config = PHASE_BOUNDARIES.get(current_phase, {})
    excluded_engines = phase_config.get("excluded_engines", [])

    for engine in excluded_engines:
        # 检查文本中是否引用了被排除的引擎
        engine_pattern = re.compile(re.escape(engine), re.IGNORECASE)
        if engine_pattern.search(text):
            violation = check_phase_boundary(engine, current_phase, location)
            if violation:
                phase_violations.append(violation)

    # 3. 确定警报级别和处理动作
    has_naming_violations = len(naming_violations) > 0
    has_phase_violations = len(phase_violations) > 0

    if has_naming_violations or has_phase_violations:
        is_valid = False
        if has_phase_violations:
            alarm_level = AlarmLevel.CRITICAL
            action_required = ActionType.BLOCK
        else:
            alarm_level = AlarmLevel.WARN
            action_required = ActionType.REVIEW
    else:
        is_valid = True
        alarm_level = AlarmLevel.INFO
        action_required = ActionType.NONE

    # 4. 生成摘要
    summary_parts = []
    if naming_violations:
        summary_parts.append(f"发现 {len(naming_violations)} 处命名违规")
    if phase_violations:
        summary_parts.append(f"发现 {len(phase_violations)} 处 Phase 边界违规")
    if not summary_parts:
        summary_parts.append("检查通过，无违规")

    summary = "；".join(summary_parts)

    return GuardResult(
        is_valid=is_valid,
        alarm_level=alarm_level,
        action_required=action_required,
        naming_violations=naming_violations,
        phase_violations=phase_violations,
        summary=summary
    )


def format_report(result: GuardResult) -> str:
    """
    格式化检查结果为可读报告

    Args:
        result: 守卫检查结果

    Returns:
        格式化的报告字符串
    """
    lines = [
        "# 命名+Phase 守卫检查报告",
        "",
        f"**状态**: {'通过' if result.is_valid else '不通过'}",
        f"**警报级别**: {result.alarm_level.value}",
        f"**处理动作**: {result.action_required.value}",
        f"**摘要**: {result.summary}",
        "",
    ]

    if result.naming_violations:
        lines.append("## 命名违规")
        lines.append("")
        for v in result.naming_violations:
            lines.append(f"- [X] `{v.deprecated_name}` -> `{v.correct_name}`")
            lines.append(f"  位置: {v.location}")
            lines.append(f"  详情: {v.context}")
        lines.append("")

    if result.phase_violations:
        lines.append("## Phase 边界违规")
        lines.append("")
        for v in result.phase_violations:
            lines.append(f"- [X] `{v.module_name}` 不允许在 {v.current_phase} 使用")
            lines.append(f"  需要: {v.required_phase}")
            lines.append(f"  位置: {v.location}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--content", required=True)
    args = parser.parse_args()
    result = run_guard(args.content, current_phase="Phase 1", location=args.file)
    print(format_report(result))
    sys.exit(0 if result.is_valid else 1)

if __name__ == "__main__":
    main()
