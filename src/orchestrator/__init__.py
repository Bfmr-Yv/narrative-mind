"""
Narrative Mind v3.1 — Orchestrator Package

Phase 1 简化版：事件路由 + 引擎调度 + 降级策略

唯一有记忆写入权限的模块。

包含：
- post_edit_validator.py: 编辑后验证器（Post-edit）
- router.py: 事件路由（待创建）
- scheduler.py: 引擎调度（待创建）
- fallback.py: 降级策略（待创建）
"""

from .post_edit_validator import (
    ValidationLevel,
    ValidationResult,
    CostInconsistency,
    DateFormatIssue,
    DuplicateLine,
    check_duplicate_lines,
    check_date_format,
    check_cost_numbers,
    format_validation_report,
    validate_content,
)

__all__ = [
    "ValidationLevel",
    "ValidationResult",
    "CostInconsistency",
    "DateFormatIssue",
    "DuplicateLine",
    "check_duplicate_lines",
    "check_date_format",
    "check_cost_numbers",
    "format_validation_report",
    "validate_content",
]
