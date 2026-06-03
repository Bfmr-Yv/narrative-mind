# 一致性守卫

> **Phase 1**：仅激活 3 维（角色行为 / 世界规则 / 空间一致），二级警报（WARN / CRITICAL）。
> **Phase 2+**：完整八维 + 三级警报 + 意图标记系统。

---

## 守卫在架构中的位置

```
角色引擎输出 ──┐
               ├──► 一致性守卫 ──► 通过 → 编排器写入记忆
世界引擎输出 ──┘                  │
                                  ├─► WARN → 写入+警告标签
                                  └─► CRITICAL → 阻断，返回冲突报告
```

守卫是所有引擎输出进入记忆系统之前的**唯一校验门**。用户操作（编辑、定稿）的结果也必须经过守卫才能写入情节记忆。

---

## 八维检查维度

| # | 维度 | 中文名 | Phase | 检查内容 | 数据来源 |
|---|------|--------|-------|---------|---------|
| 1 | character | 角色行为 | Phase 1 | 行为是否符合语料模式 + PAD 情感轨迹 | 角色引擎 |
| 2 | world_rule | 世界规则 | Phase 1 | 是否符合设定库中的规则 | 世界引擎 |
| 3 | spatial | 空间一致 | Phase 1 | 地点/移动逻辑是否合理 | 世界引擎 |
| 4 | temporal | 时间一致 | Phase 2+ | 时间线是否自洽，有无时间矛盾 | 情节记忆 |
| 5 | power | 力量体系 | Phase 2+ | 修为/能力等级是否一致 | 世界引擎 |
| 6 | relationship | 关系网络 | Phase 2+ | 角色关系演变是否合理 | 情节记忆 |
| 7 | causality | 因果逻辑 | Phase 2+ | 事件因果链是否完整 | 叙事引擎 |
| 8 | style | 风格一致 | Phase 2+ | 文风/语域是否一致 | 文辞引擎 |

---

## 三级警报

| 级别 | 标识 | 含义 | 系统行为 | 用户感知 |
|------|------|------|---------|---------|
| **INFO** | 🔵 | 提醒，无冲突 | 仅记录日志，不阻断流程 | 可选查看 |
| **WARN** | 🟡 | 软冲突，可能是创作意图 | 高亮显示，允许继续 | 建议审查，可一键忽略 |
| **CRITICAL** | 🔴 | 硬冲突，必须处理 | 阻断记忆写入，暂停流程 | 必须确认或修改后才能继续 |

### 警报升级规则

```
单维度 WARN × 3 次累积 → 升级为该维度 CRITICAL
同一角色/规则 WARN × 2 次累积 → 升级为 CRITICAL
任意维度 CRITICAL → 全局阻断
```

---

## 创作意图标记

作者可在正文中插入意图标记，守卫识别后：

- 降低对应维度的警报级别（CRITICAL → WARN，WARN → INFO）
- 记录标记位置和类型，供后续分析

```
<!-- INTENT: character-deviation -->  角色行为偏差是有意的
<!-- INTENT: world-rule-bend -->      世界规则弯曲是有意的
<!-- INTENT: style-shift -->          风格变化是有意的
<!-- INTENT: timeline-flashback -->   时间线跳跃是有意的
```

标记的生效范围：从标记位置到下一个 `<!-- /INTENT -->` 或章节结束。

---

## Phase 1 交叉验证逻辑（伪代码）

```python
def consistency_guard(results: dict, active_dimensions: list[str]) -> GuardianOutput:
    dimension_results = {}
    conflicts = []

    # 维度 1: 角色行为一致性
    if "character" in active_dimensions:
        char_result = results.get("character_engine")
        if char_result and char_result.confidence < 0.5:
            conflicts.append(Conflict(
                dimension="character",
                level="WARN",
                detail=f"角色行为预测置信度过低 ({char_result.confidence})",
                suggestion="建议人工审查该角色的行为是否合理"
            ))
        if char_result and char_result.needs_human_review:
            conflicts.append(Conflict(
                dimension="character",
                level="WARN",
                detail="角色引擎标记为需要人工审查"
            ))

    # 维度 2: 世界规则一致性
    if "world_rule" in active_dimensions:
        world_result = results.get("world_engine")
        if world_result:
            for check in world_result.rule_checks:
                if check.status == "conflict":
                    conflicts.append(Conflict(
                        dimension="world_rule",
                        level="CRITICAL",
                        detail=check.detail,
                        rule_id=check.rule_id
                    ))

    # 维度 3: 空间一致性
    if "spatial" in active_dimensions:
        world_result = results.get("world_engine")
        if world_result and not world_result.spatial_consistency:
            conflicts.append(Conflict(
                dimension="spatial",
                level="WARN",
                detail="空间逻辑可能不一致"
            ))

    # 汇总
    criticals = [c for c in conflicts if c.level == "CRITICAL"]
    warns = [c for c in conflicts if c.level == "WARN"]

    if criticals:
        alarm_level = "CRITICAL"
        action = "block"
    elif warns:
        alarm_level = "WARN"
        action = "review"
    else:
        alarm_level = "INFO"
        action = "none"

    return GuardianOutput(
        is_consistent=len(criticals) == 0,
        dimension_results=dimension_results,
        alarm_level=alarm_level,
        conflicts=conflicts,
        action_required=action
    )
```

---

## 冲突解决协议

1. 守卫生成冲突报告 → 提交给编排器
2. 编排器根据 `action_required` 决定：
   - `none`：正常写入记忆
   - `review`：写入记忆 + 前端高亮冲突卡片
   - `block`：拒绝写入，前端弹出冲突对话框
3. 用户处理选项：
   - **确认修改**：编辑文本后重新触发检查
   - **标记为意图**：插入 `<!-- INTENT -->` 标记，降低警报
   - **忽略此次**：强制写入（记录忽略日志）
4. 所有冲突处理结果记录到情节记忆

---

## 设计笔记

- 守卫不修改引擎输出，只做交叉验证
- CRITICAL 警报必须阻断记忆写入，防止错误记忆污染后续分析
- Phase 1 的 WARN 阈值设置偏宽松（宁可多报，不可漏报）
- 意图标记是作者与 AI 系统之间的"元通信"协议
- 所有冲突和处理结果记录到 `conflict_resolutions` 表，用于改进守卫阈值
