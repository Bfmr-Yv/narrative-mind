"""
LLM 配置中心 — Narrative Mind v4.0

读取 API 配置，支持 DeepSeek 和 OpenAI 两种 provider。
配置来源优先级：环境变量 > config/llm.json > 默认值。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Provider 配置
# ---------------------------------------------------------------------------

# --- DeepSeek V4 ---
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_PRO_MODEL = "deepseek-v4-pro"
DEEPSEEK_FLASH_MODEL = "deepseek-v4-flash"
DEEPSEEK_COST_PER_1K_INPUT = 0.000435
DEEPSEEK_COST_PER_1K_OUTPUT = 0.00087
DEEPSEEK_FLASH_COST_PER_1K_INPUT = 0.00014
DEEPSEEK_FLASH_COST_PER_1K_OUTPUT = 0.00028

# --- OpenAI ---
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_COST_PER_1K_INPUT = 0.00015
OPENAI_COST_PER_1K_OUTPUT = 0.00060

# --- Xiaomi MiMo (Token Plan) ---
MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MIMO_PRO_MODEL = "mimo-v2.5-pro"
MIMO_FLASH_MODEL = "mimo-v2.5"
MIMO_COST_PER_1K_INPUT = 0.003     # ¥3/MTok ≈ $0.003/1k
MIMO_COST_PER_1K_OUTPUT = 0.006    # ¥6/MTok ≈ $0.006/1k
MIMO_FLASH_COST_PER_1K_INPUT = 0.001   # ¥1/MTok
MIMO_FLASH_COST_PER_1K_OUTPUT = 0.002  # ¥2/MTok


def _resolve_provider() -> str:
    """解析当前使用的 LLM provider。

    优先级：环境变量 LLM_PROVIDER > 配置文件 > 自动检测
    自动检测：有 DEEPSEEK_API_KEY → deepseek，有 MIMO_API_KEY → mimo，否则 → openai
    """
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit in ("deepseek", "openai", "mimo"):
        return explicit
    if os.environ.get("MIMO_API_KEY"):
        return "mimo"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "openai"


def _init_provider_defaults(provider: str | None = None) -> dict:
    """根据 provider 初始化端点、模型和成本默认值。"""
    p = provider or _resolve_provider()
    if p == "deepseek":
        return {
            "base_url": DEEPSEEK_BASE_URL,
            "model": DEEPSEEK_PRO_MODEL,
            "flash_model": DEEPSEEK_FLASH_MODEL,
            "cost_per_1k_input": DEEPSEEK_COST_PER_1K_INPUT,
            "cost_per_1k_output": DEEPSEEK_COST_PER_1K_OUTPUT,
            "provider": "deepseek",
        }
    elif p == "mimo":
        return {
            "base_url": MIMO_BASE_URL,
            "model": MIMO_PRO_MODEL,
            "flash_model": MIMO_FLASH_MODEL,
            "cost_per_1k_input": MIMO_COST_PER_1K_INPUT,
            "cost_per_1k_output": MIMO_COST_PER_1K_OUTPUT,
            "provider": "mimo",
        }
    else:
        return {
            "base_url": OPENAI_BASE_URL,
            "model": OPENAI_DEFAULT_MODEL,
            "flash_model": OPENAI_DEFAULT_MODEL,
            "cost_per_1k_input": OPENAI_COST_PER_1K_INPUT,
            "cost_per_1k_output": OPENAI_COST_PER_1K_OUTPUT,
            "provider": "openai",
        }


# 模块加载时根据环境自动选择 provider 默认值
_active_provider = _init_provider_defaults()
DEFAULT_BASE_URL: str = _active_provider["base_url"]
DEFAULT_MODEL: str = _active_provider["model"]
FLASH_MODEL: str = _active_provider["flash_model"]
COST_PER_1K_INPUT: float = _active_provider["cost_per_1k_input"]
COST_PER_1K_OUTPUT: float = _active_provider["cost_per_1k_output"]
ACTIVE_PROVIDER: str = _active_provider["provider"]

# 月度预算硬上限
MONTHLY_BUDGET_USD = 20.00

# 三层熔断阈值
MELTDOWN_WARN_RATIO = 0.50      # 50% — 警告
MELTDOWN_RESTRICT_RATIO = 0.80  # 80% — 仅关键任务
MELTDOWN_BLOCK_RATIO = 0.95     # 95% — 全阻断

# API 超时
API_TIMEOUT_SECONDS = 25
MAX_RETRIES = 2

# 配置文件路径
CONFIG_FILE_PATH = "config/llm.json"


# ---------------------------------------------------------------------------
# Tier 路由表
# ---------------------------------------------------------------------------

@dataclass
class TierRoute:
    """单个任务的 Tier 配置"""
    model: str
    max_tokens: int
    temperature: float = 0.3


# MiMo-V2.5-Pro 是推理模型，输出 tokens 包含推理过程。
# max_tokens 需要预留推理开销（通常 100-300 tokens），实际内容 = max_tokens - reasoning。
# 以下值已包含推理余量。
TIER_CONFIG: dict[str, TierRoute] = {
    "pad_compute":    TierRoute(model=DEFAULT_MODEL, max_tokens=1024, temperature=0.2),
    "action_infer":   TierRoute(model=DEFAULT_MODEL, max_tokens=1536, temperature=0.3),
    "rule_check":     TierRoute(model=DEFAULT_MODEL, max_tokens=1536, temperature=0.2),
    "spatial_check":  TierRoute(model=DEFAULT_MODEL, max_tokens=1024, temperature=0.2),
    "rerank":         TierRoute(model=DEFAULT_MODEL, max_tokens=1024, temperature=0.1),
    "entity_extract":     TierRoute(model=DEFAULT_MODEL, max_tokens=1536, temperature=0.1),
    "scene_analysis":    TierRoute(model=DEFAULT_MODEL, max_tokens=4096, temperature=0.4),
    "foreshadow_detect": TierRoute(model=DEFAULT_MODEL, max_tokens=2048, temperature=0.3),
    "causal_extract":    TierRoute(model=DEFAULT_MODEL, max_tokens=2048, temperature=0.2),
    "resolution_check":  TierRoute(model=DEFAULT_MODEL, max_tokens=1024, temperature=0.2),
    "event_predict":     TierRoute(model=DEFAULT_MODEL, max_tokens=2048, temperature=0.4),
    "style_check":       TierRoute(model=DEFAULT_MODEL, max_tokens=1536, temperature=0.2),
    "register_check":    TierRoute(model=DEFAULT_MODEL, max_tokens=1536, temperature=0.3),
    "theme_extract":     TierRoute(model=DEFAULT_MODEL, max_tokens=2048, temperature=0.4),
    "economy_check":      TierRoute(model=DEFAULT_MODEL, max_tokens=1536, temperature=0.2),
    "expectation_analyze": TierRoute(model=DEFAULT_MODEL, max_tokens=2048, temperature=0.4),
    "imagery_detect":    TierRoute(model=DEFAULT_MODEL, max_tokens=2048, temperature=0.4),
}


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
# 配置加载
# ---------------------------------------------------------------------------

def _load_config_file() -> dict:
    """从 config/llm.json 加载配置"""
    import sys

    candidates = [Path(CONFIG_FILE_PATH)]

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
    - LLM_PROVIDER: 强制指定 provider（"deepseek" | "openai"）
    - LLM_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY: API key
    - LLM_BASE_URL / DEEPSEEK_BASE_URL / OPENAI_BASE_URL: API 地址
    - LLM_MODEL / DEEPSEEK_MODEL / OPENAI_MODEL: 模型名称
    """
    file_config = _load_config_file()
    # 从配置文件或环境变量检测 provider
    file_provider = file_config.get("provider", "").strip().lower()
    if file_provider in ("deepseek", "openai", "mimo"):
        provider_config = _init_provider_defaults(file_provider)
    else:
        provider_config = _init_provider_defaults()

    resolved_key = (
        api_key or
        os.environ.get("LLM_API_KEY", "") or
        os.environ.get("DEEPSEEK_API_KEY", "") or
        os.environ.get("OPENAI_API_KEY", "") or
        os.environ.get("MIMO_API_KEY", "") or
        file_config.get("api_key", "")
    )

    resolved_url = (
        base_url or
        os.environ.get("LLM_BASE_URL", "") or
        os.environ.get("DEEPSEEK_BASE_URL", "") or
        os.environ.get("OPENAI_BASE_URL", "") or
        file_config.get("base_url", "") or
        provider_config["base_url"]
    )

    resolved_model = (
        model or
        os.environ.get("LLM_MODEL", "") or
        os.environ.get("DEEPSEEK_MODEL", "") or
        os.environ.get("OPENAI_MODEL", "") or
        os.environ.get("MIMO_MODEL", "") or
        file_config.get("model", "") or
        provider_config["model"]
    )

    return LLMConfig(
        api_key=resolved_key,
        base_url=resolved_url,
        model=resolved_model,
    )


def get_provider_config(provider: str | None = None) -> dict:
    """获取指定 provider 的端点、模型和成本参数。"""
    return _init_provider_defaults(provider)
