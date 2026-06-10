"""
向量检索器 — Phase 1

职责：基于向量相似度检索语料切片。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .embedder import Embedder
from .slice_manager import SliceManager, CorpusSlice


@dataclass
class CorpusHit:
    """语料命中结果"""
    slice_id: str
    text: str
    similarity: float
    metadata: dict = field(default_factory=dict)


@dataclass
class CorpusResponse:
    """语料检索响应"""
    hits: list[CorpusHit]
    similarity_scores: list[float]


class Retriever:
    """向量检索器 — Phase 1

    基于 TF-IDF 向量相似度检索语料切片。
    相似度 < 0.3 的结果不返回（噪声过滤）。
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        slice_manager: Optional[SliceManager] = None,
        similarity_threshold: float = 0.1,
        llm_client: Optional[object] = None,
        enricher: Optional[object] = None,
    ) -> None:
        """初始化检索器

        Args:
            embedder: 向量化器实例
            slice_manager: 切片管理器实例
            similarity_threshold: 相似度阈值，默认 0.1
            llm_client: LLM 客户端（可选，用于精排）
            enricher: 语料自扩充器（可选，提供动态索引）
        """
        self._embedder = embedder or Embedder()
        self._slice_manager = slice_manager or SliceManager()
        self._similarity_threshold = similarity_threshold
        self._llm = llm_client
        self._enricher = enricher
        self._slice_vectors: dict[str, list[float]] = {}
        self._dynamic_vectors: dict[str, list[float]] = {}
        self._is_indexed = False

    def build_index(self) -> None:
        """构建向量索引

        从 SliceManager 加载所有切片，训练 Embedder 并生成向量。
        同时构建动态扩充索引（如果 Enricher 可用）。
        """
        slices = self._slice_manager.get_all_slices()
        if not slices:
            return

        # 训练 Embedder（仅基于静态语料，保持词汇表稳定）
        texts = [s.text for s in slices]
        self._embedder.fit(texts)

        # 生成所有静态切片的向量
        for slice_obj in slices:
            vector = self._embedder.embed(slice_obj.text)
            self._slice_vectors[slice_obj.slice_id] = vector

        # 构建动态扩充索引
        self.rebuild_dynamic_index()

        self._is_indexed = True

    def rebuild_dynamic_index(self) -> int:
        """重建动态扩充索引

        从 Enricher 加载所有动态切片并生成向量。
        在 Enricher 写入新切片后调用。

        Returns:
            动态索引中的切片数量
        """
        if not self._enricher:
            return 0

        dynamic_slices = self._enricher.get_dynamic_slices()
        if not dynamic_slices:
            return 0

        self._dynamic_vectors.clear()
        for slice_obj in dynamic_slices:
            try:
                # 使用同一个 Embedder（已训练）向量化
                vector = self._embedder.embed(slice_obj.text)
                self._dynamic_vectors[slice_obj.slice_id] = vector
            except Exception:
                continue

        return len(self._dynamic_vectors)

    def retrieve(
        self,
        query_text: str,
        category: str,
        top_k: int = 3
    ) -> CorpusResponse:
        """检索语料切片（双索引 + LLM 精排）

        流水线：
        1. TF-IDF 检索静态语料库 → top-N
        2. TF-IDF 检索动态扩充索引 → top-N
        3. 合并去重，按相似度粗排
        4. 如果有 LLM：取 top-20 候选 → LLM 精排选 top-k
        5. 如果无 LLM：直接返回粗排 top-k

        Args:
            query_text: 待检索文本片段
            category: 检索类别（behavior/emotion/scene/world_rule）
            top_k: 返回数量，默认 3

        Returns:
            CorpusResponse: 包含命中切片和相似度分数

        Raises:
            ValueError: 当 category 不在允许范围内
            RuntimeError: 当索引未构建时
        """
        allowed_categories = {"behavior", "emotion", "scene", "world_rule"}
        if category not in allowed_categories:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Allowed: {allowed_categories}"
            )

        if not self._is_indexed:
            raise RuntimeError("Index not built. Call build_index() first.")

        # 向量化查询文本
        query_vector = self._embedder.embed(query_text)

        # 1. 检索静态语料库
        static_hits = self._search_vector_index(
            query_vector, self._slice_vectors, top_k=20
        )

        # 2. 检索动态扩充索引
        dynamic_hits: list[tuple[str, float]] = []
        if self._dynamic_vectors:
            dynamic_hits = self._search_vector_index(
                query_vector, self._dynamic_vectors, top_k=20
            )

        # 3. 合并去重（动态命中优先保留更高相似度）
        seen_ids: set[str] = set()
        merged: list[tuple[str, float]] = []

        for slice_id, sim in dynamic_hits + static_hits:
            if slice_id not in seen_ids and sim >= self._similarity_threshold:
                seen_ids.add(slice_id)
                merged.append((slice_id, sim))
                if len(merged) >= 20:
                    break

        # 按相似度降序排序
        merged.sort(key=lambda x: x[1], reverse=True)

        # 4. LLM 精排（如果可用且候选充足）
        if self._llm and self._llm.is_available and len(merged) > top_k:
            try:
                merged = self._llm_rerank(query_text, merged, top_k)
            except Exception:
                pass  # Fall through to TF-IDF only

        # 取 top_k
        top_results = merged[:top_k]

        # 5. 构建响应
        hits = []
        scores = []
        for slice_id, sim in top_results:
            slice_obj = self._get_slice_from_any(slice_id)
            if slice_obj:
                hit = CorpusHit(
                    slice_id=slice_id,
                    text=slice_obj.text,
                    similarity=sim,
                    metadata={
                        "source": slice_obj.source,
                        "chapter": slice_obj.chapter,
                        "characters": slice_obj.metadata.characters,
                        "scene_type": slice_obj.metadata.scene_type,
                        "emotion": slice_obj.metadata.emotion,
                    }
                )
                hits.append(hit)
                scores.append(sim)

        return CorpusResponse(hits=hits, similarity_scores=scores)

    def retrieve_by_character(
        self,
        query_text: str,
        character_id: str,
        category: str,
        top_k: int = 3
    ) -> CorpusResponse:
        """按角色限定检索语料切片

        Args:
            query_text: 待检索文本片段
            character_id: 限定角色范围
            category: 检索类别
            top_k: 返回数量

        Returns:
            CorpusResponse: 包含命中切片和相似度分数
        """
        # 先获取所有结果（候选池扩大以便角色过滤后仍有足够候选）
        all_results = self.retrieve(query_text, category, top_k=100)

        # 按角色过滤
        filtered_hits = []
        filtered_scores = []
        for hit, score in zip(all_results.hits, all_results.similarity_scores):
            if character_id in hit.metadata.get("characters", []):
                filtered_hits.append(hit)
                filtered_scores.append(score)
                if len(filtered_hits) >= top_k:
                    break

        return CorpusResponse(hits=filtered_hits, similarity_scores=filtered_scores)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _search_vector_index(
        self,
        query_vector: list[float],
        index: dict[str, list[float]],
        top_k: int = 20,
    ) -> list[tuple[str, float]]:
        """在指定向量索引中搜索

        Args:
            query_vector: 查询向量
            index: 向量索引 (slice_id -> vector)
            top_k: 返回数量

        Returns:
            [(slice_id, similarity), ...] 按相似度降序
        """
        similarities: list[tuple[str, float]] = []
        for slice_id, slice_vector in index.items():
            sim = self._embedder.similarity(query_vector, slice_vector)
            if sim >= self._similarity_threshold:
                similarities.append((slice_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _get_slice_from_any(self, slice_id: str) -> Optional[CorpusSlice]:
        """从任意来源获取切片（静态或动态）

        Args:
            slice_id: 切片 ID

        Returns:
            CorpusSlice 或 None
        """
        # 先查静态
        slice_obj = self._slice_manager.get_slice(slice_id)
        if slice_obj:
            return slice_obj

        # 再查动态
        if self._enricher:
            for s in self._enricher.get_dynamic_slices():
                if s.slice_id == slice_id:
                    return s

        return None

    def _llm_rerank(
        self,
        query_text: str,
        candidates: list[tuple[str, float]],
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
        """使用 LLM 对候选切片进行语义精排

        Args:
            query_text: 查询文本
            candidates: TF-IDF 候选 [(slice_id, similarity), ...]
            top_k: 返回数量

        Returns:
            LLM 精排后的 [(slice_id, similarity), ...]
        """
        if not self._llm or not self._llm.is_available:
            return candidates[:top_k]

        try:
            from ..llm.prompts import RERANK_SYSTEM, format_rerank_prompt

            # 构建候选摘要列表
            candidate_summaries: list[tuple[str, str]] = []
            for slice_id, sim in candidates:
                slice_obj = self._get_slice_from_any(slice_id)
                if slice_obj:
                    snippet = slice_obj.text[:80].replace("\n", " ")
                    source = slice_obj.source
                    candidate_summaries.append((slice_id, f"[{source}] {snippet}"))
                else:
                    candidate_summaries.append((slice_id, f"[unknown]"))

            if not candidate_summaries:
                return candidates[:top_k]

            user_message = format_rerank_prompt(query_text, candidate_summaries)

            result = self._llm.call(
                system_prompt=RERANK_SYSTEM,
                user_message=user_message,
                task_type="rerank",
            )

            if result and "ranked_ids" in result:
                ranked_ids = result["ranked_ids"]
                # 保持原有相似度分数，但按 LLM 排序
                sim_map = dict(candidates)
                reranked = []
                for sid in ranked_ids:
                    if sid in sim_map:
                        reranked.append((sid, sim_map[sid]))
                # 补上 LLM 未排的候选项
                seen = set(ranked_ids)
                for sid, sim in candidates:
                    if sid not in seen:
                        reranked.append((sid, sim))
                        seen.add(sid)
                return reranked[:top_k]

        except Exception:
            pass

        return candidates[:top_k]

    @property
    def is_indexed(self) -> bool:
        """索引是否已构建"""
        return self._is_indexed

    @property
    def slice_count(self) -> int:
        """已索引的切片数量"""
        return len(self._slice_vectors)
