---
name: ngp-character-engine
description: 角色引擎任务
version: 1.0.0
---

# NGP 角色引擎 Skill

> **Phase**: 1  
> **状态**: 活跃  
> **依赖**: 语料锚定层、工作记忆、世界引擎

## Phase 1 限制

- **Profile 类型**: 仅通用 Profile（不支持奇幻等类型专用 Profile）
- **守卫维度**: 仅 3 维（角色行为 / 世界规则 / 空间一致）
- **语料规模**: 20 片（红楼 10 + 自有 10）
- **记忆层级**: 仅工作记忆 + 简化情节记忆（无永久记忆）

## 职责

模拟角色在特定情境下的行为反应，基于语料行为模式而非标签推理。不存储"性格标签"（如"冷酷"），只存储"行为模式向量"。

## 输入格式

```python
@dataclass
class CharacterQuery:
    character_id: str          # 角色唯一标识
    scene_text: str            # 当前场景文本
    emotion_context: EmotionContext | None  # 情感上下文（可选）
```

## 输出格式

```python
@dataclass
class CharacterResponse:
    pad_state: PADState        # Pleasure-Arousal-Dominance 三维情感坐标
    behavior_prediction: BehaviorPrediction  # 预测行为 + 置信度
    implicit_triggers: list[str]  # 被触发的隐性记忆标签
    confidence: float          # 整体置信度 0-1
    needs_human_review: bool   # 置信度 < 0.5 时为 True
```

## PAD 情感状态定义

```python
@dataclass
class PADState:
    pleasure: float      # 愉悦度 [-1, 1]
    arousal: float       # 唤醒度 [-1, 1]
    dominance: float     # 支配度 [-1, 1]
    
    def distance_to(self, other: 'PADState') -> float:
        """计算两个情感状态的距离"""
        return ((self.pleasure - other.pleasure) ** 2 +
                (self.arousal - other.arousal) ** 2 +
                (self.dominance - other.dominance) ** 2) ** 0.5
```

## 行为模式匹配（伪代码）

```python
def predict_behavior(character, scene):
    # 1. 从语料库检索相似情境下的行为模式
    corpus_hits = vector_db.search(
        text=scene.text,
        category="behavior",
        character_id=character.id,
        top_k=3
    )
    
    # 2. 获取当前情感状态
    pad_current = memory.get_pad(character.id)
    
    # 3. 融合语料模式和当前情感
    behavior = fuse_patterns(corpus_hits, pad_current)
    
    # 4. 校验世界规则
    world_check = world_engine.validate(behavior)
    
    return BehaviorPrediction(
        action=behavior.action,
        confidence=behavior.confidence,
        triggers=behavior.implicit_triggers
    )
```

## 依赖模块

- 工作记忆（当前 PAD 情感坐标查询与更新）
- 语料锚定层（行为模式向量检索，top-k=3）
- 世界引擎（设定规则校验行为合法性）
- 一致性守卫（Phase 1 仅角色/世界/空间三维校验）

## 契约

- 不直接修改记忆，只返回建议
- 记忆更新由编排器统一写入
- 置信度 < 0.5 时必须返回 `needs_human_review=True`
- 角色不存储"性格标签"，只存储"行为模式向量"
- 行为模式从语料中提取，不人工编写

## 阻塞问题

- 行为模式怎么从语料切片中自动提取？需要确定提取规则
- PAD 状态的初始值怎么设定？是固定默认值还是从语料统计？

## 设计笔记

- 情感状态随章节推进动态变化，不固定
- 语料切片标准：500 字场景级（ADR-013）
- Phase 1 仅使用通用 Profile，不支持类型专用 Profile
