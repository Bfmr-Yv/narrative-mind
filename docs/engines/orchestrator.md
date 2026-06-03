# 编排器卡片 `[Phase 1]`

> **v3.1 更新**：路由表扩展到 8 引擎全景（6 个标记 Phase 2+）。记忆写入使用三层模型。一致性守卫独立为独立模块。

## 职责
接收用户操作，路由到相应引擎，协调引擎返回结果，统一写入记忆。**唯一有记忆写入权限的模块**。

## 当前状态
- [ ] 事件类型枚举
- [ ] 路由规则实现
- [ ] 一致性守卫调用逻辑（见 `06-CONSISTENCY-GUARDIAN.md`）
- [x] 接口契约已冻结
- [ ] Tier 0-4 降级策略实现（见 `04-COST-BUDGET.md`）

## 输入/输出

**输入**：`UserAction { type, payload }`

**输出**：`ExecutionPlan { engines_to_call, call_order, fallback_strategy }`

详见 `02-CONTRACTS.md` — 编排器契约

## 事件类型枚举（草案）

```python
class ActionType:
    ANALYZE = "analyze"      # 分析当前文本（角色+世界）
    CHECK = "check"          # 校验规则（世界引擎）
    PREDICT = "predict"      # 预测行为（角色引擎）
    IMPACT = "impact"        # 影响分析（级联修正器，Phase 1 简化版）
    FINALIZE = "finalize"    # 章节定稿（角色+世界并行）
```

## Phase 1 路由规则

```python
ROUTE_MAP = {
    "analyze":  ["character_engine", "world_engine"],
    "check":    ["world_engine"],
    "predict":  ["character_engine"],
    "impact":   ["cascade_fixer"],       # Phase 1 简化版：关键词扫描+待办清单
    "finalize": ["character_engine", "world_engine"],  # 并行调用
}
```

### 全景路由规则（含 Phase 2+ 引擎）

```python
ROUTE_MAP_FULL = {
    "write_paragraph":    ["character_engine", "prose_engine"],           # Phase 2+
    "modify_setting":     ["world_engine", "cascade_fixer"],              # Phase 2+
    "chapter_finalize":   ["character_engine", "world_engine",
                           "narrative_engine", "prose_engine",
                           "theme_engine"],                              # Phase 2+
    "full_review":        ["character_engine", "world_engine",
                           "narrative_engine", "prose_engine",
                           "theme_engine", "economy_engine"],            # Phase 3+
    "brainstorm":         ["conception_engine", "reader_expectation_engine"], # Phase 3+
    "world_building":     ["world_engine", "economy_engine"],             # Phase 3+
}
```

## 一致性守卫调用

编排器在所有引擎返回后调用一致性守卫（详见 `06-CONSISTENCY-GUARDIAN.md`）：
- Phase 1 激活 3 维：角色行为、世界规则、空间一致
- 守卫返回 CRITICAL → 阻断记忆写入，返回冲突报告
- 守卫返回 WARN → 写入记忆 + 附带提醒标记
- 守卫通过 → 正常写入记忆

## 记忆写入流程

```
一致性守卫通过
    │
    ├─► 写入工作记忆（当前 PAD 状态、场景上下文）
    ├─► 写入情节记忆（行为日志、世界事件、章节索引）
    └─► (Phase 2+) 下沉永久记忆（跨书模式、作者指纹）
```

详见 `05-MEMORY-SYSTEM.md` — 三层记忆模型

## 降级策略

| 场景 | Tier | 降级方式 |
|------|------|---------|
| 单引擎超时 (30s) | — | 跳过该引擎，返回部分结果 |
| 月度预算用至 50% | Tier 2→1 | 关闭非核心引擎，top-k 3→2 |
| 月度预算用至 80% | Tier 1→0 | 切换本地模型处理所有任务 |
| 月度预算用至 95% | 熔断 | 停止所有 API 调用，纯规则模式 |
| 向量检索失败 | — | 降级为关键词匹配 |

详见 `04-COST-BUDGET.md` — Tier 0-4 分级定价

## 阻塞问题
- 事件类型枚举需要冻结
- 一致性守卫的冲突判定阈值需要确定
- 多引擎并行调用的时序控制

## 设计笔记
- 编排器是唯一有记忆写入权限的模块
- 引擎之间不直接通信，只通过编排器协调
- 所有引擎返回后，经一致性守卫校验，统一写入记忆
- Phase 1 仅路由到角色引擎、世界引擎、级联修正器（简化版）
