"""
文本向量化器 — Phase 1

职责：将文本转换为向量表示，用于语料检索。
实现：TF-IDF 向量化（纯 Python 标准库）
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Optional


class Embedder:
    """文本向量化器 — Phase 1

    使用 TF-IDF 将文本转换为向量表示。
    中文分词采用 bigram 方式（两个字符组合）。
    """

    def __init__(self) -> None:
        """初始化向量化器"""
        self._vocabulary: dict[str, int] = {}  # 词 -> 索引
        self._idf_scores: dict[str, float] = {}  # 词 -> IDF 分数
        self._is_fitted = False

    def fit(self, corpus: list[str]) -> None:
        """训练 IDF 模型

        Args:
            corpus: 语料库文本列表
        """
        # 收集所有文档的词
        doc_count = len(corpus)
        doc_freq: dict[str, int] = Counter()  # 词出现在多少文档中

        for text in corpus:
            tokens = set(self._tokenize(text))
            for token in tokens:
                doc_freq[token] += 1

        # 构建词汇表
        self._vocabulary = {
            word: idx for idx, word in enumerate(doc_freq.keys())
        }

        # 计算 IDF 分数
        self._idf_scores = {}
        for word, freq in doc_freq.items():
            self._idf_scores[word] = math.log((doc_count + 1) / (freq + 1)) + 1

        self._is_fitted = True

    def embed(self, text: str) -> list[float]:
        """将文本转换为 TF-IDF 向量

        Args:
            text: 待向量化文本

        Returns:
            TF-IDF 向量表示

        Raises:
            ValueError: 当文本为空时
            RuntimeError: 当模型未训练时
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not self._is_fitted:
            raise RuntimeError("Embedder not fitted. Call fit() first.")

        # 分词
        tokens = self._tokenize(text)

        # 计算 TF
        token_counts = Counter(tokens)
        total_tokens = len(tokens)

        # 生成向量
        vector = [0.0] * len(self._vocabulary)
        for token, count in token_counts.items():
            if token in self._vocabulary:
                tf = count / total_tokens
                idf = self._idf_scores.get(token, 1.0)
                idx = self._vocabulary[token]
                vector[idx] = tf * idf

        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        return [self.embed(text) for text in texts]

    def similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度

        Args:
            vec1: 向量 1
            vec2: 向量 2

        Returns:
            余弦相似度（0 到 1）

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if len(vec1) != len(vec2):
            raise ValueError(
                f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}"
            )

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _tokenize(self, text: str) -> list[str]:
        """中文分词（bigram 方式）

        Args:
            text: 输入文本

        Returns:
            token 列表
        """
        # 清洗文本：保留中文字符和基本标点
        cleaned = re.sub(r'[^\u4e00-\u9fff]', '', text)

        if len(cleaned) < 2:
            return list(cleaned)

        # 使用 bigram 分词
        tokens = []
        for i in range(len(cleaned) - 1):
            tokens.append(cleaned[i:i + 2])

        return tokens

    @property
    def vocabulary_size(self) -> int:
        """词汇表大小"""
        return len(self._vocabulary)

    @property
    def is_fitted(self) -> bool:
        """模型是否已训练"""
        return self._is_fitted
