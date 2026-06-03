"""
编辑后验证器（自检清单后置双保险）

职责：
1. 重复行检测（基于 10-AGENT-CONSTRAINTS.md 的重复预防硬规则）
2. 日期格式检查（YYYY-MM-DD）
3. 成本数字自洽检查（与 04-COST-BUDGET.md 交叉核对）

本模块是自检清单的后置双保险，不替代写入前的主动检查。
"""

from __future__ import annotations

import re
import sys
import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ValidationLevel(Enum):
    """验证级别"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class DuplicateLine:
    """重复行详情"""
    line_number: int
    content: str
    count: int


@dataclass
class DateFormatIssue:
    """日期格式问题"""
    line_number: int
    found_date: str
    expected_format: str


@dataclass
class CostInconsistency:
    """成本数字不一致"""
    line_number: int
    found_value: str
    expected_range: str
    context: str


@dataclass
class ValidationResult:
    """验证结果"""
    level: ValidationLevel
    duplicate_lines: list[DuplicateLine]
    date_format_issues: list[DateFormatIssue]
    cost_inconsistencies: list[CostInconsistency]
    summary: str
    warnings: list[str]


# 成本预算参考值（来源：04-COST-BUDGET.md）
COST_REFERENCE = {
    "tier_0": {"cost_per_call": 0, "monthly_quota": "unlimited"},
    "tier_1": {"cost_per_call": 0, "monthly_quota": "unlimited"},
    "tier_2": {"cost_per_call": 0.05, "monthly_quota": 300},
    "tier_3": {"cost_per_call": 0.20, "monthly_quota": 75},
    "tier_4": {"cost_per_call": 1.00, "monthly_quota": 15},
    "monthly_limit": 20,
}

# 错误日期格式正则（匹配 YYYY/MM/DD、YYYY.MM.DD、DD/MM/YYYY、DD.MM.YYYY、YY/MM/DD 等）
BAD_DATE_PATTERN = re.compile(r'\b(?:\d{4}[\/\.]\d{2}[\/\.]\d{2}|\d{2}[\/\.]\d{2}[\/\.]\d{4}|\d{2}[\/\.]\d{2}[\/\.]\d{2})\b')


def check_duplicate_lines(content: str) -> list[DuplicateLine]:
    """
    检测连续重复行

    Args:
        content: 待检查的文本内容

    Returns:
        重复行列表
    """
    lines = content.split('\n')
    duplicates = []

    # 检测连续重复行
    i = 0
    while i < len(lines) - 1:
        current_line = lines[i].strip()
        if not current_line:  # 跳过空行
            i += 1
            continue

        count = 1
        j = i + 1
        while j < len(lines) and lines[j].strip() == current_line:
            count += 1
            j += 1

        if count > 1:
            duplicates.append(DuplicateLine(
                line_number=i + 1,
                content=current_line,
                count=count
            ))
            i = j
        else:
            i += 1

    return duplicates


def check_date_format(content: str) -> list[DateFormatIssue]:
    """
    检查日期格式是否为 YYYY-MM-DD（检测错误格式）

    Args:
        content: 待检查的文本内容

    Returns:
        日期格式问题列表
    """
    lines = content.split('\n')
    issues = []

    for line_num, line in enumerate(lines, 1):
        matches = BAD_DATE_PATTERN.findall(line)
        for date_str in matches:
            issues.append(DateFormatIssue(
                line_number=line_num,
                found_date=date_str,
                expected_format="YYYY-MM-DD"
            ))

    return issues


def check_cost_numbers(content: str) -> list[CostInconsistency]:
    """
    检查成本数字是否与预算文档一致

    Args:
        content: 待检查的文本内容

    Returns:
        成本不一致问题列表
    """
    lines = content.split('\n')
    inconsistencies = []

    # 匹配 Tier X: $Y.YY 格式
    tier_pattern = re.compile(r'Tier\s*(\d)\s*[:：]\s*\$(\d+\.?\d*)', re.IGNORECASE)
    # 匹配月度预算 $XX 格式
    monthly_pattern = re.compile(r'(?:月度|monthly)\s*(?:预算|budget|limit)\s*[:：]?\s*\$(\d+)', re.IGNORECASE)

    for line_num, line in enumerate(lines, 1):
        # 检查 Tier 成本
        tier_matches = tier_pattern.findall(line)
        for tier_num, cost in tier_matches:
            tier_key = f"tier_{tier_num}"
            if tier_key in COST_REFERENCE:
                expected = COST_REFERENCE[tier_key]["cost_per_call"]
                found = float(cost)
                if abs(found - expected) > 0.01:  # 允许小误差
                    inconsistencies.append(CostInconsistency(
                        line_number=line_num,
                        found_value=f"${found}",
                        expected_range=f"${expected}",
                        context=f"Tier {tier_num} 单次调用成本"
                    ))

        # 检查月度预算
        monthly_matches = monthly_pattern.findall(line)
        for budget in monthly_matches:
            found = int(budget)
            expected = COST_REFERENCE["monthly_limit"]
            if found != expected:
                inconsistencies.append(CostInconsistency(
                    line_number=line_num,
                    found_value=f"${found}",
                    expected_range=f"${expected}",
                    context="月度预算上限"
                ))

    return inconsistencies


def validate_content(
    content: str,
    check_duplicates: bool = True,
    check_dates: bool = True,
    check_costs: bool = True
) -> ValidationResult:
    """
    执行完整的编辑后验证

    Args:
        content: 待验证的文本内容
        check_duplicates: 是否检查重复行
        check_dates: 是否检查日期格式
        check_costs: 是否检查成本数字

    Returns:
        验证结果
    """
    duplicates = []
    date_issues = []
    cost_issues = []
    warnings = []

    if check_duplicates:
        duplicates = check_duplicate_lines(content)
        if duplicates:
            warnings.append(f"发现 {len(duplicates)} 处连续重复行")

    if check_dates:
        date_issues = check_date_format(content)
        if date_issues:
            warnings.append(f"发现 {len(date_issues)} 处日期格式问题")

    if check_costs:
        cost_issues = check_cost_numbers(content)
        if cost_issues:
            warnings.append(f"发现 {len(cost_issues)} 处成本数字不一致")

    # 确定验证级别
    has_failures = len(cost_issues) > 0
    has_warnings = len(duplicates) > 0 or len(date_issues) > 0

    if has_failures:
        level = ValidationLevel.FAIL
    elif has_warnings:
        level = ValidationLevel.WARN
    else:
        level = ValidationLevel.PASS

    # 生成摘要
    if not warnings:
        summary = "验证通过，无问题"
    else:
        summary = "；".join(warnings)

    return ValidationResult(
        level=level,
        duplicate_lines=duplicates,
        date_format_issues=date_issues,
        cost_inconsistencies=cost_issues,
        summary=summary,
        warnings=warnings
    )


def format_validation_report(result: ValidationResult) -> str:
    """
    格式化验证结果为可读报告

    Args:
        result: 验证结果

    Returns:
        格式化的报告字符串
    """
    lines = [
        "# 编辑后验证报告",
        "",
        f"**状态**: {result.level.value.upper()}",
        f"**摘要**: {result.summary}",
        "",
    ]

    if result.duplicate_lines:
        lines.append("## 连续重复行")
        lines.append("")
        for dup in result.duplicate_lines:
            lines.append(f"- 第 {dup.line_number} 行（重复 {dup.count} 次）：`{dup.content[:50]}...`")
        lines.append("")

    if result.date_format_issues:
        lines.append("## 日期格式问题")
        lines.append("")
        for issue in result.date_format_issues:
            lines.append(f"- 第 {issue.line_number} 行：发现 `{issue.found_date}`，应为 {issue.expected_format}")
        lines.append("")

    if result.cost_inconsistencies:
        lines.append("## 成本数字不一致")
        lines.append("")
        for issue in result.cost_inconsistencies:
            lines.append(f"- 第 {issue.line_number} 行：{issue.context}")
            lines.append(f"  发现: {issue.found_value}，预期: {issue.expected_range}")
        lines.append("")

    if result.warnings:
        lines.append("## 警告")
        lines.append("")
        for warning in result.warnings:
            lines.append(f"- [!] {warning}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    with open(args.file, 'r', encoding='utf-8') as f:
        content = f.read()
    result = validate_content(content)
    print(format_validation_report(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
