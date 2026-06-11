"""
成本追踪器 — Phase 1

职责：月度预算 $20 硬熔断，三层降级机制。
持久化到 config/cost-log.json，每月自动重置。

三层熔断（来源：04-COST-BUDGET.md）：
- 50% ($10): 警告，正常使用
- 80% ($16): 仅关键任务（action_infer, rule_check）
- 95% ($19): 全阻断
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import (
    MONTHLY_BUDGET_USD,
    MELTDOWN_WARN_RATIO,
    MELTDOWN_RESTRICT_RATIO,
    MELTDOWN_BLOCK_RATIO,
    CRITICAL_TASK_TYPES,
    ESTIMATED_COST_PER_CALL,
)


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class BudgetExceededError(Exception):
    """预算超限异常 — 调用方 catch 后走 fallback"""
    pass


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class CallRecord:
    """单次调用记录"""
    timestamp: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost: float


@dataclass
class MonthlyLog:
    """月度成本日志"""
    month: str  # "2026-06"
    total_spent: float = 0.0
    call_count: int = 0
    by_task_type: dict[str, float] = field(default_factory=dict)
    calls: list[CallRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 成本追踪器
# ---------------------------------------------------------------------------

class CostTracker:
    """月度预算追踪器 — $20 硬熔断"""

    def __init__(self, log_path: str = "config/cost-log.json") -> None:
        """初始化成本追踪器

        Args:
            log_path: 成本日志文件路径
        """
        self._log_path = Path(log_path)
        self._log: MonthlyLog = self._load_or_reset()

    def check_before_call(self, task_type: str) -> bool:
        """调用前检查预算

        Args:
            task_type: 任务类型（对应 TIER_CONFIG 的 key）

        Returns:
            True 允许调用，False 应阻断

        Raises:
            BudgetExceededError: 预算已耗尽
        """
        current = self._log.total_spent
        ratio = current / MONTHLY_BUDGET_USD if MONTHLY_BUDGET_USD > 0 else 0.0

        # 95% — 全阻断
        if ratio >= MELTDOWN_BLOCK_RATIO:
            raise BudgetExceededError(
                f"月度预算已耗尽 (${current:.2f}/${MONTHLY_BUDGET_USD:.2f}, "
                f"{ratio*100:.0f}%)"
            )

        # 80% — 仅关键任务
        if ratio >= MELTDOWN_RESTRICT_RATIO:
            if task_type not in CRITICAL_TASK_TYPES:
                return False  # 非关键任务降级

        # 50% — 警告但放行
        # (日志级别，不阻断)

        return True

    def estimate_cost(self, task_type: str) -> float:
        """估算单次调用成本

        Args:
            task_type: 任务类型

        Returns:
            预估成本（USD）
        """
        return ESTIMATED_COST_PER_CALL.get(task_type, 0.0001)

    def record_call(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """记录一次 API 调用的实际成本

        Args:
            task_type: 任务类型
            input_tokens: 实际输入 token 数
            output_tokens: 实际输出 token 数

        Returns:
            本次调用成本（USD）
        """
        from .config import COST_PER_1K_INPUT, COST_PER_1K_OUTPUT

        cost = (
            input_tokens / 1000 * COST_PER_1K_INPUT +
            output_tokens / 1000 * COST_PER_1K_OUTPUT
        )

        record = CallRecord(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

        self._log.total_spent += cost
        self._log.call_count += 1
        self._log.by_task_type[task_type] = (
            self._log.by_task_type.get(task_type, 0.0) + cost
        )
        self._log.calls.append(record)

        # 持久化（保留最近 500 条记录）
        if len(self._log.calls) > 500:
            self._log.calls = self._log.calls[-500:]

        self._save()

        return cost

    def remaining_budget(self) -> float:
        """剩余预算"""
        return max(0.0, MONTHLY_BUDGET_USD - self._log.total_spent)

    def current_month_total(self) -> float:
        """当月累计花费"""
        return self._log.total_spent

    def status(self) -> dict:
        """返回当前成本状态

        Returns:
            包含 budget_remaining, monthly_spend, call_count, meltdown_level
        """
        ratio = self._log.total_spent / MONTHLY_BUDGET_USD if MONTHLY_BUDGET_USD > 0 else 0.0

        if ratio >= MELTDOWN_BLOCK_RATIO:
            meltdown_level = "blocked"
        elif ratio >= MELTDOWN_RESTRICT_RATIO:
            meltdown_level = "restricted"
        elif ratio >= MELTDOWN_WARN_RATIO:
            meltdown_level = "warning"
        else:
            meltdown_level = "normal"

        return {
            "budget_remaining": self.remaining_budget(),
            "monthly_spend": round(self._log.total_spent, 4),
            "monthly_budget": MONTHLY_BUDGET_USD,
            "call_count": self._log.call_count,
            "meltdown_level": meltdown_level,
            "by_task_type": dict(self._log.by_task_type),
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_or_reset(self) -> MonthlyLog:
        """加载成本日志，若月份变更则自动重置"""
        current_month = datetime.now().strftime("%Y-%m")

        if self._log_path.exists():
            try:
                data = json.loads(self._log_path.read_text(encoding="utf-8"))
                if data.get("month") == current_month:
                    # 同月，恢复日志
                    log = MonthlyLog(
                        month=data["month"],
                        total_spent=data.get("total_spent", 0.0),
                        call_count=data.get("call_count", 0),
                    )
                    log.by_task_type = data.get("by_task_type", {})
                    log.calls = [
                        CallRecord(**c) for c in data.get("calls", [])
                    ]
                    return log
                # 月份变更，旧日志保留为备份
                archive_path = self._log_path.with_suffix(
                    f".{data.get('month', 'archive')}.json"
                )
                try:
                    archive_path.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
            except (json.JSONDecodeError, KeyError):
                pass

        # 新月份或首次运行
        return MonthlyLog(month=current_month)

    def _save(self) -> None:
        """持久化到磁盘"""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "month": self._log.month,
            "total_spent": round(self._log.total_spent, 6),
            "call_count": self._log.call_count,
            "by_task_type": self._log.by_task_type,
            "calls": [
                {
                    "timestamp": c.timestamp,
                    "task_type": c.task_type,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cost": round(c.cost, 8),
                }
                for c in self._log.calls
            ],
        }
        self._log_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
