"""
Narrative Mind v3.1 — Consistency Guardian Package

Phase 1 简化版：八维检查中仅激活前 3 维（character, world_rule, spatial）

包含：
- naming_phase_guard.py: 命名+Phase 边界守卫（Pre-edit）
- guardian.py: 一致性守卫主逻辑（待创建）
- dimensions.py: 检查维度定义（待创建）
"""

from .naming_phase_guard import (
    AlarmLevel,
    ActionType,
    GuardResult,
    NamingViolation,
    PhaseViolation,
    check_naming,
    check_phase_boundary,
    format_report,
    run_guard,
)

__all__ = [
    "AlarmLevel",
    "ActionType",
    "GuardResult",
    "NamingViolation",
    "PhaseViolation",
    "check_naming",
    "check_phase_boundary",
    "format_report",
    "run_guard",
]
