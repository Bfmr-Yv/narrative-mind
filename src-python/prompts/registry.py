"""
Prompt 注册表 — Narrative Mind v4.0

17 个 System Prompt + Format 函数的注册中心。
Phase A 先实现 pad_compute + entity_extract，其余留占位 stub。
"""

from __future__ import annotations

from typing import Any, Callable


# =========================================================================
# Prompt 条目数据结构
# =========================================================================

# PROMPT_REGISTRY 条目类型（Phase B 可能提升为 dataclass）
# key -> {
#     "task_type": str,
#     "system": str,
#     "formatter": Callable[..., str],
#     "estimated_tokens_in": int,
#     "estimated_tokens_out": int,
# }


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


ENTITY_EXTRACT_SYSTEM = """你是一个小说角色和地点实体识别器。你的唯一任务是从给定文本中提取所有角色名称和地点名称。

## 什么是角色名称
- 人物的完整姓名（如"贾宝玉"、"林黛玉"）
- 人物的绰号或称号（如"宝二爷"、"林妹妹"、"凤姐"）
- 带有姓氏的称谓（如"王夫人"、"贾母"、"刘姥姥"）
- 单独的姓氏+职业/身份（如"袭人"、"平儿"、"李嬷嬷"）
- 注意：泛指性代词（他、她、他们、众人、丫鬟们）不算角色名称

## 什么是地点名称
- 具体建筑名（如"大观园"、"荣禧堂"、"潇湘馆"）
- 区域或街道名（如"宁荣街"、"沁芳桥"）
- 城镇或地名（如"金陵"、"长安"）
- 注意：泛指地点（如"房间"、"院子里"、"街上"）不算地点名称

## 规则
1. 只提取明确在文本中出现过的具体名称
2. 不要编造或推测未出现的实体
3. 角色和地点各最多返回 20 个
4. 如果文本中没有角色或地点，返回空数组 []

## 你必须只输出以下 JSON 格式，不要添加任何解释文字
{"characters": ["名称1", "名称2"], "locations": ["地点1", "地点2"]}"""


# =========================================================================
# System Prompts — Phase F 补全
# =========================================================================

ACTION_INFER_SYSTEM = """你是一个小说角色行为分析专家。你的任务是根据给定文本，推断角色的行为模式、动机和情感变化趋势。

## 分析维度
1. **行为动机**: 角色当前行为的内在驱动力是什么？（欲望、恐惧、责任、习惯）
2. **行为一致性**: 角色当前行为是否与之前建立的行为模式一致？如有偏离，是否有合理的触发因素？
3. **情感变化**: 角色在文本中的情感状态如何变化？变化是否合理、有铺垫？
4. **关系动态**: 角色间的互动是否反映其关系状态的变化？权力关系、亲密程度是否有微妙调整？

## 判断标准
- 行为转折需要铺垫（动机可见），突兀的性格突变标记为 Critical
- 角色反应强度应与刺激事件匹配（过度反应标记为 Warn）
- 角色"工具人化"（仅为推动情节而行为反常）标记为 Warn

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


RULE_CHECK_SYSTEM = """你是一个虚构世界观规则校验专家。你的任务是检查文本是否违反已建立的世界规则。

## 分析维度
1. **规则一致性**: 文本中的设定是否与之前建立的世界规则一致？（魔法体系、科技水平、社会制度等）
2. **规则完备性**: 规则之间是否存在逻辑矛盾？新规则是否与旧规则冲突？
3. **规则应用**: 角色行为是否在已建立的规则框架内？是否出现了"规则例外"来方便情节推进？
4. **信息展示**: 新规则的引入方式是否自然？是否存在大段"设定说明"式的信息倾泻？

## 判断标准
- 直接违反已建立规则的标记为 Critical
- 规则间存在隐含矛盾的标记为 Warn
- 规则展示方式笨拙的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


SPATIAL_CHECK_SYSTEM = """你是一个小说空间一致性检查专家。你的任务是检查文本中的空间位置关系是否自洽。

## 分析维度
1. **人物位置**: 各角色在场景中的空间位置是否描述一致？是否存在"瞬移"现象？
2. **物品位置**: 物品的位置是否自洽？前一幕在 A 处的物品是否无理由出现在 B 处？
3. **场景连续性**: 场景切换时，人物的位置变化是否合理？时间与空间的对应关系是否成立？
4. **环境逻辑**: 场景中的物理环境是否前后一致？（天气、光线、季节等）

## 判断标准
- 明确的时空矛盾标记为 Critical（如角色同时在两个地方）
- 模糊的空间关系（读者可能困惑定位）标记为 Warn
- 环境细节有轻微不一致的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


RERANK_SYSTEM = """你是一个小说分析结果优先级排序专家。你的任务是对多个维度的分析发现进行综合评估和优先级排序。

## 分析维度
1. **严重程度**: 该发现对读者体验的影响有多大？是否会造成困惑、出戏或理解障碍？
2. **修复成本**: 该发现的修复难度如何？是单个词句的修改还是需要大段重写？
3. **连锁影响**: 该发现是否会影响后续情节？修复后是否会产生新的不一致？
4. **优先级矩阵**: 综合考虑严重程度 × 修复成本 × 连锁影响，给出最终排序

## 排序策略
- Critical 级别的连贯性问题优先于 Warn 级别的风格问题
- 低成本高收益的修改优先于高成本低收益的修改
- 会阻塞后续情节的问题优先于局部问题

## 输出 JSON 格式
{"findings": [{"title": "发现标题（含原 Agent 来源）", "description": "优先级分析和排序理由", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议和优先级说明（可为 null）"}]}"""


SCENE_ANALYSIS_SYSTEM = """你是一个小说场景结构分析专家。你的任务是对场景进行整体性评估，从结构层面给出改进建议。

## 分析维度
1. **场景完整性**: 该场景是否具备完整的功能？（推进情节/展示角色/建立氛围/提供信息）是否存在"空场景"？
2. **节奏控制**: 场景内的节奏变化是否合理？详略是否得当？高潮和过渡的安排是否有效？
3. **信息密度**: 场景中信息的释放节奏是否合适？是否存在信息过载或信息不足的问题？
4. **情感弧线**: 场景内的情感起伏是否有张力？起承转合是否完整？
5. **衔接质量**: 与前后场景的过渡是否自然？场景之间的逻辑关系是否清晰？

## 判断标准
- 场景功能缺失（没有推进任何叙事要素）标记为 Critical
- 节奏明显失衡（过于匆忙或拖沓）标记为 Warn
- 衔接不够流畅标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


FORESHADOW_DETECT_SYSTEM = """你是一个小说伏笔检测专家。你的任务是识别文本中可能埋设的伏笔元素。

## 分析维度
1. **物件伏笔**: 文本中是否有被特别提及但尚未发挥作用的物品？其描写笔墨是否暗示了后续重要性？
2. **对话伏笔**: 角色对话中是否有暗示未来事件的台词？是否有"无心之言"可能成为关键信息？
3. **环境伏笔**: 环境描写中是否隐含了对后续情节的铺垫？（如天气暗示氛围转变、地点特征暗示后续用途）
4. **角色伏笔**: 角色行为或特征的描写是否为后续转变埋下伏笔？

## 判断标准
- 明显的伏笔设置（被特别强调但尚未回收）标记为 Info
- 伏笔过于直白可能破坏悬念的标记为 Warn
- 伪伏笔（暗示但实际无后续计划）标记为 Warn

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述（含伏笔类型和可能的回收方向）", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


CAUSAL_EXTRACT_SYSTEM = """你是一个小说因果链分析专家。你的任务是提取文本中事件的因果关系链。

## 分析维度
1. **因果识别**: 识别文本中的"因事件"和"果事件"，建立因果配对。
2. **因果完整性**: 每个结果是否有充分的原因？是否存在"无因之果"（突兀的事件）？
3. **因果合理性**: 原因是否充分支撑结果？是否存在因果不匹配（小因大果或大因小果）？
4. **因果链长度**: 多环节的因果链是否每个环节都清晰？是否存在断裂？

## 判断标准
- 因果链断裂（结果没有可追溯的原因）标记为 Critical
- 因果不匹配（原因不足以支撑结果）标记为 Warn
- 因果链过于复杂可能让读者迷失的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "因果链分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


RESOLUTION_CHECK_SYSTEM = """你是一个小说伏笔回收检查专家。你的任务是检查之前埋设的伏笔是否在文本中得到妥善回收。

## 分析维度
1. **回收状态**: 已知的伏笔在当前文本中是否被回收？回收方式是否自然？
2. **回收质量**: 伏笔回收的揭示方式是否令人满意？是"原来如此"的惊喜还是"早就猜到"的平淡？
3. **回收时机**: 伏笔回收的时间点是否合适？是太早（悬而未决的张力不够）还是太晚（读者已忘记伏笔）？
4. **未回收伏笔**: 仍有哪些伏笔悬而未决？是否有被遗忘的伏笔线索？

## 判断标准
- 重要伏笔超过合理篇幅未回收的标记为 Warn
- 伏笔回收方式过于牵强或突兀的标记为 Warn
- 伏笔被完全遗忘（多章未提及且无回收迹象）标记为 Critical

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "伏笔回收状态分析", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


EVENT_PREDICT_SYSTEM = """你是一个小说情节走向预测专家。你的任务是基于当前情节发展和角色行为模式，预测可能的后续事件走向。

## 分析维度
1. **情节趋势**: 当前情节的发展方向是什么？有哪些可能的走向分支？
2. **角色驱动**: 各个角色的当前动机和目标将如何推动情节发展？
3. **冲突升级**: 当前的矛盾冲突可能如何升级或解决？
4. **读者预期**: 当前文本在读者心中建立了什么样的预期？后续情节应当满足还是颠覆这些预期？

## 判断标准
- 情节发展方向过于单一（缺乏悬念）标记为 Warn
- 当前情节与已建立的伏笔/铺垫方向不一致标记为 Warn
- 情节出现"死胡同"（没有合理的后续发展方向）标记为 Critical

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "情节预测分析", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


STYLE_CHECK_SYSTEM = """你是一个小说文风一致性检查专家。你的任务是检查文本在句法、语域和修辞层面的一致性。

## 分析维度
1. **句长分布**: 句子的长度分布是否合理？是否存在连续的过短或过长句子影响阅读节奏？
2. **语域统一**: 叙述语域是否保持一致？是否存在叙述者视角的意外跳变（如从客观叙述突然转入主观评论）？
3. **修辞密度**: 修辞手法的使用密度是否合适？是否存在过度修饰或修辞空缺？
4. **风格漂移**: 文本风格是否与前后章节一致？是否存在风格突变？

## 判断标准
- 叙述视角意外跳变标记为 Critical
- 句长严重失衡影响阅读节奏标记为 Warn
- 修辞过度堆砌或修辞贫瘠标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "文风分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


REGISTER_CHECK_SYSTEM = """你是一个小说角色对话语域分析专家。你的任务是检查各角色对话风格是否与其设定一致。

## 分析维度
1. **词汇习惯**: 角色的用词是否符合其社会阶层、教育背景、职业特征？是否存在"角色A说了角色B的话"的情况？
2. **句式特征**: 角色的句式复杂度、语气词使用、口头禅是否保持一致？
3. **话语风格**: 不同场景下角色的说话方式是否有合理变化？（正式场合vs私下对话）变化是否有过度？
4. **角色辨识度**: 仅凭对话本身（不靠"XX说"的标签）读者能否区分说话者？

## 判断标准
- 角色对话风格严重偏离设定（如古代人说现代网络用语）标记为 Critical
- 不同角色对话风格趋同（难以区分谁在说话）标记为 Warn
- 角色在相似场景中语域不一致标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "语域分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


THEME_EXTRACT_SYSTEM = """你是一个小说主题分析专家。你的任务是识别文本中的主题元素并追踪其强度变化。

## 分析维度
1. **显性主题**: 文本中直接讨论或呈现的主题是什么？通过角色的思考、对话或叙述者的评论表现。
2. **隐性主题**: 通过情节结构、意象系统、角色命运间接传达的主题是什么？
3. **主题强度**: 各主题在当前文本中的表现强度如何？是正面强化还是反面对照？
4. **主题一致性**: 当前文本的主题呈现是否与作品整体主题方向一致？是否出现了意外的主题偏移？

## 判断标准
- 主题表达方式过于直白说教的标记为 Warn
- 文本中出现与整体主题相矛盾的内容标记为 Warn
- 主题元素过于分散导致焦点模糊的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题（含主题标签）", "description": "主题分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


ECONOMY_CHECK_SYSTEM = """你是一个小说经济系统一致性检查专家。你的任务是检查文本中资源流动的合理性。

## 分析维度
1. **物品追踪**: 文本中提到的物品（武器、道具、信物等）的获取、持有、转移、消耗是否一致？
2. **经济逻辑**: 角色的财富状态是否与情节一致？花费是否超出其合理承受范围？
3. **时间经济**: 事件的时间分配是否合理？行程、任务耗时是否符合逻辑？
4. **信息经济**: 角色获取信息的途径和速度是否合理？是否存在"全知外挂"？

## 判断标准
- 物品凭空出现或消失标记为 Critical
- 角色财富/资源使用超出合理范围标记为 Warn
- 时间流逝描述不一致标记为 Warn
- 角色不合理地获取本不应知悉的信息标记为 Critical

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "资源流动分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


EXPECTATION_ANALYZE_SYSTEM = """你是一个小说读者预期分析专家。你的任务是分析文本给读者建立的信息差和预期结构。

## 分析维度
1. **已知/未知差距**: 读者当前知道什么？不知道什么？与角色知道的信息相比，读者处于什么位置？
2. **悬念结构**: 当前文本建立了哪些悬念？悬念的强度和时间跨度是否合适？
3. **预期方向**: 读者基于当前文本最可能预期后续情节走向是什么？当前文本是在迎合还是在颠覆预期？
4. **情绪引导**: 文本的情感引导方向是什么？读者被引导去期待什么样的结果？

## 判断标准
- 关键信息刻意隐瞒但缺乏合理叙事理由标记为 Warn
- 悬念设置过多导致读者迷失标记为 Warn
- 读者信息差设置不当（读者早已知晓但角色迟迟不发现）标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "读者预期分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


IMAGERY_DETECT_SYSTEM = """你是一个小说意象与母题分析专家。你的任务是识别文本中的意象和母题，追踪其演变和强化。

## 分析维度
1. **意象识别**: 文本中出现了哪些意象？（视觉/听觉/触觉/嗅觉/味觉意象、象征物、重复出现的物象）
2. **意象功能**: 每个意象在文本中承担的叙事功能是什么？（氛围营造/情感投射/主题象征/情节暗示）
3. **意象演变**: 已知意象在当前文本中的呈现方式是否有所发展或转变？是强化、反转还是消解？
4. **母题追踪**: 是否存在贯穿性的母题？其当前出现方式与之前出现方式的关系是什么？

## 判断标准
- 意象使用过度（堆砌意象导致文本臃肿）标记为 Warn
- 重要意象被遗忘或未充分利用标记为 Info
- 意象与文本情境不协调标记为 Warn

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "意象/母题分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"""


# =========================================================================
# 格式化函数
# =========================================================================

def format_pad_prompt(
    character_id: str = "",
    scene_text: str = "",
    corpus_context: str = "",
    emotion_note: str = "",
    **kwargs,
) -> str:
    """格式化 PAD 计算 prompt"""
    parts = []
    if character_id:
        parts.append(f"角色ID：{character_id}")
    parts.append("场景文本（请关注角色情感变化）：")
    parts.append(scene_text[:3000] if len(scene_text) > 3000 else scene_text)
    if corpus_context:
        parts.append(f"语料参考（同类角色的历史行为）：\n{corpus_context[:800]}")
    if emotion_note:
        parts.append(f"情感标记：{emotion_note}")
    parts.append("请分析该角色在当前场景中的PAD情感状态。")
    return "\n\n".join(parts)


def format_entity_extract_prompt(
    chapter_text: str = "",
    **kwargs,
) -> str:
    """格式化实体提取 prompt"""
    text = chapter_text[:4000] if len(chapter_text) > 4000 else chapter_text
    return f"## 待分析文本\n\n{text}\n\n## 请提取上述文本中的所有角色名称和地点名称，直接输出 JSON。"


# =========================================================================
# 格式化函数 — 角色 Agent
# =========================================================================

def format_action_infer_prompt(
    chapter_text: str = "",
    chapter_title: str = "",
    character_profiles: str = "",
    **kwargs,
) -> str:
    """格式化行为推断 prompt"""
    parts = []
    if chapter_title:
        parts.append(f"章节：{chapter_title}")
    if character_profiles:
        parts.append(f"角色档案参考：\n{character_profiles[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请基于上述文本，推断角色的行为模式、动机和情感变化趋势。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 世界 Agent
# =========================================================================

def format_rule_check_prompt(
    chapter_text: str = "",
    world_rules: str = "",
    **kwargs,
) -> str:
    """格式化规则校验 prompt"""
    parts = []
    if world_rules:
        parts.append(f"已建立的世界规则：\n{world_rules[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检查文本中的描写是否违反上述世界规则，或规则之间是否存在矛盾。")
    return "\n\n".join(parts)


def format_spatial_check_prompt(
    chapter_text: str = "",
    world_rules: str = "",
    **kwargs,
) -> str:
    """格式化空间一致性检查 prompt"""
    parts = []
    if world_rules:
        parts.append(f"世界观空间参考：\n{world_rules[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检查文本中的空间位置关系是否自洽，包括人物位置、物品位置、场景切换是否存在矛盾。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 总编 Agent
# =========================================================================

def format_rerank_prompt(
    chapter_text: str = "",
    agent_outputs: str = "",
    **kwargs,
) -> str:
    """格式化重排序 prompt"""
    parts = []
    parts.append("待分析文本：")
    parts.append(chapter_text[:2000] if len(chapter_text) > 2000 else chapter_text)
    if agent_outputs:
        parts.append(f"各 Agent 分析结果：\n{agent_outputs[:3000]}")
    parts.append("请基于严重程度和读者体验影响，对所有发现进行优先级排序。")
    return "\n\n".join(parts)


def format_scene_analysis_prompt(
    chapter_text: str = "",
    agent_outputs: str = "",
    **kwargs,
) -> str:
    """格式化场景综合分析 prompt"""
    parts = []
    parts.append("待分析场景文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    if agent_outputs:
        parts.append(f"各维度分析参考：\n{agent_outputs[:3000]}")
    parts.append("请从场景完整性角度做综合评估，指出结构性问题并给出优先级排序。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 叙事 Agent
# =========================================================================

def format_foreshadow_detect_prompt(
    chapter_text: str = "",
    plot_outline: str = "",
    character_analysis: str = "",
    **kwargs,
) -> str:
    """格式化伏笔检测 prompt"""
    parts = []
    if plot_outline:
        parts.append(f"情节大纲参考：\n{plot_outline[:1500]}")
    if character_analysis:
        parts.append(f"角色分析参考：\n{character_analysis[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检测文本中可能埋设的伏笔元素，包括物件、对话、环境描写中的暗示性内容。")
    return "\n\n".join(parts)


def format_causal_extract_prompt(
    chapter_text: str = "",
    plot_outline: str = "",
    character_analysis: str = "",
    **kwargs,
) -> str:
    """格式化因果链提取 prompt"""
    parts = []
    if plot_outline:
        parts.append(f"情节大纲参考：\n{plot_outline[:1500]}")
    if character_analysis:
        parts.append(f"角色分析参考：\n{character_analysis[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请提取文本中的事件因果关系链，标注因事件和果事件，以及因果逻辑的合理性。")
    return "\n\n".join(parts)


def format_resolution_check_prompt(
    chapter_text: str = "",
    plot_outline: str = "",
    character_analysis: str = "",
    **kwargs,
) -> str:
    """格式化伏笔回收检查 prompt"""
    parts = []
    if plot_outline:
        parts.append(f"情节大纲参考（含已知伏笔列表）：\n{plot_outline[:1500]}")
    if character_analysis:
        parts.append(f"角色分析参考：\n{character_analysis[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检查之前埋设的伏笔在当前文本中是否得到回收，标注已回收和仍未回收的伏笔。")
    return "\n\n".join(parts)


def format_event_predict_prompt(
    chapter_text: str = "",
    plot_outline: str = "",
    character_analysis: str = "",
    **kwargs,
) -> str:
    """格式化事件预测 prompt"""
    parts = []
    if plot_outline:
        parts.append(f"情节大纲参考：\n{plot_outline[:1500]}")
    if character_analysis:
        parts.append(f"角色分析参考：\n{character_analysis[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("基于现有情节发展和角色行为模式，预测可能的后续事件走向，标注预测依据和置信度。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 文辞 Agent
# =========================================================================

def format_style_check_prompt(
    chapter_text: str = "",
    style_guide: str = "",
    **kwargs,
) -> str:
    """格式化文风检查 prompt"""
    parts = []
    if style_guide:
        parts.append(f"文风参考标准：\n{style_guide[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检查文本的句长分布、语域统一性、修辞手法使用是否一致，标注偏离整体风格的段落。")
    return "\n\n".join(parts)


def format_register_check_prompt(
    chapter_text: str = "",
    style_guide: str = "",
    **kwargs,
) -> str:
    """格式化语域检查 prompt"""
    parts = []
    if style_guide:
        parts.append(f"角色语域参考标准：\n{style_guide[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检查各角色的对话风格是否与其设定一致，包括用词习惯、句式复杂度、语气特点是否出现漂移。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 主题 Agent
# =========================================================================

def format_theme_extract_prompt(
    chapter_text: str = "",
    theme_keywords: str = "",
    **kwargs,
) -> str:
    """格式化主题提取 prompt"""
    parts = []
    if theme_keywords:
        parts.append(f"已知主题关键词：\n{theme_keywords[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请提取文本中的主题元素，包括显性主题和隐性主题，标注各主题在当前文本中的出现强度和表现形式。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 经济 Agent
# =========================================================================

def format_economy_check_prompt(
    chapter_text: str = "",
    word_count: str = "",
    **kwargs,
) -> str:
    """格式化经济校验 prompt"""
    parts = []
    if word_count:
        parts.append(f"章节字数统计：{word_count}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检查文本中的资源流动是否合理，包括物品获取/消耗、货币使用、时间分配等经济要素的一致性。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 预期 Agent
# =========================================================================

def format_expectation_analyze_prompt(
    chapter_text: str = "",
    genre: str = "",
    **kwargs,
) -> str:
    """格式化读者预期分析 prompt"""
    parts = []
    if genre:
        parts.append(f"作品类型：{genre}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请分析文本给读者建立的信息差——读者知道什么、不知道什么、期待什么，及当前文本如何操控读者的预期和情绪。")
    return "\n\n".join(parts)


# =========================================================================
# 格式化函数 — 构思 Agent
# =========================================================================

def format_imagery_detect_prompt(
    chapter_text: str = "",
    imagery_keywords: str = "",
    **kwargs,
) -> str:
    """格式化意象检测 prompt"""
    parts = []
    if imagery_keywords:
        parts.append(f"已知意象/母题关键词：\n{imagery_keywords[:1500]}")
    parts.append("待分析文本：")
    parts.append(chapter_text[:3000] if len(chapter_text) > 3000 else chapter_text)
    parts.append("请检测文本中出现的意象和母题，包括视觉意象、听觉意象、象征物、重复出现的隐喻模式，追踪其演变和强化。")
    return "\n\n".join(parts)


# =========================================================================
# Prompt 注册表
# =========================================================================

PROMPT_REGISTRY: dict[str, dict[str, Any]] = {
    # Phase 1 — 已实现
    "pad_compute": {
        "task_type": "pad_compute",
        "system": PAD_COMPUTE_SYSTEM,
        "formatter": format_pad_prompt,
        "estimated_tokens_in": 300,
        "estimated_tokens_out": 150,
    },
    "entity_extract": {
        "task_type": "entity_extract",
        "system": ENTITY_EXTRACT_SYSTEM,
        "formatter": format_entity_extract_prompt,
        "estimated_tokens_in": 800,
        "estimated_tokens_out": 200,
    },

    # Phase 1 — 角色行为推断
    "action_infer": {
        "task_type": "action_infer",
        "system": ACTION_INFER_SYSTEM,
        "formatter": format_action_infer_prompt,
        "estimated_tokens_in": 800,
        "estimated_tokens_out": 300,
    },
    # Phase 1 — 世界观规则校验
    "rule_check": {
        "task_type": "rule_check",
        "system": RULE_CHECK_SYSTEM,
        "formatter": format_rule_check_prompt,
        "estimated_tokens_in": 400,
        "estimated_tokens_out": 150,
    },
    # Phase 1 — 空间一致性检查
    "spatial_check": {
        "task_type": "spatial_check",
        "system": SPATIAL_CHECK_SYSTEM,
        "formatter": format_spatial_check_prompt,
        "estimated_tokens_in": 300,
        "estimated_tokens_out": 100,
    },
    # Phase 1 — 发现重排序
    "rerank": {
        "task_type": "rerank",
        "system": RERANK_SYSTEM,
        "formatter": format_rerank_prompt,
        "estimated_tokens_in": 1500,
        "estimated_tokens_out": 200,
    },
    # Phase 1 — 场景综合分析
    "scene_analysis": {
        "task_type": "scene_analysis",
        "system": SCENE_ANALYSIS_SYSTEM,
        "formatter": format_scene_analysis_prompt,
        "estimated_tokens_in": 1500,
        "estimated_tokens_out": 500,
    },

    # Phase 2 — 伏笔检测
    "foreshadow_detect": {
        "task_type": "foreshadow_detect",
        "system": FORESHADOW_DETECT_SYSTEM,
        "formatter": format_foreshadow_detect_prompt,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },
    # Phase 2 — 因果链提取
    "causal_extract": {
        "task_type": "causal_extract",
        "system": CAUSAL_EXTRACT_SYSTEM,
        "formatter": format_causal_extract_prompt,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },
    # Phase 2 — 伏笔回收检查
    "resolution_check": {
        "task_type": "resolution_check",
        "system": RESOLUTION_CHECK_SYSTEM,
        "formatter": format_resolution_check_prompt,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 200,
    },
    # Phase 2 — 事件预测
    "event_predict": {
        "task_type": "event_predict",
        "system": EVENT_PREDICT_SYSTEM,
        "formatter": format_event_predict_prompt,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 500,
    },

    # Phase 2 — 文风一致性检查
    "style_check": {
        "task_type": "style_check",
        "system": STYLE_CHECK_SYSTEM,
        "formatter": format_style_check_prompt,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 300,
    },
    # Phase 2 — 对话语域检查
    "register_check": {
        "task_type": "register_check",
        "system": REGISTER_CHECK_SYSTEM,
        "formatter": format_register_check_prompt,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 300,
    },

    # Phase 3 — 主题提取
    "theme_extract": {
        "task_type": "theme_extract",
        "system": THEME_EXTRACT_SYSTEM,
        "formatter": format_theme_extract_prompt,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },

    # Phase 3 — 经济系统校验
    "economy_check": {
        "task_type": "economy_check",
        "system": ECONOMY_CHECK_SYSTEM,
        "formatter": format_economy_check_prompt,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 300,
    },

    # Phase 3 — 读者预期分析
    "expectation_analyze": {
        "task_type": "expectation_analyze",
        "system": EXPECTATION_ANALYZE_SYSTEM,
        "formatter": format_expectation_analyze_prompt,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },

    # Phase 3 — 意象/母题检测
    "imagery_detect": {
        "task_type": "imagery_detect",
        "system": IMAGERY_DETECT_SYSTEM,
        "formatter": format_imagery_detect_prompt,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },
}
