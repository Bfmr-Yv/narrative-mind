# 全局记忆系统：三层模型

> **Phase 1**：工作记忆 + 简化情节记忆（近 10 章）。
> **Phase 2+**：完整三层模型 + 主动遗忘 + 冷存储。

---

## 三层架构全景

```
┌─────────────────────────────────────────────────────────────┐
│                    工作记忆 (Working Memory)                  │
│                                                                          │
│  范围：当前编辑会话                                                    │
│  存储：内存（不持久化）                                                │
│  容量：会话级，会话结束清空                                           │
│                                                                          │
│  内容：                                                                  │
│  · 当前场景上下文 (scene_context)                                      │
│  · 活跃角色 PAD 状态 (active_pad_states)                               │
│  · 待处理冲突列表 (pending_conflicts)                                  │
│  · 最近 N 条用户操作 (recent_actions)                                  │
│  · 临时分析缓存 (analysis_cache)                                      │
│                                                                          │
│  读写：所有引擎可读，编排器可写                                        │
│  延迟：<10ms                                                                 │
└────────────────────────┬────────────────────────────────────┘
                         │ 章节结束时下沉
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    情节记忆 (Episodic Memory)                 │
│                                                                          │
│  范围：当前作品的所有章节                                             │
│  存储：SQLite（热数据：近 10 章）+ 冷存储（10 章前）                   │
│  容量：全量章节                                                        │
│                                                                          │
│  内容：                                                                  │
│  · 章节内容摘要 (chapter_summaries)                                    │
│  · 角色行为日志 (behavior_logs)                                        │
│  · 世界事件记录 (world_events)                                         │
│  · PAD 情感历史 (pad_history)                                          │
│  · 决策结果 (decision_outcomes)                                        │
│  · 冲突解决记录 (conflict_resolutions)                                 │
│  · 因果图谱 (causality_graph) `[Phase 2+]`                              │
│  · 伏笔登记表 (foreshadowing_registry) `[Phase 2+]`                     │
│  · 章节实体索引 (chapter_entity_index)                                 │
│                                                                          │
│  读写：引擎可读，编排器可写（经守卫校验后）                              │
│  延迟：<100ms（热），<1s（冷）                                                │
└────────────────────────┬────────────────────────────────────┘
                         │ 跨书沉淀
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    永久记忆 (Permanent Memory)                │
│                                                                          │
│  范围：跨作品                                                          │
│  存储：SQLite（结构化）+ LanceDB（向量）                                │
│  容量：不限                                                            │
│                                                                          │
│  内容：                                                                  │
│  · 角色原型库 (character_archetypes)                                   │
│  · 世界规则模式 (world_rule_patterns)                                  │
│  · 类型特征 (genre_profiles)                                           │
│  · 作者指纹 (author_fingerprint)                                       │
│  · 意象库 (imagery_catalog)                                            │
│  · 成功/失败模式 (success_failure_patterns)                            │
│                                                                          │
│  读写：编排器可写，所有引擎可读                                        │
│  延迟：<500ms                                                               │
│  维护策略：主动遗忘 + 多级摘要 + 冷热分层                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 写入接口（仅供编排器调用）

```python
@dataclass
class MemoryWrite:
    source_engine: str         # 来源引擎标识
    target_tier: str           # "working" | "episodic" | "permanent"
    memory_type: str           # 数据类型标签
    data: dict                 # 载荷数据
    confidence: float          # 置信度标签 [0, 1]
    timestamp: datetime        # 写入时间
    ttl: int | None            # 生存时间（秒），None = 永久
```

### 写入权限矩阵

| 操作 | 工作记忆 | 情节记忆 | 永久记忆 |
|------|---------|---------|---------|
| 编排器写入 | ✅ | ✅（经守卫校验） | ✅（Phase 2+） |
| 引擎直接写入 | ❌ | ❌ | ❌ |
| 用户手动写入 | ✅ | ✅ | ❌ |

---

## 读取接口（所有引擎可读）

```python
@dataclass
class MemoryQuery:
    tier: str                  # "working" | "episodic" | "permanent" | "all"
    character_id: str | None   # 按角色过滤
    chapter_range: tuple[str, str] | None  # 章节范围
    time_range: tuple[datetime, datetime] | None  # 时间范围
    memory_type: str | None    # 按类型过滤
    top_k: int = 10            # 返回数量上限
    min_confidence: float = 0.0  # 最低置信度
```

```python
@dataclass
class MemoryResult:
    items: list[MemoryItem]
    total_count: int
    query_time_ms: float
```

---

## 各层保留策略

| 层级 | 容量 | 热数据 | 冷数据 | 清理策略 |
|------|------|--------|--------|---------|
| 工作记忆 | 当前会话 | 全部 | 无 | 会话结束清空 |
| 情节记忆 | 不限 | 近 10 章 | 10 章前 | 冷数据压缩存储；手动归档 |
| 永久记忆 | 不限 | 高频访问 | 低频访问 | 主动遗忘（超过 30 天未访问）；多级摘要替代原文 |

---

## Phase 1 简化实现

Phase 1 仅实现：
- **工作记忆**：内存 dict，存储当前 PAD 状态 + 场景上下文
- **情节记忆**：SQLite 单表，存储近 10 章的行为日志 + 实体索引
- **暂不实现**：永久记忆、因果图谱、伏笔登记表、冷热分层

### Phase 1 情节记忆表结构

```sql
CREATE TABLE episodic_memory (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,   -- "behavior_log" | "world_event" | "entity_index"
    character_id TEXT,
    data JSON NOT NULL,
    confidence REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_episodic_chapter ON episodic_memory(chapter_id);
CREATE INDEX idx_episodic_character ON episodic_memory(character_id);
CREATE INDEX idx_episodic_type ON episodic_memory(memory_type);
```

---

## 与一致性守卫的关系

```
引擎输出
    │
    ▼
一致性守卫交叉验证
    │
    ├─► 通过 → 编排器写入记忆（标记 confidence 为守卫评估值）
    ├─► WARN → 编排器写入记忆 + 附加警告标签
    └─► CRITICAL → 拒绝写入，返回冲突报告，等待人类裁决
```

守卫的置信度评估直接影响记忆写入的 `confidence` 标签，后续检索时可按 `min_confidence` 过滤低置信度记忆。

---

## 设计笔记

- 所有记忆读取返回的数据必须带 `last_modified` 时间戳
- 引擎不可绕过编排器直接写记忆（契约强制，非约定）
- 工作记忆的临时性意味着：关闭应用后，未下沉到情节记忆的数据丢失
- 永久记忆的"主动遗忘"机制：定期清理低频访问数据，保留多级摘要
- 跨书永久记忆使得后续作品的 GenreProfile 和 AuthorFingerprint 可以持续累积
