"""
LLM 客户端 — Narrative Mind v4.0

统一 LLM 调用接口，包装 OpenAI SDK。
处理重试、超时、成本记录。
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from .config import LLMConfig, TIER_CONFIG, get_config


class LLMClient:
    """LLM 客户端 — 统一调用接口

    包装 OpenAI-compatible SDK，所有引擎通过此类调用 LLM。
    API 失败或未配置时返回 None，调用方走 fallback。
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
    ) -> None:
        """初始化 LLM 客户端

        Args:
            config: LLM 配置（可选，默认从环境变量读取）
        """
        self._config = config or get_config()
        self._client: Any = None
        self._last_input_tokens: int = 0
        self._last_output_tokens: int = 0
        self._last_cost: float = 0.0

        if self._config.is_configured:
            self._init_client()

    def _init_client(self) -> None:
        """初始化 OpenAI SDK 客户端"""
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.timeout,
                max_retries=0,  # 我们自己控制重试
            )
        except ImportError:
            self._client = None

    @property
    def is_available(self) -> bool:
        """LLM 是否可用"""
        return self._client is not None and self._config.is_configured

    def call(
        self,
        system_prompt: str,
        user_message: str,
        task_type: str,
        response_format: str = "json",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[dict]:
        """调用 LLM

        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            task_type: 任务类型（对应 TIER_CONFIG）
            response_format: "json" 或 "text"
            temperature: 覆盖默认温度
            max_tokens: 覆盖默认最大 token 数

        Returns:
            解析后的 JSON dict，或 None（失败/降级）
        """
        if not self.is_available:
            return None

        tier = TIER_CONFIG.get(task_type)
        if not tier:
            return None

        for attempt in range(self._config.max_retries + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._config.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": max_tokens if max_tokens is not None else tier.max_tokens,
                    "temperature": temperature if temperature is not None else tier.temperature,
                }

                if response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}

                response = self._client.chat.completions.create(**kwargs)

                usage = response.usage
                if usage:
                    self._last_input_tokens = usage.prompt_tokens or 0
                    self._last_output_tokens = usage.completion_tokens or 0
                    # 粗略成本估算（将在 Phase B 接入 cost_tracker）
                    from .config import COST_PER_1K_INPUT, COST_PER_1K_OUTPUT
                    self._last_cost = (
                        self._last_input_tokens * COST_PER_1K_INPUT / 1000 +
                        self._last_output_tokens * COST_PER_1K_OUTPUT / 1000
                    )

                content = response.choices[0].message.content
                if not content:
                    return None

                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # 尝试从文本中提取 JSON
                        content = content.strip()
                        start = content.find("{")
                        end = content.rfind("}")
                        if start >= 0 and end > start:
                            try:
                                return json.loads(content[start:end + 1])
                            except json.JSONDecodeError:
                                pass
                        if attempt < self._config.max_retries:
                            continue
                        return None
                else:
                    return {"text": content}

            except Exception:
                if attempt < self._config.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return None

        return None

    def status(self) -> dict:
        """返回 LLM 客户端状态"""
        return {
            "available": self.is_available,
            "model": self._config.model,
            "base_url": self._config.base_url,
        }


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

_client_instance: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """获取全局 LLMClient 单例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
