"""
Narrative Mind v4.0 — LLM 集成层
OpenAI 兼容 SDK 封装
"""

from .client import LLMClient, get_client
from .config import LLMConfig, get_config

__all__ = ["LLMClient", "get_client", "LLMConfig", "get_config"]
