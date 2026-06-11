# 世界引擎卡片 `[Phase 1 活跃]`

> **v3.1 更新**：Phase 1 唯二活跃引擎之一。只做校验，不做裁决。

## 职责
校验事件是否符合世界观设定（力量体系、空间规则、社会结构等）。规则冲突时返回 `conflict` 状态 + 冲突详情，由人类作者决定。

## 当前状态
- [ ] 修仙力量体系 Schema
- [ ] 空间规则定义
- [ ] 社会结构规则
- [x] 接口契约已冻结
- [ ] Prompt v1 编写
- [ ] GenreProfile 统计规则（ADR-014，Phase 2+ 实现）

## 输入/输出

**输入**：`WorldQuery { event_description, location, involved_characters }`

**输出**：`WorldResponse { rule_checks, spatial_consistency, power_level_validation }`

详见 `02-CONTRACTS.md` — 世界引擎契约

## 依赖模块
- 无（只读设定库，不依赖其他引擎）

## 设定库结构（草案）

```
corpus/
├── world-settings/
│   ├── power-system.yaml      # 力量体系
│   ├── spatial-rules.yaml     # 空间规则
│   ├── social-structure.yaml  # 社会结构
│   └── genre-profile.yaml     # 类型特征（从语料统计生成）
```

## 力量体系规则示例（修仙）

```yaml
power_system:
  name: "修仙境界体系"
  levels:
    - name: "练气"
      range: [1, 9]
      capabilities: ["基础法术", "轻身术"]
    - name: "筑基"
      range: [10, 19]
      capabilities: ["飞行", "法宝使用"]
    - name: "金丹"
      range: [20, 29]
      capabilities: ["领域", "分身"]
  
  rules:
    - id: "R001"
      desc: "低境界无法感知高境界气息"
      condition: "observer_level < target_level - 3"
      effect: "感知失败"
    - id: "R002"
      desc: "跨境界战斗需要特殊条件"
      condition: "attacker_level < defender_level - 5"
      effect: "需要特殊道具或阵法辅助"
```

## 规则校验逻辑（伪代码）

```python
def validate_event(event, settings):
    results = []
    
    # 力量体系校验
    for char in event.involved_characters:
        char_level = memory.get_power_level(char)
        for rule in settings.power_system.rules:
            if rule.condition_matches(event, char_level):
                results.append(RuleCheck(
                    rule_id=rule.id,
                    status="pass" or "conflict",
                    detail=rule.desc
                ))
    
    # 空间一致性校验
    spatial_ok = check_spatial_consistency(event.location, settings)
    
    return WorldResponse(
        rule_checks=results,
        spatial_consistency=spatial_ok,
        power_level_validation=aggregate_power_checks(results)
    )
```

## 阻塞问题
- 修仙力量体系的境界划分需要确定（参考哪些作品？）
- 空间规则的粒度怎么定？（全局 vs 区域）
- GenreProfile 的统计规则待定

## 设计笔记
- 世界引擎只做校验，不做裁决
- 规则冲突时返回 `conflict` 状态，由人类作者决定
- 设定库由人类维护，引擎只读
