"""
语料检索器 — Narrative Mind v4.0

基于嵌入向量的语义检索。
Phase I: 完整实现，组合 SliceManager + Embedder。
"""

from __future__ import annotations

from typing import Any, Optional

from .slice_manager import SliceManager
from .embedder import Embedder


class Retriever:
    """语料检索器

    组合 SliceManager + Embedder 完成语义搜索。
    """

    def __init__(
        self,
        corpus_path: str = "corpus/",
        slice_manager: Optional[SliceManager] = None,
        embedder: Optional[Embedder] = None,
    ):
        self.slice_manager = slice_manager or SliceManager(corpus_path)
        self.embedder = embedder or Embedder()

    def search(
        self,
        query_text: str,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """语义检索语料切片

        Args:
            query_text: 查询文本
            top_k: 返回结果数
            filters: 可选的元数据过滤条件（当前未使用，预留）

        Returns:
            匹配的切片列表，每项包含 slice_id, text, source_chapter_id, similarity
        """
        return self.slice_manager.search(query_text, self.embedder, top_k)

    def index_corpus(self, texts: list[str]) -> int:
        """索引文本切片

        Args:
            texts: 文本切片列表

        Returns:
            已索引的切片数
        """
        return self.slice_manager.index_slices(texts, self.embedder)

    def index_from_files(self) -> int:
        """从 corpus/ 目录自动索引"""
        return self.slice_manager.index_from_files(self.embedder)

    def status(self) -> dict:
        """返回检索器状态"""
        return {
            "slice_manager": self.slice_manager.status(),
            "embedder": self.embedder.status(),
            "phase": "active",
        }
