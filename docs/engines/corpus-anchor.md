# 语料锚定层卡片 `[Phase 1 共享基础设施]`

> **v3.1 更新**：切片标准确定为 500 字场景级（ADR-013）。

## 职责
提供语料向量检索服务，为角色引擎和世界引擎提供行为模式和设定规则的语料支撑。只做检索，不做语料修改。

## 当前状态
- [x] 技术选型（LanceDB）
- [ ] 向量维度确定（768 BGE-small vs 1024 BGE-large）
- [ ] 相似度算法选择（余弦相似度 vs 内积）
- [x] 语料切片格式定义（500 字场景级，ADR-013）
- [ ] 索引更新流程
- [ ] Phase 1 启动集：20 切片（红楼 10 + 自有 10）

## 输入/输出

**输入**：`CorpusQuery { text, category, character_id, top_k }`

**输出**：`CorpusResponse { hits, similarity_scores }`

详见 `02-CONTRACTS.md`

## 依赖模块
- LanceDB（向量存储）

## 语料切片格式（草案）

```python
@dataclass
class CorpusSlice:
    id: str                    # 切片唯一 ID
    source: str                # 来源（如 "红楼梦-第三回"）
    text: str                  # 原文文本
    category: str              # "behavior" / "emotion" / "scene" / "world_rule"
    character_ids: list[str]   # 涉及的角色 ID
    metadata: dict             # 额外元数据（章节、场景等）
    embedding: list[float]     # 向量表示
```

## 向量检索流程

```python
def search(query: CorpusQuery) -> CorpusResponse:
    # 1. 文本向量化
    embedding = embed_model.encode(query.text)
    
    # 2. 构建过滤条件
    filters = {"category": query.category}
    if query.character_id:
        filters["character_ids"] = {"$contains": query.character_id}
    
    # 3. 向量检索
    results = lance_db.search(
        embedding,
        filters=filters,
        top_k=query.top_k
    )
    
    # 4. 过滤低相似度结果
    hits = [r for r in results if r.score >= 0.3]
    
    return CorpusResponse(
        hits=[CorpusSlice(**r.data) for r in hits],
        similarity_scores=[r.score for r in hits]
    )
```

## 索引更新流程

```
新增语料 → 切片 → 向量化 → 写入 LanceDB
                    ↓
            更新 SQLite 元数据索引
```

## 阻塞问题
- 向量维度：768（BGE-small）还是 1024（BGE-large）？
- 相似度算法：余弦相似度还是内积？
- 语料切片的粒度：按段落还是按场景？

## 设计笔记
- 只做检索，不做语料修改
- 相似度 < 0.3 的结果不返回（噪声过滤）
- 向量模型用本地 BGE，不调用 API
