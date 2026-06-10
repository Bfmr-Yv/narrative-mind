# 编码规范

> **项目**: Narrative Mind v3.1  
> **最后更新**: 2026-06-03  
> **适用范围**: Phase 1 所有 Python 代码

---

## 1. 语言与环境

- **Python 版本**: 3.11+
- **类型注解**: 必须使用（`from __future__ import annotations`）
- **编码**: UTF-8

---

## 2. 依赖管理

### 2.1 Phase 1 限制

**核心引擎禁止引入任何外部依赖**，仅使用 Python 标准库。

**例外**：API 服务器（`src/api_server.py`）允许使用 Flask 和 Flask-CORS，因为标准库 `http.server` 无法提供生产级 REST API 所需的路由、CORS 和 JSON 处理能力。此例外仅适用于 Web 传输层，引擎核心逻辑不受影响。

### 2.2 允许的标准库模块

```python
# 数据处理
dataclasses, typing, json, csv, sqlite3

# 文件与路径
pathlib, os, shutil

# 日期时间
datetime, time

# 序列化
pickle, base64

# 网络（Phase 1 本地优先）
http.server, socketserver

# 并发（按需）
threading, concurrent.futures

# 日志
logging

# 测试
unittest, pytest（如后续引入）
```

---

## 3. 代码风格

### 3.1 PEP 8 基础

- 缩进：4 空格
- 行宽：88 字符（Black 默认）
- 命名约定：
  - 变量/函数：`snake_case`
  - 类：`PascalCase`
  - 常量：`UPPER_SNAKE_CASE`
  - 私有成员：`_前缀`

### 3.2 类型注解

```python
# ✅ 正确
def process_text(text: str, top_k: int = 3) -> list[dict[str, Any]]:
    ...

# ❌ 错误
def process_text(text, top_k=3):
    ...
```

### 3.3 文档字符串（Google 风格）

```python
def retrieve_similar_slices(
    query_text: str,
    category: str,
    top_k: int = 3
) -> CorpusResponse:
    """检索语料切片

    Args:
        query_text: 待检索文本片段
        category: 检索类别（behavior/emotion/scene/world_rule）
        top_k: 返回数量，默认 3

    Returns:
        CorpusResponse: 包含命中切片和相似度分数

    Raises:
        ValueError: 当 category 不在允许范围内
    """
```

---

## 4. 数据模型

### 4.1 使用 dataclass

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CorpusQuery:
    """语料检索查询"""
    text: str
    category: str
    character_id: Optional[str] = None
    top_k: int = 3
```

### 4.2 类型别名

```python
from typing import TypeAlias

# 类型别名
Vector: TypeAlias = list[float]
SliceID: TypeAlias = str
```

---

## 5. 错误处理

### 5.1 异常层次

```python
class NarrativeMindError(Exception):
    """基础异常"""
    pass

class CorpusError(NarrativeMindError):
    """语料相关错误"""
    pass

class EngineError(NarrativeMindError):
    """引擎执行错误"""
    pass
```

### 5.2 错误处理原则

- 不捕获裸异常（`except Exception`）
- 记录详细错误日志
- 向上层返回有意义的错误信息

---

## 6. 模块组织

### 6.1 文件结构

```
src/corpus_anchor/
├── __init__.py          # 公开 API
├── retriever.py         # 向量检索
├── embedder.py          # 文本向量化
├── slice_manager.py     # 切片管理
└── _internal.py         # 内部实现（可选）
```

### 6.2 导入顺序

```python
# 1. 标准库
import json
from pathlib import Path
from typing import Optional

# 2. 项目内模块
from src.shared.config import load_config
from src.memory.models import MemoryWrite

# 3. 当前包内
from .retriever import Retriever
```

---

## 7. 测试规范

### 7.1 测试结构

```
tests/
├── unit/
│   └── test_corpus_anchor/
│       ├── __init__.py
│       ├── test_retriever.py
│       └── test_embedder.py
└── fixtures/
    └── sample_slices.json
```

### 7.2 测试命名

```python
class TestRetriever:
    """检索器测试"""

    def test_retrieve_returns_top_k_slices(self):
        """验证返回指定数量的结果"""
        ...

    def test_similarity_score_above_threshold(self):
        """验证相似度分数 > 0.3"""
        ...
```

---

## 8. 语料切片规范

### 8.1 切片格式

```json
{
  "slice_id": "hlm_001",
  "source": "红楼梦",
  "chapter": "第一回",
  "text": "500字场景级文本...",
  "metadata": {
    "characters": ["贾宝玉", "林黛玉"],
    "scene_type": "dialogue",
    "emotion": "melancholy"
  }
}
```

### 8.2 质量要求

- 每片 450-800 字（场景级完整性优先于字数限制）
- 场景级完整性（有开头、发展、结尾）
- 人工审核确认真实性
- 标注角色、场景类型、情感基调

---

## 9. 提交规范

### 9.1 提交信息格式

```
<type>(<scope>): <description>

[可选正文]

[可选脚注]
```

### 9.2 类型示例

- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

---

## 10. 自检清单

提交代码前确认：

- [ ] 无外部依赖引入
- [ ] 类型注解完整
- [ ] 文档字符串符合 Google 风格
- [ ] 命名符合 PEP 8
- [ ] 错误处理适当
- [ ] 测试覆盖关键路径
