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


# ---------------------------------------------------------------------------
# Entity extraction prompt (Item 2: Character/Location Auto-extraction)
# ---------------------------------------------------------------------------

ENTITY_EXTRACT_SYSTEM = """你是一个小说角色和地点实体识别器。你的唯一任务是从给定文本中提取所有角色名称和地点名称。

## 什么是角色名称
- 人物的完整姓名（如"贾宝玉"、"林黛玉"）
- 人物的绰号或称号（如"宝二爷"、"林妹妹"、"凤姐"、"颦儿"）
- 带有姓氏的称谓（如"王夫人"、"贾母"、"刘姥姥"）
- 单独的姓氏+职业/身份（如"袭人"、"平儿"、"李嬷嬷"）
- 注意：泛指性代词（他、她、他们、众人、丫鬟们）不算角色名称
- 注意：纯描述性短语（如"一个穿红衣的女子"）不算角色名称，除非在文中被用作称呼

## 什么是地点名称
- 具体建筑名（如"大观园"、"荣禧堂"、"潇湘馆"）
- 区域或街道名（如"宁荣街"、"沁芳桥"）
- 城镇或地名（如"金陵"、"长安"）
- 注意：泛指地点（如"房间"、"院子里"、"街上"）不算地点名称
- 注意：方向描述（如"东边"、"左转"）不算地点名称

## 示例
输入："宝玉到了潇湘馆，只见黛玉正坐在窗前看书。凤姐从荣禧堂过来，说贾母要找他们。"
输出：{"characters": ["宝玉", "黛玉", "凤姐", "贾母"], "locations": ["潇湘馆", "荣禧堂"]}

## 规则
1. 只提取明确在文本中出现过的具体名称
2. 不要编造或推测未出现的实体
3. 角色和地点各最多返回 20 个
4. 如果文本中没有角色或地点，返回空数组 []

## 你必须只输出以下 JSON 格式，不要添加任何解释文字
{"characters": ["名称1", "名称2"], "locations": ["地点1", "地点2"]}"""


# ---------------------------------------------------------------------------
# Unified scene analysis prompt (replaces entity extraction + character analysis)
# ---------------------------------------------------------------------------

SCENE_ANALYSIS_SYSTEM = """你是一个小说场景分析器。分析给定的小说文本片段，输出结构化的分析结果。

## 一、角色提取
- 识别文本中所有具名角色：人名、绰号、称谓
- 不包括代词、泛指、纯描述性短语
- 一个角色多个称呼时只提取最常用的一个

## 二、角色简介（character_intros）
为每个提取的角色写一句简介（30字内），描述：身份/地位 + 当前场景中的状态/情绪。
格式：{"角色名": "简介", ...}
示例：{"贾宝玉": "贾府公子，性格温柔多情，此刻正为黛玉的态度感到不安"}

## 三、地点提取
- 识别文本中所有具体地点：建筑名、区域名、地名
- 不包括泛称（"房间"、"街上"）

## 四、地点简介（location_intros）
为每个地点写一句简介（15字内），描述地点的特征或氛围。
格式：{"地点名": "简介", ...}
示例：{"潇湘馆": "清幽雅致的居所，遍植翠竹，是黛玉的住处"}

## 五、事件推演（约200字）
基于当前场景推断接下来可能发生什么：
- 当前场景的核心事件或冲突
- 各角色的可能反应和下一步行动
- 情节短期发展方向
- 只推演情节逻辑，不需要文学性描写

## 输出格式（严格JSON）
{"characters": [...], "character_intros": {...}, "locations": [...], "location_intros": {...}, "event_prediction": "..."}"""


def format_scene_analysis_prompt(chapter_text: str) -> str:
    """格式化统一场景分析 prompt

    Args:
        chapter_text: 章节文本（自动截取 4000 字）
    """
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    return (
        f"## 待分析文本\n\n{text}\n\n"
        "## 请分析以上文本，提取角色、地点，并推演事件发展。直接输出 JSON。"
    )


def format_entity_extract_prompt(chapter_text: str) -> str:
    """格式化实体提取 prompt

    Args:
        chapter_text: 章节文本（自动截取 4000 字）
    """
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    return f"## 待分析文本\n\n{text}\n\n## 请提取上述文本中的所有角色名称和地点名称，直接输出 JSON。"


# =========================================================================
# Phase 2 — 叙事引擎 Prompts
# =========================================================================

FORESHADOW_DETECT_SYSTEM = """你是一个小说伏笔分析专家。你的任务是从给定的章节文本中识别出所有可能构成伏笔的元素。

## 什么是伏笔
伏笔是作者在当前章节中埋下的暗示或铺垫，可能在后续章节中产生回响。包括但不限于：
1. **物品伏笔**：某个被特别提及、但未解释用途或来源的物品（如神秘玉佩、一封未读的信）
2. **对话伏笔**：角色之间含有暗示、预兆、或未说明信息的对话
3. **角色伏笔**：角色表现出的异常行为、隐藏的情绪、或未揭示的身份/关系
4. **事件伏笔**：某个看似偶然、但可能引发连锁反应的事件
5. **设定伏笔**：对某个地点、规则、或历史事件的提及，暗示其后续重要性

## 分析原则
1. 关注文本中被"特意提及但未充分解释"的细节
2. 关注角色对话中的暗示和保留信息
3. 关注叙述者语气中透露出"后面会再说"的信号
4. 宁可多报，不可漏报（允许假阳性，不允许假阴性）
5. 如果文本中没有明显伏笔，返回空数组

## 输出格式
严格输出以下JSON，不要任何额外文字：
{"foreshadowings": [{"description": "伏笔内容描述（30字内）", "hint_text": "原文暗示片段（≤80字）", "category": "object|dialogue|character|event|setting", "related_characters": ["角色名"], "confidence": 0.7}]}"""


def format_foreshadow_prompt(chapter_text: str, chapter_id: str = "") -> str:
    """格式化伏笔检测 prompt

    Args:
        chapter_text: 章节文本（自动截取 4000 字）
        chapter_id: 章节标识
    """
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    parts = [
        f"章节ID：{chapter_id}" if chapter_id else "",
        f"## 待分析文本\n\n{text}",
        "## 请识别上述文本中的所有伏笔。直接输出 JSON。",
    ]
    return "\n\n".join(p for p in parts if p)


CAUSAL_EXTRACT_SYSTEM = """你是一个小说情节因果关系分析专家。你的任务是从给定章节中提取事件之间的因果链。

## 什么是因果链
因果链连接两个事件，其中前一个事件是后一个事件的直接或间接原因。例如：
- "贾宝玉摔玉" → "林黛玉生气" （直接触发）
- "王熙凤设局" → "尤二姐吞金" （间接导致）

## 提取原则
1. 关注因果关系，而非时间顺序（"A然后B"不一定等于"A导致B"）
2. 因果链应该是有意义的叙事连接，而非琐碎的日常动作
3. 强度评估：1.0 = 必然导致，0.5 = 显著影响，0.2 = 微弱相关
4. 如果文本中没有明确的因果关系，返回空数组
5. 最多提取 5 条最核心的因果链

## 输出格式
严格输出以下JSON，不要任何额外文字：
{"causal_links": [{"cause": "原因事件描述（30字内）", "effect": "结果事件描述（30字内）", "strength": 0.7, "description": "因果说明（20字内）"}]}"""


def format_causal_prompt(chapter_text: str, chapter_id: str = "") -> str:
    """格式化因果提取 prompt

    Args:
        chapter_text: 章节文本（自动截取 4000 字）
        chapter_id: 章节标识
    """
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    parts = [
        f"章节ID：{chapter_id}" if chapter_id else "",
        f"## 待分析文本\n\n{text}",
        "## 请提取上述文本中的因果关系链。直接输出 JSON。",
    ]
    return "\n\n".join(p for p in parts if p)


RESOLUTION_CHECK_SYSTEM = """你是一个小说伏笔回收检测专家。你的任务是判断一个已知的伏笔是否在给定的新章节中得到了回收（呼应）。

## 判断标准
1. **已回收**：新章节中的某个情节、对话、或细节明确解释了伏笔的悬念
2. **部分回收**：伏笔被提及或推进了一步，但核心悬念尚未完全解开
3. **未回收**：新章节中没有与伏笔明显相关的内容

## 分析要点
- 伏笔的"回收"不一定是直白的揭晓，可以是暗示性的呼应
- 一个伏笔可能分多次回收（第一次给出线索，第二次完全揭晓）
- 注意伏笔的细节（物品的描述、对话的关键词）是否在新章中出现

## 输出格式
严格输出以下JSON，不要任何额外文字：
{"resolved": true, "confidence": 0.8, "detail": "回收说明（30字内）"}"""


def format_resolution_check_prompt(
    foreshadowing_desc: str,
    foreshadowing_hint: str,
    chapter_text: str,
) -> str:
    """格式化伏笔回收检查 prompt

    Args:
        foreshadowing_desc: 伏笔描述
        foreshadowing_hint: 伏笔原文片段
        chapter_text: 新章节文本（自动截取 4000 字）
    """
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    parts = [
        f"## 待检查的伏笔\n描述：{foreshadowing_desc}\n原文片段：{foreshadowing_hint}",
        f"## 新章节文本\n\n{text}",
        "## 该伏笔是否在本章中得到回收？直接输出 JSON。",
    ]
    return "\n\n".join(parts)


EVENT_PREDICT_SYSTEM = """你是一个小说情节推演专家。基于当前章节的事件和因果链，推演接下来可能发生的短期情节发展。

## 推演原则
1. 基于已有因果链进行逻辑推演，不要凭空创造新的设定
2. 推演要具体，包含"谁可能会做什么"以及"可能导致什么"
3. 考虑多条可能的发展线（2-3条），每条简短说明
4. 推演范围限于接下来1-3个场景，不需要长篇展望
5. 使用直接的陈述语气，不需要文学性描写

## 输出格式
严格输出以下JSON，不要任何额外文字：
{"prediction": "情节推演文本（150-250字）", "possible_branches": ["分支1简述", "分支2简述"], "confidence": 0.6}"""


def format_event_predict_prompt(
    chapter_text: str,
    causal_summary: str = "",
) -> str:
    """格式化情节推演 prompt

    Args:
        chapter_text: 章节文本（自动截取 4000 字）
        causal_summary: 因果链摘要
    """
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    parts = [
        f"## 当前章节\n\n{text}",
    ]
    if causal_summary:
        parts.append(f"## 已提取的因果链\n\n{causal_summary}")
    parts.append("## 请基于以上内容推演短期情节发展。直接输出 JSON。")
    return "\n\n".join(parts)
