"""
Prompt 模板 — Phase 1

为 5 个 LLM 任务提供中文 system prompt 和格式化函数。
所有 prompt 要求 JSON 输出，保证解析一致性。
"""

from __future__ import annotations


# =========================================================================
# System Prompts
# =========================================================================

PAD_COMPUTE_SYSTEM = """你是一个文学情感分析专家。你的任务是根据给定的场景文本和角色上下文，精确分析角色的PAD三维情感坐标。

PAD模型说明：
- Pleasure (愉悦度): [-1, 1]，正值愉悦/快乐，负值不快/痛苦
- Arousal (唤醒度): [-1, 1]，正值兴奋/紧张/激动，负值平静/困倦/低落
- Dominance (支配度): [-1, 1]，正值掌控/自信/主动，负值被支配/顺从/被动

分析要点：
1. 注意角色的社会地位对支配度的影响
2. 注意场景氛围对唤醒度的影响
3. 注意角色间互动对愉悦度的影响
4. 区分角色的外在表现和内在真实情感

输出严格的JSON格式，不要包含任何其他文本：
{"pleasure": float, "arousal": float, "dominance": float, "rationale": "简要分析理由，30字以内"}"""


ACTION_INFER_SYSTEM = """你是一个文学角色行为分析专家。你的任务是根据场景文本和语料参考，预测角色在当前情境下最可能的具体行为反应。

预测原则：
1. 行为必须符合角色的性格和社会地位
2. 参考语料中同类角色的行为模式
3. 考虑场景的情感氛围（PAD状态）
4. 行为描述要具体，不要泛化（例如："走上前轻声安慰黛玉"而非"说话"）
5. 给出2-3个备选行为，区分主次

输出严格的JSON格式，不要包含任何其他文本：
{"predicted_action": "最可能的具体行为描述（20字以内）", "alternative_actions": ["备选行为1", "备选行为2"], "confidence": float, "rationale": "推理依据，30字以内"}"""


RULE_CHECK_SYSTEM = """你是一个小说世界观规则校验专家。你的任务是判断给定的世界规则是否适用于描述的事件场景。

判断标准：
1. 规则描述的是哪类事件（感知、战斗、移动、社交等）？
2. 事件描述是否涉及规则所关注的领域？
3. 规则的条件（condition）在事件中是否满足？
4. 如果规则关注力量等级，事件中角色的力量等级是否符合触发条件？

输出严格的JSON格式，不要包含任何其他文本：
{"applies": bool, "detail": "规则是否适用的简要说明，30字以内"}"""


SPATIAL_CHECK_SYSTEM = """你是一个空间一致性校验专家。你的任务是判断事件描述是否违反了特定地点的空间规则约束。

校验原则：
1. 仔细阅读空间规则的约束条件
2. 分析事件描述中角色的行为和移动方式
3. 判断行为是否与约束冲突
4. 如果不确定，偏向"不冲突"（conservative）

输出严格的JSON格式，不要包含任何其他文本：
{"consistent": bool, "violation": "如果不一致，描述冲突原因，20字以内；如果一致，填null"}"""


RERANK_SYSTEM = """你是一个文学语料检索专家。你的任务是从候选语料切片中选出与查询场景最相关的切片。

排序标准（按重要性降序）：
1. 角色行为模式相似度：同类型角色在相似情境下的反应
2. 情感氛围相似度：场景的情感基调是否接近
3. 情节结构相似度：事件的发展逻辑是否类似
4. 文本表面相似度：关键词和描写的重叠程度

输出严格的JSON格式，不要包含任何其他文本：
{"ranked_ids": ["slice_id1", "slice_id2", "slice_id3"], "rationale": "排序理由，40字以内"}"""


# =========================================================================
# 格式化函数
# =========================================================================

def format_pad_prompt(
    character_id: str,
    scene_text: str,
    corpus_context: str = "",
    emotion_note: str = "",
) -> str:
    """格式化 PAD 计算 prompt

    Args:
        character_id: 角色 ID
        scene_text: 场景文本（自动截取 800 字）
        corpus_context: 语料参考上下文
        emotion_note: 情感标记（如 target_emotion）
    """
    parts = [
        f"角色ID：{character_id}",
        f"场景文本（请关注角色情感变化）：",
        scene_text[:3000] if len(scene_text) > 3000 else scene_text,
    ]
    if corpus_context:
        parts.append(f"语料参考（同类角色的历史行为）：")
        parts.append(corpus_context[:800])
    if emotion_note:
        parts.append(f"情感标记：{emotion_note}")

    parts.append("请分析该角色在当前场景中的PAD情感状态。")
    return "\n\n".join(parts)


def format_action_prompt(
    scene_text: str,
    hit_context: str,
    scene_type: str = "unknown",
    character_id: str = "",
) -> str:
    """格式化行为预测 prompt

    Args:
        scene_text: 当前场景文本（自动截取 500 字）
        hit_context: 语料命中切片的上下文
        scene_type: 场景类型
        character_id: 角色 ID
    """
    parts = []
    if character_id:
        parts.append(f"角色ID：{character_id}")
    parts.extend([
        f"场景类型：{scene_type}",
        f"当前场景文本（分析角色的处境和行为动机）：",
        scene_text[:4000] if len(scene_text) > 4000 else scene_text,
        f"语料参考切片（同类情境的行为模式）：",
        hit_context[:1000] if len(hit_context) > 1000 else hit_context,
        "请预测该角色在当前场景中最可能的具体行为。",
    ])
    return "\n\n".join(parts)


def format_rule_check_prompt(
    rule_description: str,
    rule_condition: str,
    event_description: str,
    char_level: str = "",
) -> str:
    """格式化规则校验 prompt

    Args:
        rule_description: 规则描述
        rule_condition: 规则条件表达式
        event_description: 事件描述（自动截取 400 字）
        char_level: 角色力量等级
    """
    parts = [
        f"世界规则：{rule_description}",
        f"规则条件：{rule_condition}",
        f"事件描述：",
        event_description[:1500] if len(event_description) > 1500 else event_description,
    ]
    if char_level:
        parts.append(f"角色力量等级：{char_level}")

    parts.append("该规则是否适用于此事件？")
    return "\n\n".join(parts)


def format_spatial_check_prompt(
    constraint: str,
    rule_description: str,
    event_description: str,
) -> str:
    """格式化空间校验 prompt

    Args:
        constraint: 空间规则约束（如 "只能步行进入"）
        rule_description: 规则描述
        event_description: 事件描述（自动截取 400 字）
    """
    parts = [
        f"地点规则：{rule_description}",
        f"约束条件：{constraint}",
        f"事件描述：",
        event_description[:1500] if len(event_description) > 1500 else event_description,
        "该事件是否违反了地点规则约束？",
    ]
    return "\n\n".join(parts)


def format_rerank_prompt(
    query_text: str,
    candidates: list[tuple[str, str]],  # [(slice_id, snippet_80chars), ...]
) -> str:
    """格式化重排序 prompt

    Args:
        query_text: 查询文本
        candidates: 候选切片列表 [(id, 80字摘要), ...]
    """
    parts = [
        f"查询场景：{query_text[:500]}",
        "候选语料切片：",
    ]
    for i, (sid, snippet) in enumerate(candidates):
        parts.append(f"[{i+1}] ID={sid} | {snippet}")

    parts.append("请从以上候选中选出最相关的3个切片，按相关性降序排列。")
    return "\n\n".join(parts)
