# 模块接口契约

> **规则**：模块之间只通过契约交互。接口冻结后，内部实现可以独立推进。
> **标记说明**：`[Phase 1]` = MVP 实现；`[Phase 2+]` = 后续阶段

---

## 角色引擎 (Character Engine) `[Phase 1]`

**职责**：模拟角色在特定情境下的行为反应，基于语料行为模式而非标签推理。

**输入**：
```python
@dataclass
class CharacterQuery:
    character_id: str          # 角色唯一标识
    scene_text: str            # 当前场景文本
    emotion_context: EmotionContext | None  # 情感上下文（可选，由编排器提供）
```

**输出**：
```python
@dataclass
class CharacterResponse:
    pad_state: PADState        # Pleasure-Arousal-Dominance 三维情感坐标
    behavior_prediction: BehaviorPrediction  # 预测行为 + 置信度
    implicit_triggers: list[str]  # 被触发的隐性记忆标签
    confidence: float          # 整体置信度 0-1
    needs_human_review: bool   # 置信度 < 0.5 时为 True
```

**依赖**：语料锚定层（行为模式检索）、工作记忆（当前 PAD 状态）、世界引擎（设定规则校验）

**契约**：不直接修改记忆，只返回建议；记忆更新由编排器统一写入；置信度 < 0.5 时必须返回 `needs_human_review=True`

---

## 世界引擎 (World Engine) `[Phase 1]`

**职责**：校验事件是否符合世界观设定（力量体系、空间规则、社会结构等）。

**输入**：
```python
@dataclass
class WorldQuery:
    event_description: str     # 事件描述
    location: str              # 发生地点
    involved_characters: list[str]  # 涉及角色 ID 列表
```

**输出**：
```python
@dataclass
class WorldResponse:
    rule_checks: list[RuleCheck]       # 规则校验结果
    spatial_consistency: bool           # 空间一致性
    power_level_validation: PowerLevel  # 力量等级校验
```

**依赖**：无（只读设定库）

**契约**：设定库由人类作者维护，引擎只查询不修改；规则冲突时返回 `conflict` 状态 + 冲突详情，不做自动裁决

---

## 语料锚定层 (Corpus Anchor) `[Phase 1]`

**职责**：提供语料向量检索服务，为其他引擎提供行为模式和设定规则的语料支撑。

**输入**：
```python
@dataclass
class CorpusQuery:
    text: str                  # 待检索文本片段
    category: str              # 检索类别（behavior / emotion / scene / world_rule）
    character_id: str | None   # 可选：限定角色范围
    top_k: int = 3             # 返回数量
```

**输出**：
```python
@dataclass
class CorpusResponse:
    hits: list[CorpusHit]      # 命中的语料切片（每片 500 字，场景级）
    similarity_scores: list[float]  # 相似度分数
```

**依赖**：LanceDB（向量存储）

**契约**：只做检索，不做语料修改；相似度 < 0.3 的结果不返回（噪声过滤）；切片标准 500 字场景级（ADR-013）

---

## 级联修正器 (Cascade Fixer) — Phase 1 简化版 `[Phase 1]`

> v3.1 重命名：原"影响雷达 (Impact Radar)"。Phase 1 仅做关键词扫描 + 待办清单生成，不做因果推理。

**职责**：基于关键词匹配和实体引用扫描，检测文本修改可能影响的章节，生成待办清单。

**输入**：
```python
@dataclass
class CascadeQueryLite:
    changed_text: str          # 被修改的文本片段
    chapter_id: str            # 所在章节
    entity_refs: list[str]     # 修改涉及的实体名（角色名/地名/物品名等）
```

**输出**：
```python
@dataclass
class CascadeResponseLite:
    matched_chapters: list[MatchedChapter]  # 包含相同实体的章节
    match_type: str            # "entity_match" / "keyword_match"
    todo_items: list[TodoItem] # 待办清单（供作者逐条处理）
    alarm_level: str           # "info" / "warn" — Phase 1 不产生 critical
```

**依赖**：情节记忆（章节实体索引）

**契约**：只做关键词/实体匹配，不做因果推理；不自动修正正文；生成待办清单供作者逐条确认

---

## 级联修正器 (Cascade Fixer) — 完整版 `[Phase 2+]`

> Phase 2+ 升级：从关键词扫描升级为因果推理 + 影响传播分析。

**职责**：检测文本修改对已写章节的级联影响，基于因果图谱进行影响传播分析，生成修复方案建议。

**输入**：
```python
@dataclass
class CascadeQuery:
    changed_text: str          # 被修改的文本片段
    chapter_id: str            # 所在章节
    change_type: str           # "character_behavior" / "world_rule" / "plot_point" / "setting"
```

**输出**：
```python
@dataclass
class CascadeResponse:
    direct_hits: list[DirectHit]         # 直接冲突（必须处理）
    indirect_risks: list[IndirectRisk]   # 间接风险（建议检查）
    impact_level: str          # "low" / "medium" / "high" / "critical"
    suggested_actions: list[SuggestedAction]  # 建议的修复动作
    alarm_level: str           # 映射到守卫三级警报：info / warn / critical
```

**依赖**：情节记忆（已写章节索引和因果图谱）

**契约**：只做影响报告和修复建议，不做自动修正；`critical` 级别必须阻断编排器流程，等待人类确认

---

## 编排器 (Orchestrator) `[Phase 1]`

**职责**：接收用户操作，路由到相应引擎，协调引擎返回结果，统一写入记忆。唯一有记忆写入权限的模块。

**输入**：
```python
@dataclass
class UserAction:
    type: str                  # "analyze" / "check" / "predict" / "impact" / "finalize"
    payload: dict              # 根据 type 路由到不同引擎
```

**输出**：
```python
@dataclass
class ExecutionPlan:
    engines_to_call: list[str]  # 需要调用的引擎列表
    call_order: list[str]       # 调用顺序
    fallback_strategy: str      # 失败降级策略
```

**Phase 1 路由规则**：
```python
ROUTE_MAP = {
    "analyze":  ["character_engine", "world_engine"],  # 全量分析
    "check":    ["world_engine"],                       # 设定校验
    "predict":  ["character_engine"],                   # 行为预测
    "impact":   ["cascade_fixer"],                      # 级联影响检查（Phase 1 简化版：关键词扫描+待办清单）
    "finalize": ["character_engine", "world_engine"],   # 章节定稿并行
}
```

**契约**：所有引擎返回后，由一致性守卫交叉验证；验证通过后统一写入记忆，不允许多个引擎直接写记忆；单引擎超时 30s 触发降级

---

## 叙事引擎 (Narrative Engine) `[Phase 2+]`

**职责**：追踪伏笔埋设与回收、管理因果链、校验情节逻辑一致性。

**输入**：
```python
@dataclass
class NarrativeQuery:
    chapter_id: str            # 当前章节
    plot_points: list[str]     # 情节节点列表
    foreshadowing_refs: list[str] | None  # 已埋伏笔引用
```

**输出**：
```python
@dataclass
class NarrativeResponse:
    unresolved_foreshadowing: list[ForeshadowingItem]  # 未回收伏笔
    causality_conflicts: list[CausalityConflict]       # 因果冲突
    plot_arc_deviation: float   # 情节弧偏差度 0-1
    suggestions: list[str]      # 叙事建议
```

**依赖**：情节记忆（因果图谱和伏笔登记表）

**契约**：不自动修改情节结构；发现未回收伏笔时生成提醒，不强制处理

---

## 文辞引擎 (Prose Engine) `[Phase 2+]`

**职责**：检测文风一致性（语域、句式、修辞密度），标记风格漂移。

**输入**：
```python
@dataclass
class ProseQuery:
    text: str                  # 待检测文本
    baseline_chapter_ids: list[str]  # 用于建立风格基线的章节
```

**输出**：
```python
@dataclass
class ProseResponse:
    style_metrics: StyleMetrics       # 风格量化指标
    deviations: list[StyleDeviation]  # 偏离基线的段落
    register_consistency: float       # 语域一致性 0-1
```

**依赖**：永久记忆（作者指纹基线）

**契约**：只检测和报告，不做自动改写；风格建议仅供参考

---

## 主题引擎 (Theme Engine) `[Phase 3+]`

**职责**：从文本中提取主题、追踪主题演变、检测主题一致性。

**输入**：
```python
@dataclass
class ThemeQuery:
    chapter_ids: list[str]     # 待分析的章节范围
    theme_hints: list[str] | None  # 作者预设主题（可选）
```

**输出**：
```python
@dataclass
class ThemeResponse:
    identified_themes: list[Theme]       # 识别到的主题
    theme_evolution: list[ThemeChange]   # 主题演变记录
    consistency_alerts: list[ThemeAlert] # 主题偏离警告
```

**依赖**：情节记忆（章节内容摘要）

**契约**：主题提取结果供作者参考，不强制对齐预设主题

---

## 经济引擎 (Economy Engine) `[Phase 3+]`

**职责**：校验世界观中经济/资源系统的内部一致性。

**输入**：
```python
@dataclass
class EconomyQuery:
    chapter_id: str            # 当前章节
    resource_events: list[ResourceEvent]  # 资源变动事件
```

**输出**：
```python
@dataclass
class EconomyResponse:
    resource_inconsistencies: list[ResourceConflict]  # 资源矛盾
    economic_balance: float    # 经济平衡度 0-1
```

**依赖**：世界引擎（设定库中的经济规则）、情节记忆（历史资源状态）

**契约**：只校验不修改设定；资源系统规则由作者在设定库中维护

---

## 读者预期引擎 (Reader Expectation Engine) `[Phase 3+]`

**职责**：建模"读者已知信息 vs 角色已知信息"，管理悬念和信息差。

**输入**：
```python
@dataclass
class ReaderExpectationQuery:
    chapter_id: str
    revealed_info: list[str]   # 本章向读者揭示的信息
    character_knowledge: dict[str, list[str]]  # 各角色已知信息
```

**输出**：
```python
@dataclass
class ReaderExpectationResponse:
    knowledge_gaps: list[KnowledgeGap]      # 读者-角色信息差
    suspense_quality: SuspenseMetrics       # 悬念质量评估
    spoiler_risks: list[SpoilerRisk]        # 意外剧透风险
```

**依赖**：情节记忆（已揭示信息登记表）

**契约**：信息差分析供作者参考，不做自动修改

---

## 构思引擎 (Conception Engine) `[Phase 3+]`

**职责**：管理意象体系（符号、隐喻、意象网络），辅助意象一致性。

**输入**：
```python
@dataclass
class ConceptionQuery:
    text: str                  # 待分析文本
    imagery_catalog: list[str] | None  # 已有意象目录
```

**输出**：
```python
@dataclass
class ConceptionResponse:
    detected_imagery: list[ImageryItem]   # 检测到的意象使用
    imagery_network: ImageryGraph         # 意象关联图
    consistency_notes: list[str]          # 一致性备注
```

**依赖**：永久记忆（意象库）

**契约**：只做意象检测和关联分析，不做自动替换

---

## 全局记忆系统 (Memory System) `[Phase 1 简化版]`

### 三层模型

```
工作记忆 (Working Memory)        ← 会话级，内存存储，快速读写
    ↓ 章节结束时下沉
情节记忆 (Episodic Memory)       ← 章节级，SQLite，近 10 章热数据
    ↓ 跨书沉淀
永久记忆 (Permanent Memory)       ← 跨书级，SQLite+LanceDB，冷热分层
```

### 写入接口（仅供编排器调用）

```python
@dataclass
class MemoryWrite:
    source_engine: str         # 来源引擎
    target_tier: str           # "working" / "episodic" / "permanent"
    memory_type: str           # "pad_state" / "behavior_log" / "world_event" / "plot_event"
    data: dict                 # 具体数据
    confidence: float          # 置信度标签
    timestamp: datetime
```

### 读取接口（所有引擎可读）

```python
@dataclass
class MemoryQuery:
    tier: str                  # "working" / "episodic" / "permanent" / "all"
    character_id: str | None
    chapter_range: tuple[str, str] | None
    time_range: tuple[datetime, datetime] | None
    memory_type: str | None
    top_k: int = 10
```

### 各层保留策略

| 层级 | 容量 | 保留策略 | 存储 |
|------|------|---------|------|
| 工作记忆 | 当前会话 | 会话结束清空 | 内存 |
| 情节记忆 | 近 10 章（热）+ 全量（冷） | 10 章后下沉冷存储 | SQLite |
| 永久记忆 | 不限 | 主动遗忘 + 多级摘要 | SQLite + LanceDB |

**契约**：只有编排器有写入权限；读取无限制，返回数据必须带 `last_modified` 时间戳；工作记忆不持久化

---

## 一致性守卫 (Consistency Guardian) `[Phase 1 简化版]`

### 八维检查维度（Phase 1 仅激活前 3 维）

| 维度 | 中文名 | Phase | 检查内容 |
|------|--------|-------|---------|
| 1. character | 角色行为 | Phase 1 | 行为是否符合语料模式 |
| 2. world_rule | 世界规则 | Phase 1 | 是否符合设定库规则 |
| 3. spatial | 空间一致 | Phase 1 | 地点/移动逻辑是否合理 |
| 4. temporal | 时间一致 | Phase 2+ | 时间线是否自洽 |
| 5. power | 力量体系 | Phase 2+ | 修为/能力是否一致 |
| 6. relationship | 关系网络 | Phase 2+ | 角色关系演变是否合理 |
| 7. causality | 因果逻辑 | Phase 2+ | 事件因果链是否完整 |
| 8. style | 风格一致 | Phase 2+ | 文风/语域是否一致 |

### 三级警报

| 级别 | 标识 | 含义 | 行为 |
|------|------|------|------|
| **INFO** | 🔵 | 提醒，无冲突 | 仅记录日志，不阻断 |
| **WARN** | 🟡 | 软冲突，可能是创作意图 | 突出显示给用户，不阻断流程 |
| **CRITICAL** | 🔴 | 硬冲突，必须处理 | 阻断编排器流程，需人类确认后继续 |

### 创作意图标记

作者可在正文中插入意图标记，守卫识别后降低对应维度的警报级别：
```
<!-- INTENT: character-deviation -->  ← 标记此处为有意角色偏差
<!-- INTENT: world-rule-bend -->      ← 标记此处为有意规则弯曲
```

### 输入/输出

**输入**：
```python
@dataclass
class GuardianInput:
    engine_results: dict[str, Any]    # 各引擎的返回结果
    intent_markers: list[IntentMarker] | None  # 检测到的意图标记
    active_dimensions: list[str]      # 本次激活的维度
```

**输出**：
```python
@dataclass
class GuardianOutput:
    is_consistent: bool               # 整体是否一致
    dimension_results: dict[str, DimensionResult]  # 各维度结果
    alarm_level: str                  # 最高警报级别
    conflicts: list[Conflict]         # 冲突详情列表
    action_required: str              # "none" / "review" / "block"
```

**契约**：守卫不修改引擎输出，只做交叉验证；CRITICAL 警报必须阻断后续记忆写入；Phase 1 只检查 3 个维度
