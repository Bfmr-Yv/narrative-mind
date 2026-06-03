# 级联修正器卡片 `[Phase 1 简化版 + Phase 2+ 完整版]`

> **v3.1 重命名**：原"影响雷达 (Impact Radar)"。
> Phase 1：关键词扫描 + 待办清单生成。
> Phase 2+：因果推理 + 影响传播分析 + 修复方案建议。

## 职责

**Phase 1（简化版）**：基于关键词匹配和实体引用扫描，检测文本修改可能影响的章节，生成待办清单。不做因果推理。

**Phase 2+（完整版）**：基于因果图谱进行级联影响传播分析，生成修复方案建议。

## 当前状态
- [ ] Phase 1 简化版：关键词扫描 + 实体匹配
- [ ] Phase 1 简化版：待办清单生成
- [ ] Phase 2+：因果图谱构建
- [ ] Phase 2+：影响传播算法
- [x] 接口契约已冻结（Phase 1 + Phase 2+）
- [ ] Prompt v1 编写

## 输入/输出

### Phase 1 简化版

**输入**：`CascadeQueryLite { changed_text, chapter_id, entity_refs }`

**输出**：`CascadeResponseLite { matched_chapters, match_type, todo_items, alarm_level }`

### Phase 2+ 完整版

**输入**：`CascadeQuery { changed_text, chapter_id, change_type }`

**输出**：`CascadeResponse { direct_hits, indirect_risks, impact_level, suggested_actions, alarm_level }`

详见 `02-CONTRACTS.md` — 级联修正器契约

## 依赖模块
- 情节记忆（章节实体索引，Phase 1）
- 情节记忆（因果图谱，Phase 2+）

## 影响等级定义

| 等级 | 条件 | 处理方式 | 守卫警报 |
|------|------|---------|---------|
| `low` | 仅影响当前章节 | 提示但不阻断 | 🔵 INFO |
| `medium` | 影响 1-3 个相邻章节 | 建议审查 | 🟡 WARN |
| `high` | 影响 >3 个章节或涉及主线 | 强烈建议审查 | 🟡 WARN |
| `critical` | 涉及世界观或核心角色设定 | 阻断流程，必须人类确认 | 🔴 CRITICAL |

## Phase 1 简化版流程（伪代码）

```python
def detect_impact_lite(query: CascadeQueryLite) -> CascadeResponseLite:
    # 1. 从修改文本中提取实体名
    entities = extract_entities(query.entity_refs)

    # 2. 在情节记忆中扫描包含相同实体的章节
    matched = []
    for chapter in memory.get_all_chapters():
        for entity in entities:
            if entity in chapter.entity_index:
                matched.append(MatchedChapter(
                    chapter_id=chapter.id,
                    matched_entity=entity,
                    match_type="entity_match"
                ))

    # 3. 生成待办清单
    todo_items = [TodoItem(
        chapter_id=m.chapter_id,
        description=f"检查第{m.chapter_id}章中'{m.matched_entity}'相关段落",
        severity="suggested"
    ) for m in matched]

    # 4. 确定警报级别（Phase 1 最多 WARN，不产生 CRITICAL）
    alarm = "warn" if len(matched) > 3 else "info"

    return CascadeResponseLite(
        matched_chapters=matched,
        match_type="entity_match",
        todo_items=todo_items,
        alarm_level=alarm
    )
```

## 阻塞问题
- 章节实体索引的构建和更新策略
- Phase 2+ 因果图谱的建模方式（事件节点+因果边）
- 影响传播的深度限制（最多追溯几层？）

## 设计笔记
- 只做报告，不做自动修正（ADR-003）
- `critical` 级别必须阻断编排器流程（ADR-008）
- Phase 1 简化版不产生 critical 警报（因果推理能力不足）
- 影响报告存入情节记忆，供后续分析
- 前端呈现为待办清单（Todo List），作者手动逐条处理
