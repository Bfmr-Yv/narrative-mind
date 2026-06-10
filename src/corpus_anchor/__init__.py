"""
语料锚定层 (Corpus Anchor) — Phase 1

职责：提供语料向量检索服务，为其他引擎提供行为模式和设定规则的语料支撑。

契约（来源：02-CONTRACTS.md）：
- 只做检索，不做语料修改
- 相似度 < 0.3 的结果不返回（噪声过滤）
- 切片标准 500 字场景级（ADR-013）

Phase 1 M6 新增：
- Enricher: 语料自扩充器，LLM 分析结果反哺动态索引

依赖：LanceDB（向量存储）
"""

from __future__ import annotations

from .retriever import Retriever
from .embedder import Embedder
from .slice_manager import SliceManager
from .enricher import Enricher

__all__ = ["Retriever", "Embedder", "SliceManager", "Enricher"]

