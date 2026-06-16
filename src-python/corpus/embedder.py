"""
文本嵌入器 — Narrative Mind v4.0

将文本转换为嵌入向量，用于语义检索。
Phase A 支架实现，Phase F 完整移植。
"""

from __future__ import annotations

from typing import Any, Optional


class Embedder:
    """文本嵌入器

    Phase A 支架：encode() 返回空向量。
    Phase F 完整实现：加载 sentence-transformers 模型，生成嵌入向量。
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or "paraphrase-multilingual-MiniLM-L12-v2"
        self._model: Any = None  # sentence-transformers 模型，延迟加载

    def encode(self, text: str) -> list[float]:
        """将文本编码为向量（支架：返回空列表）

        Args:
            text: 输入文本

        Returns:
            嵌入向量（float 列表）
        """
        return []

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """批量编码（支架：返回空向量列表）"""
        return [[] for _ in texts]

    def status(self) -> dict:
        """返回嵌入器状态"""
        return {
            "model_name": self._model_name,
            "loaded": self._model is not None,
            "phase": "stub",
        }
