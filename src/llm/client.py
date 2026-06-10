"""
LLM 客户端 — Phase 1

统一 LLM 调用接口，包装 OpenAI SDK。
处理重试、超时、成本记录和预算检查。
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from .config import LLMConfig, TIER_CONFIG, get_config
from .cost_tracker import CostTracker, BudgetExceededError


class LLMClient:
    """LLM 客户端 — 统一调用接口

    包装 OpenAI-compatible SDK，所有引擎通过此类调用 LLM。
    API 失败或预算超限时返回 None，调用方走 fallback。
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        """初始化 LLM 客户端

        Args:
            config: LLM 配置（可选，默认从环境变量读取）
            cost_tracker: 成本追踪器（可选，默认创建新实例）
        """
        self._config = config or get_config()
        self._cost_tracker = cost_tracker or CostTracker()
        self._client: Any = None  # OpenAI client，延迟初始化

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
    ) -> Optional[dict]:
        """调用 LLM

        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            task_type: 任务类型（对应 TIER_CONFIG）
            response_format: "json" 或 "text"

        Returns:
            解析后的 JSON dict，或 None（失败/降级）
        """
        if not self.is_available:
            return None

        # 1. 获取 Tier 配置
        tier = TIER_CONFIG.get(task_type)
        if not tier:
            return None

        # 2. 预算检查
        try:
            allowed = self._cost_tracker.check_before_call(task_type)
            if not allowed:
                # 降级：非关键任务在预算紧张时跳过
                return None
        except BudgetExceededError:
            return None

        # 3. 调用 API（含重试）
        for attempt in range(self._config.max_retries + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": tier.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": tier.max_tokens,
                    "temperature": tier.temperature,
                }

                # JSON mode（DeepSeek 兼容 OpenAI 的 response_format）
                if response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}

                response = self._client.chat.completions.create(**kwargs)

                # 记录成本
                usage = response.usage
                if usage:
                    self._cost_tracker.record_call(
                        task_type=task_type,
                        input_tokens=usage.prompt_tokens or 0,
                        output_tokens=usage.completion_tokens or 0,
                    )

                # 提取内容
                content = response.choices[0].message.content
                if not content:
                    return None

                # 解析 JSON
                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # JSON 解析失败，尝试从文本中提取
                        content = content.strip()
                        # 尝试找到 {...} 块
                        start = content.find("{")
                        end = content.rfind("}")
                        if start >= 0 and end > start:
                            try:
                                return json.loads(content[start:end + 1])
                            except json.JSONDecodeError:
                                pass
                        # 最后一次重试
                        if attempt < self._config.max_retries:
                            continue
                        return None
                else:
                    return {"text": content}

            except Exception:
                if attempt < self._config.max_retries:
                    time.sleep(0.5 * (attempt + 1))  # 递增等待
                    continue
                return None

        return None

    def status(self) -> dict:
        """返回 LLM 客户端状态"""
        return {
            "available": self.is_available,
            "model": self._config.model,
            "base_url": self._config.base_url,
            **self._cost_tracker.status(),
        }
