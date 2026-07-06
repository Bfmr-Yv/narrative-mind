"""
语料切片管理器 — Narrative Mind v4.0

管理语料库切片的读取、索引和检索。
Phase I: 完整实现，LanceDB 向量存储。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np


class SliceManager:
    """语料切片管理器

    使用 LanceDB 存储切片文本和向量，支持语义检索。
    """

    def __init__(self, corpus_path: Optional[str] = None):
        self._corpus_path = Path(corpus_path or "corpus/").resolve()
        self._slices: list[dict[str, Any]] = []
        self._db: Any = None
        self._table: Any = None
        self._table_name = "slices"

    def _ensure_db(self):
        """延迟初始化 LanceDB 连接"""
        if self._db is not None:
            return
        import lancedb
        db_path = self._corpus_path / "lancedb"
        db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(db_path))

        # 尝试打开已有表
        try:
            self._table = self._db.open_table(self._table_name)
        except Exception:
            self._table = None

    def index_slices(
        self,
        texts: list[str],
        embedder: Any,
        source_chapter_ids: Optional[list[str]] = None,
    ) -> int:
        """将文本切片索引到 LanceDB

        Args:
            texts: 文本切片列表
            embedder: Embedder 实例（用于编码）
            source_chapter_ids: 可选的来源章节 ID 列表

        Returns:
            已索引的切片数
        """
        self._ensure_db()

        if not texts:
            return 0

        ids = source_chapter_ids or [""] * len(texts)
        vectors = embedder.encode_batch(texts)

        import lancedb
        import pyarrow as pa

        rows = [
            {
                "text": text,
                "vector": np.array(vec, dtype=np.float32),
                "source_chapter_id": cid,
            }
            for text, vec, cid in zip(texts, vectors, ids)
        ]

        if self._table is not None:
            self._table.add(rows)
        else:
            self._table = self._db.create_table(self._table_name, rows)

        count = len(rows)
        self._slices.extend(
            {"text": t, "source_chapter_id": cid}
            for t, cid in zip(texts, ids)
        )
        return count

    def search(
        self,
        query: str,
        embedder: Any,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """语义检索语料切片

        Args:
            query: 查询文本
            embedder: Embedder 实例
            top_k: 返回结果数

        Returns:
            匹配的切片列表，每项包含 text, source_chapter_id, _distance
        """
        self._ensure_db()

        if self._table is None:
            return []

        query_vec = embedder.encode(query)

        try:
            results = (
                self._table.search(np.array(query_vec, dtype=np.float32))
                .limit(top_k)
                .to_list()
            )
        except Exception:
            return []

        return [
            {
                "slice_id": f"slice_{i}",
                "text": r.get("text", ""),
                "source_chapter_id": r.get("source_chapter_id", ""),
                "similarity": round(1.0 - r.get("_distance", 0.0), 4),
            }
            for i, r in enumerate(results)
        ]

    def index_from_files(self, embedder: Any) -> int:
        """从 corpus/ 目录读取 .txt/.md 文件并索引

        按空行分隔段落作为切片单元。

        Returns:
            索引的切片总数
        """
        texts: list[str] = []
        source_ids: list[str] = []

        for pattern in ["*.txt", "*.md"]:
            for fpath in self._corpus_path.glob(pattern):
                # 跳过 lancedb 目录
                if "lancedb" in fpath.parts:
                    continue
                try:
                    content = fpath.read_text(encoding="utf-8")
                except Exception:
                    continue

                # 按空行分隔段落
                paragraphs = [
                    p.strip()
                    for p in content.split("\n\n")
                    if p.strip()
                ]
                for para in paragraphs:
                    texts.append(para)
                    source_ids.append(fpath.name)

        if not texts:
            return 0

        return self.index_slices(texts, embedder, source_ids)

    def slice_count(self) -> int:
        """返回已索引切片总数"""
        return len(self._slices)

    def status(self) -> dict:
        """返回管理器状态"""
        self._ensure_db()
        return {
            "corpus_path": str(self._corpus_path),
            "slice_count": len(self._slices),
            "table_exists": self._table is not None,
            "phase": "active",
        }
