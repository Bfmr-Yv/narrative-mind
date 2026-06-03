# 角色引擎卡片 `[Phase 1 活跃]`

> **v3.1 更新**：Phase 1 唯二活跃引擎之一。基于语料行为模式而非标签推理。

## 职责
模拟角色在特定情境下的行为反应，基于语料行为模式而非标签推理。不存储"性格标签"（如"冷酷"），只存储"行为模式向量"。

## 当前状态
- [ ] 心理模型 Schema 设计
- [x] PAD 情感状态定义
- [ ] 隐性记忆结构
- [ ] 行为模式提取算法（500 字场景级切片，ADR-013）
- [ ] Prompt v1 编写
- [ ] 与三层记忆系统对接（工作记忆读写 PAD）

## 输入/输出

**输入**：`CharacterQuery { character_id, scene_text, emotion_context }`

**输出**：`CharacterResponse { pad_state, behavior_prediction, implicit_triggers, confidence, needs_human_review }`

详见 `02-CONTRACTS.md` — 角色引擎契约

## 依赖模块
- 工作记忆（当前 PAD 情感坐标查询与更新）
- 语料锚定层（行为模式向量检索，top-k=3）
- 世界引擎（设定规则校验行为合法性）
- 一致性守卫（Phase 1 仅角色/世界/空间三维校验）

## 关键算法草稿

```python
# 行为模式匹配（伪代码）
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

## 阻塞问题
- 行为模式怎么从语料切片中自动提取？需要确定提取规则
- PAD 状态的初始值怎么设定？是固定默认值还是从语料统计？

## 设计笔记
- 角色不存储"性格标签"（如"冷酷"），只存储"行为模式向量"
- 行为模式从语料中提取，不人工编写
- 情感状态随章节推进动态变化，不固定
