"""
文本嵌入器 — Narrative Mind v4.0

将文本转换为嵌入向量，用于语义检索。
Phase I: 完整实现，sentence-transformers 延迟加载。
"""

from __future__ import annotations

from typing import Any, Optional


class Embedder:
    """文本嵌入器

    使用 sentence-transformers 模型生成 384 维嵌入向量。
    首次调用 encode() 时自动下载模型（~120MB），后续调用复用。
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "paraphrase-multilingual-MiniLM-L12-v2"
        self._model: Any = None  # 延迟加载

    def _load(self):
        """延迟加载模型（首次调用时触发）"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)

    def encode(self, text: str) -> list[float]:
        """将文本编码为向量

        Args:
            text: 输入文本

        Returns:
            384 维嵌入向量（float 列表）
        """
        self._load()
        return self._model.encode(text).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """批量编码

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        self._load()
        return self._model.encode(texts).tolist()

    def status(self) -> dict:
        """返回嵌入器状态"""
        return {
            "phase": "active",
            "model": self.model_name,
            "loaded": self._model is not None,
        }
