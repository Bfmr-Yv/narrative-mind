---
name: ngp-world-engine
description: 世界引擎任务
version: 1.0.0
---

# NGP 世界引擎 Skill

> **Phase**: 1  
> **状态**: 活跃  
> **依赖**: 无（只读设定库）

## Phase 1 限制

- **Profile 类型**: 仅通用 Profile（不支持奇幻等类型专用 Profile）
- **守卫维度**: 仅 3 维（角色行为 / 世界规则 / 空间一致）
- **语料规模**: 20 片（红楼 10 + 自有 10）
- **规则类型**: 仅基础规则校验（无因果推理）

## 职责

校验事件是否符合世界观设定（力量体系、空间规则、社会结构等）。规则冲突时返回 `conflict` 状态 + 冲突详情，由人类作者决定。

## 输入格式

```python
@dataclass
class WorldQuery:
    event_description: str     # 事件描述
    location: str              # 发生地点
    involved_characters: list[str]  # 涉及角色 ID 列表
```

## 输出格式

```python
@dataclass
class WorldResponse:
    rule_checks: list[RuleCheck]       # 规则校验结果
    spatial_consistency: bool           # 空间一致性
    power_level_validation: PowerLevel  # 力量等级校验
```

## 设定库结构

```
corpus/
├── world-settings/
│   ├── power-system.yaml      # 力量体系
│   ├── spatial-rules.yaml     # 空间规则
│   ├── social-structure.yaml  # 社会结构
│   └── genre-profile.yaml     # 类型特征（从语料统计生成）
```

## 力量体系规则示例（通用）

```yaml
power_system:
  name: "通用权限体系"
  levels:
    - name: "初级"
      range: [1, 9]
      capabilities: ["初级权限"]
    - name: "中级"
      range: [10, 19]
      capabilities: ["中级权限"]
    - name: "高级"
      range: [20, 29]
      capabilities: ["高级权限"]
  
  rules:
    - id: "R001"
      desc: "低等级无法获取高等级信息"
      condition: "observer_level < target_level - 3"
      effect: "信息获取受限"
    - id: "R002"
      desc: "跨等级操作需要授权"
      condition: "requester_level < target_level - 5"
      effect: "需要特殊授权或辅助条件"
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

## 依赖模块

- 无（只读设定库，不依赖其他引擎）

## 契约

- 设定库由人类作者维护，引擎只查询不修改
- 规则冲突时返回 `conflict` 状态 + 冲突详情，不做自动裁决
- 所有校验结果供一致性守卫使用
- 世界引擎只做校验，不做裁决

## 阻塞问题

- 类型专用力量体系的等级划分规则待定（Phase 2+）
- 空间规则的粒度怎么定？（全局 vs 区域）
- GenreProfile 的统计规则待定（ADR-014，Phase 2+ 实现）

## 设计笔记

- 设定库由人类维护，引擎只读
- 规则冲突时返回 `conflict` 状态，由人类作者决定
- Phase 1 仅使用通用 Profile，不支持类型专用 Profile
- GenreProfile 统计规则待定（Phase 2+ 实现）
