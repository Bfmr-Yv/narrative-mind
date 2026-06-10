"""
LLM 集成层 — Phase 1 M6

提供统一的 LLM 调用抽象、成本追踪和预算控制。
所有引擎通过此层调用 LLM，不直接使用外部 SDK。
"""

from .config import LLMConfig, get_config, TIER_CONFIG, MONTHLY_BUDGET_USD
from .cost_tracker import CostTracker, BudgetExceededError
from .client import LLMClient
from .prompts import (
    PAD_COMPUTE_SYSTEM,
    ACTION_INFER_SYSTEM,
    RULE_CHECK_SYSTEM,
    SPATIAL_CHECK_SYSTEM,
    RERANK_SYSTEM,
    format_pad_prompt,
    format_action_prompt,
    format_rule_check_prompt,
    format_spatial_check_prompt,
    format_rerank_prompt,
)

__all__ = [
    "LLMConfig",
    "get_config",
    "TIER_CONFIG",
    "MONTHLY_BUDGET_USD",
    "CostTracker",
    "BudgetExceededError",
    "LLMClient",
    "PAD_COMPUTE_SYSTEM",
    "ACTION_INFER_SYSTEM",
    "RULE_CHECK_SYSTEM",
    "SPATIAL_CHECK_SYSTEM",
    "RERANK_SYSTEM",
    "format_pad_prompt",
    "format_action_prompt",
    "format_rule_check_prompt",
    "format_spatial_check_prompt",
    "format_rerank_prompt",
]
