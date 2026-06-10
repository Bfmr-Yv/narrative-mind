"""
LLM 配置中心 — Phase 1

读取 API 配置、定义 Tier 路由和成本常数。
配置来源优先级：环境变量 > config/llm.json > 默认值。
未配置 API key 时 LLM 调用自动跳过。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# 默认值（MiMo TokenPlan）
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.5-pro"

# MiMo TokenPlan 定价参考（用于成本追踪，实际以 TokenPlan 消耗为准）
# MiMo v2.5-pro: 输入 ~$0.55/1M tokens, 输出 ~$1.10/1M tokens
COST_PER_1K_INPUT = 0.00055    # $0.00055 / 1K input tokens
COST_PER_1K_OUTPUT = 0.00110   # $0.00110 / 1K output tokens

# 月度预算硬上限（来源：04-COST-BUDGET.md）
MONTHLY_BUDGET_USD = 20.00

# 三层熔断阈值
MELTDOWN_WARN_RATIO = 0.50      # 50% ($10) — 警告
MELTDOWN_RESTRICT_RATIO = 0.80  # 80% ($16) — 仅关键任务
MELTDOWN_BLOCK_RATIO = 0.95     # 95% ($19) — 全阻断

# 单次调用成本估算（MiMo v2.5-pro，用于事前检查）
ESTIMATED_COST_PER_CALL = {
    "pad_compute":    0.00030,   # ~300 in + ~150 out
    "action_infer":   0.00077,   # ~800 in + ~300 out
    "rule_check":     0.00039,   # ~400 in + ~150 out
    "spatial_check":  0.00027,   # ~300 in + ~100 out
    "rerank":         0.00104,   # ~1500 in + ~200 out
    "entity_extract": 0.00066,   # ~800 in + ~200 out (Item 2)
    "scene_analysis": 0.00165,   # ~1500 in + ~500 out (unified analysis)
}

# API 超时（留 5s 给编排器的 30s fallback）
API_TIMEOUT_SECONDS = 25

# 最大重试次数
MAX_RETRIES = 2

# 配置文件路径
CONFIG_FILE_PATH = "config/llm.json"


# ---------------------------------------------------------------------------
# 配置数据模型
# ---------------------------------------------------------------------------

@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: int = API_TIMEOUT_SECONDS
    max_retries: int = MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        """是否已配置 API key"""
        return bool(self.api_key and self.api_key.strip())


# ---------------------------------------------------------------------------
# Tier 路由表
# ---------------------------------------------------------------------------

@dataclass
class TierRoute:
    """单个任务的 Tier 配置"""
    model: str
    max_tokens: int
    temperature: float = 0.3  # 分析任务用低温度，保证一致性


TIER_CONFIG: dict[str, TierRoute] = {
    "pad_compute":    TierRoute(model=DEFAULT_MODEL, max_tokens=256,  temperature=0.2),
    "action_infer":   TierRoute(model=DEFAULT_MODEL, max_tokens=512,  temperature=0.3),
    "rule_check":     TierRoute(model=DEFAULT_MODEL, max_tokens=512,  temperature=0.2),
    "spatial_check":  TierRoute(model=DEFAULT_MODEL, max_tokens=256,  temperature=0.2),
    "rerank":         TierRoute(model=DEFAULT_MODEL, max_tokens=256,  temperature=0.1),
    "entity_extract": TierRoute(model=DEFAULT_MODEL, max_tokens=512,  temperature=0.1),
    "scene_analysis": TierRoute(model=DEFAULT_MODEL, max_tokens=1024, temperature=0.4),
}

# Tier 2+ 任务（预算紧张时优先保留，Tier 1 类任务先降级）
CRITICAL_TASK_TYPES = {"action_infer", "rule_check"}


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def _load_config_file() -> dict:
    """从 config/llm.json 加载配置

    路径解析优先级：
    1. PyInstaller frozen: <_MEIPASS>/config/llm.json
    2. CWD: ./config/llm.json
    3. 项目根: ../config/llm.json (相对于此文件)

    Returns:
        配置字典（可能为空）
    """
    import sys

    candidates = [Path(CONFIG_FILE_PATH)]

    # PyInstaller frozen 模式
    if getattr(sys, 'frozen', False):
        candidates.insert(0, Path(sys._MEIPASS) / CONFIG_FILE_PATH)

    # 相对于此文件的上级目录（项目根）
    candidates.append(Path(__file__).resolve().parent.parent.parent / CONFIG_FILE_PATH)

    for config_path in candidates:
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("api_key"):
                    return data
            except (json.JSONDecodeError, OSError):
                continue

    return {}


def get_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMConfig:
    """获取 LLM 配置

    优先级：参数 > 环境变量 > config/llm.json > 默认值

    环境变量：
    - LLM_API_KEY: API key
    - LLM_BASE_URL: API 地址
    - LLM_MODEL: 模型名称

    Args:
        api_key: API key（可选）
        base_url: API 地址（可选）
        model: 模型名称（可选）

    Returns:
        LLMConfig 实例
    """
    # 1. 从配置文件加载
    file_config = _load_config_file()

    # 2. 逐字段按优先级解析
    resolved_key = (
        api_key or
        os.environ.get("LLM_API_KEY", "") or
        os.environ.get("DEEPSEEK_API_KEY", "") or  # 兼容旧环境变量名
        file_config.get("api_key", "")
    )

    resolved_url = (
        base_url or
        os.environ.get("LLM_BASE_URL", "") or
        os.environ.get("DEEPSEEK_BASE_URL", "") or
        file_config.get("base_url", DEFAULT_BASE_URL)
    )

    resolved_model = (
        model or
        os.environ.get("LLM_MODEL", "") or
        os.environ.get("DEEPSEEK_MODEL", "") or
        file_config.get("model", DEFAULT_MODEL)
    )

    return LLMConfig(
        api_key=resolved_key,
        base_url=resolved_url,
        model=resolved_model,
    )
