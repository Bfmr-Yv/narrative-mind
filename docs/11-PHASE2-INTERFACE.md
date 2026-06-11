# Phase 2 接口文档 — 实践者对接指南

> **写给实践者**：这份文档涵盖 Phase 2 新增的 4 个模块（叙事引擎、文辞引擎、情节记忆、永久记忆）的完整接口。所有模块均可独立实例化、独立测试，不依赖编排器。

---

## 一、模块总览

```
src/
├── engines/
│   ├── narrative.py    # 叙事引擎 — 伏笔 + 因果链 + 情节推演
│   └── prose.py        # 文辞引擎 — 风格指标 + 语域一致性
├── memory/
│   ├── episodic_memory.py   # 情节记忆 — SQLite 持久化 + 热缓存
│   └── permanent_memory.py  # 永久记忆 — 作者指纹 + 原型库
└── orchestrator/
    └── router.py       # 已集成 prose 路由 + full_analyze 四引擎
```

### 测试命令

```bash
# 叙事引擎（6 项）
.venv\Scripts\python scripts\test_narrative_engine.py

# 文辞引擎（8 项）
.venv\Scripts\python scripts\test_prose_engine.py

# 三层记忆（9 项）
.venv\Scripts\python scripts\test_memory_system.py

# 全部串起来
.venv\Scripts\python scripts\test_integration.py
```

---

## 二、叙事引擎 (`src/engines/narrative.py`)

### 2.1 导入

```python
from src.engines.narrative import (
    NarrativeEngine, NarrativeQuery, NarrativeResponse,
    Foreshadowing, CausalLink,
)
```

### 2.2 实例化

```python
engine = NarrativeEngine(llm_client=llm_client)  # llm_client 可选，None=仅 fallback
```

### 2.3 输入

```python
NarrativeQuery(
    chapter_text: str,              # 当前章节文本（≤4000 字自动截断）
    chapter_id: str,                # 章节标识，如 "ch_03"
    previous_chapters: list[dict],  # 前文章节摘要
    # [{"chapter_id": "ch_01", "summary": "...", "key_events": [...]}, ...]
    known_foreshadowings: list[Foreshadowing],  # 已知未回收伏笔（来自记忆）
)
```

### 2.4 输出

```python
NarrativeResponse(
    foreshadowings: list[Foreshadowing],       # 本章检测到的新伏笔 + 已回收的
    causal_links: list[CausalLink],            # 因果链
    unresolved_foreshadowings: list[Foreshadowing],  # 仍未回收的伏笔
    narrative_issues: list[str],               # 叙事问题（循环因果、伏笔遗忘等）
    event_prediction: str,                     # 短期情节推演文本
    confidence: float,                         # 0-1
    needs_human_review: bool,                  # confidence < 0.5 时为 True
)
```

### 2.5 辅助方法

```python
# 获取引擎内部伏笔注册表的所有未回收伏笔
engine.get_unresolved_foreshadowings() -> list[Foreshadowing]

# 手动标记伏笔已回收
engine.mark_resolved(foreshadow_id: str, chapter_id: str) -> bool
```

### 2.6 伏笔生命周期

```
planted → partial → resolved
   ↑ 埋下     ↑ 部分呼应    ↑ 完全回收
```

---

## 三、文辞引擎 (`src/engines/prose.py`)

### 3.1 导入

```python
from src.engines.prose import (
    ProseEngine, ProseQuery, ProseResponse,
    StyleMetrics, StyleDeviation,
)
```

### 3.2 实例化

```python
engine = ProseEngine(llm_client=llm_client)  # llm_client 可选
```

### 3.3 输入

```python
ProseQuery(
    text: str,                      # 待检测文本（≤4000 字自动截断）
    baseline_texts: list[str],      # 前 2-3 章文本用于建立风格基线
    chapter_id: str,                # 当前章节标识
)
```

### 3.4 输出

```python
ProseResponse(
    style_metrics: Optional[StyleMetrics],    # 当前文本的风格量化指标
    deviations: list[StyleDeviation],         # 偏离基线的段落
    register_consistency: float,              # 语域一致性 0-1
    character_voice_issues: list[str],        # 角色用语问题
    confidence: float,
    needs_human_review: bool,
)
```

**StyleMetrics 字段**：
| 字段 | 类型 | 含义 |
|------|------|------|
| `avg_sentence_length` | float | 平均句长（字符数） |
| `dialogue_ratio` | float | 对话占比 0-1 |
| `vocabulary_richness` | float | 词汇丰富度 0-1 |
| `register_level` | str | casual/informal/neutral/formal/literary |
| `rhetoric_density` | float | 修辞密度 0-1 |

**StyleDeviation 字段**：
| 字段 | 类型 | 含义 |
|------|------|------|
| `paragraph_index` | int | 偏离段落序号（0-based） |
| `snippet` | str | 偏离片段 |
| `deviation_type` | str | register/dialogue_ratio/sentence_length/vocabulary/rhetoric |
| `severity` | float | 严重程度 0-1 |
| `suggestion` | str | 修正建议 |

### 3.5 辅助方法

```python
# 获取当前作者风格基线
engine.get_baseline() -> Optional[StyleMetrics]
```

### 3.6 基线更新逻辑

- **首次调用**：从 `baseline_texts` 建立初始基线
- **后续调用**：移动平均更新（权重 α=0.3），缓慢适配风格演变
- 引擎内部自动维护，无需外部管理

---

## 四、情节记忆 (`src/memory/episodic_memory.py`)

### 4.1 导入

```python
from src.memory.episodic_memory import (
    EpisodicMemory, EpisodicQuery, EpisodicEntry, EpisodicStats,
)
```

### 4.2 实例化

```python
memory = EpisodicMemory(db_path="projects/memory/episodic.db")
# 自动创建目录和表结构
```

### 4.3 核心方法

#### 写入

```python
memory.write(
    chapter_id: str,         # 章节标识
    memory_type: str,        # behavior_log/world_event/pad_history/chapter_summary/conflict_resolution
    data: dict,              # 载荷数据（自动 JSON 序列化）
    character_id: str|None,  # 关联角色
    confidence: float,       # 置信度
) -> str                     # 返回条目 ID
```

#### 读取

```python
memory.read(EpisodicQuery(
    chapter_id: str|None,               # 单章查询
    chapter_range: tuple[str,str]|None,  # 范围查询
    character_id: str|None,             # 角色过滤
    memory_type: str|None,              # 类型过滤
    min_confidence: float,              # 最低置信度
    top_k: int,                         # 返回数量
)) -> list[EpisodicEntry]
```

#### 快捷查询

```python
# 获取章节摘要
memory.get_chapter_summary(chapter_id: str) -> Optional[dict]

# 获取角色相关历史（跨章节）
memory.get_character_history(character_id: str, top_k: int) -> list[EpisodicEntry]

# 获取指定章节前 N 章的 ID 列表
memory.get_chapters_since(chapter_id: str, limit: int) -> list[str]
```

### 4.4 因果图谱（Phase 2 新增）

```python
# 添加因果链
memory.add_causal_link(
    chapter_id: str,
    cause_event: str,
    effect_event: str,
    strength: float,      # 0-1
    description: str,
) -> str                  # 因果链 ID

# 获取因果链
memory.get_causal_links(chapter_id: str|None, top_k: int) -> list[dict]
```

### 4.5 伏笔登记表（Phase 2 新增）

```python
# 注册伏笔
memory.register_foreshadowing(
    foreshadow_id: str,
    chapter_id: str,
    description: str,
    hint_text: str,
    category: str,  # character/event/object/dialogue/setting
    related_characters: list[str]|None,
    confidence: float,
) -> str

# 标记回收
memory.resolve_foreshadowing(foreshadow_id: str, resolved_in: str) -> bool

# 获取未回收列表
memory.get_unresolved_foreshadowings() -> list[dict]
```

### 4.6 统计

```python
stats = memory.get_stats()
# EpisodicStats(total_entries, hot_entries, cold_entries, chapters_covered, db_size_bytes)
```

---

## 五、永久记忆 (`src/memory/permanent_memory.py`)

### 5.1 导入

```python
from src.memory.permanent_memory import (
    PermanentMemory, AuthorFingerprint, CharacterArchetype, WorldRulePattern,
)
```

### 5.2 实例化

```python
memory = PermanentMemory(db_path="projects/memory/permanent.db")
```

### 5.3 作者指纹

```python
# 更新（移动平均，首次直接赋值）
fingerprint = memory.update_fingerprint({
    "avg_sentence_length": 25.0,
    "dialogue_ratio": 0.3,
    "vocabulary_richness": 0.65,
    "register_level": "literary",
    "rhetoric_density": 0.4,
})
# → AuthorFingerprint(total_chapters_analyzed=N, ...)

# 读取
fp = memory.get_fingerprint()  # Optional[AuthorFingerprint]
```

### 5.4 角色原型库

```python
# 保存
arch = CharacterArchetype(
    label="叛逆公子",
    pad_baseline={"pleasure": 0.2, "arousal": 0.6, "dominance": 0.7},
    behavior_patterns=["反抗权威", "保护弱者"],
    typical_roles=["男主", "反英雄"],
    appearances_across_works=3,
)
arch_id = memory.save_archetype(arch)

# 获取单个
memory.get_archetype(arch_id) -> Optional[CharacterArchetype]

# 列表（按出现次数降序）
memory.list_archetypes(min_appearances=1, top_k=20) -> list[CharacterArchetype]
```

### 5.5 世界规则模式

```python
# 保存
rule = WorldRulePattern(
    rule_category="power_system",  # power_system/spatial/social/economy
    pattern_description="修炼境界分为九层，每层突破需渡劫",
    examples=["筑基→金丹→元婴→..."],
    usage_count=3,
)
rule_id = memory.save_rule_pattern(rule)

# 搜索
memory.find_similar_rules(rule_category="power_system", keyword="修炼") -> list[WorldRulePattern]
```

### 5.6 主动遗忘

```python
# 衰减高频未访问的数据（建议定期调用，如每次启动时）
removed = memory.prune_stale_data(days_threshold=30)  # 30 天未访问 → 计数衰减
```

---

## 六、编排器集成点

### 6.1 路由表（已配置）

```python
ROUTE_MAP = {
    "narrative":    ["narrative_engine"],                                      # 仅叙事
    "prose":        ["prose_engine"],                                          # 仅文辞
    "full_analyze": ["character_engine", "world_engine", "narrative_engine", "prose_engine"],
}
```

### 6.2 编排器实例化（扩展后）

```python
from src.engines.narrative import NarrativeEngine
from src.engines.prose import ProseEngine

orchestrator = Orchestrator(
    character_engine=CharacterEngine(llm_client=llm),
    world_engine=WorldEngine(llm_client=llm),
    narrative_engine=NarrativeEngine(llm_client=llm),  # Phase 2 新增
    prose_engine=ProseEngine(llm_client=llm),           # Phase 2 新增
    guardian=ConsistencyGuardian(),
)
```

### 6.3 Action payload 约定

**narrative action**:
```json
{
  "type": "narrative",
  "payload": {
    "chapter_text": "...",
    "chapter_id": "ch_03",
    "previous_chapters": [{"chapter_id": "ch_01", "summary": "...", "key_events": ["..."]}],
    "known_foreshadowings": [...]
  }
}
```

**prose action**:
```json
{
  "type": "prose",
  "payload": {
    "chapter_text": "...",
    "baseline_texts": ["前章文本1", "前章文本2"],
    "chapter_id": "ch_03"
  }
}
```

---

## 七、待实践者接入

以下是 Phase 2 模块已就绪但尚未接入 API 层的部分：

### 7.1 建议新增的 API 端点

| Method | Path | 用途 | 调用引擎 |
|--------|------|------|---------|
| POST | `/api/narrative/analyze` | 叙事分析 | narrative_engine |
| POST | `/api/prose/analyze` | 文风分析 | prose_engine |
| GET | `/api/memory/episodic/:chapter_id` | 查询情节记忆 | episodic_memory |
| GET | `/api/memory/permanent/fingerprint` | 获取作者指纹 | permanent_memory |

### 7.2 前端可接入的新数据

- `NarrativeResponse` — 伏笔卡片、因果链可视化、情节推演面板
- `ProseResponse` — 风格偏离标记、语域一致性指示器
- `AuthorFingerprint` — 仪表盘展示作者风格画像

### 7.3 守卫维度更新

当前守卫已注册 6 个维度，但 Phase 2 新增的 `foreshadowing`/`causal`/`narrative_consistency` 三个维度的检查逻辑目前为 pass-through（见 `guardian.py` L148-153 的 else 分支）。建议补充实际校验逻辑：

```python
# guardian.py _check_dimension() 中需要补充:
if dimension == "foreshadowing":
    return self._check_foreshadowing(engine_results)
elif dimension == "causal":
    return self._check_causal(engine_results)
elif dimension == "narrative_consistency":
    return self._check_narrative_consistency(engine_results)
```

---

## 八、LLM 任务类型注册表

协作者新增的 task_type（已同步注册三处）：

| task_type | System Prompt | Format 函数 | Phase |
|-----------|-------------|-------------|-------|
| `foreshadow_detect` | `FORESHADOW_DETECT_SYSTEM` | `format_foreshadow_prompt()` | Phase 2 |
| `causal_extract` | `CAUSAL_EXTRACT_SYSTEM` | `format_causal_prompt()` | Phase 2 |
| `resolution_check` | `RESOLUTION_CHECK_SYSTEM` | `format_resolution_check_prompt()` | Phase 2 |
| `event_predict` | `EVENT_PREDICT_SYSTEM` | `format_event_predict_prompt()` | Phase 2 |
| `style_check` | `STYLE_CHECK_SYSTEM` | `format_style_prompt()` | Phase 2 |
| `register_check` | `REGISTER_CHECK_SYSTEM` | `format_register_prompt()` | Phase 2 |

---

## 九、已知局限

| 模块 | 局限 | 建议 |
|------|------|------|
| 叙事引擎 | Fallback 模式（无 LLM）仅做关键词匹配，准确率极低 | 测试时确保 LLM 可用 |
| 文辞引擎 | 中文引号检测在 fallback 模式不完善 | 对话占比在 LLM 模式下才准确 |
| 情节记忆 | 热缓存仅支持单章节 key 查找，不支持跨章节复合查询 | 跨章节用 `read()` 直接走 SQLite |
| 永久记忆 | Phase 2 无向量检索（LanceDB 留待 Phase 3） | 原型搜索仅支持 SQL LIKE |
| 引擎间联动 | 叙事引擎和文辞引擎尚未共享上下文 | 编排器层面可串联，但需要设计数据流 |

---

## 十、版本信息

| 项目 | 值 |
|------|-----|
| 创建日期 | 2026-06-11 |
| Phase | Phase 2 原型就绪 |
| 文档维护 | 协作者 |
| 下次更新 | 实践者接入后反馈修改 |
