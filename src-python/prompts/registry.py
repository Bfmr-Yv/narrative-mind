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
# Stub 格式化函数（Phase F 补齐）
# =========================================================================

def _stub_formatter(**kwargs) -> str:
    """占位格式化函数，Phase F 补齐"""
    return f"[STUB] prompt not yet implemented. args: {list(kwargs.keys())}"


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

    # Phase 1 — 占位
    "action_infer": {
        "task_type": "action_infer",
        "system": "[STUB] action_infer — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 800,
        "estimated_tokens_out": 300,
    },
    "rule_check": {
        "task_type": "rule_check",
        "system": "[STUB] rule_check — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 400,
        "estimated_tokens_out": 150,
    },
    "spatial_check": {
        "task_type": "spatial_check",
        "system": "[STUB] spatial_check — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 300,
        "estimated_tokens_out": 100,
    },
    "rerank": {
        "task_type": "rerank",
        "system": "[STUB] rerank — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1500,
        "estimated_tokens_out": 200,
    },
    "scene_analysis": {
        "task_type": "scene_analysis",
        "system": "[STUB] scene_analysis — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1500,
        "estimated_tokens_out": 500,
    },

    # Phase 2 — 叙事引擎（占位）
    "foreshadow_detect": {
        "task_type": "foreshadow_detect",
        "system": "[STUB] foreshadow_detect — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },
    "causal_extract": {
        "task_type": "causal_extract",
        "system": "[STUB] causal_extract — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },
    "resolution_check": {
        "task_type": "resolution_check",
        "system": "[STUB] resolution_check — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 200,
    },
    "event_predict": {
        "task_type": "event_predict",
        "system": "[STUB] event_predict — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 500,
    },

    # Phase 2 — 文辞引擎（占位）
    "style_check": {
        "task_type": "style_check",
        "system": "[STUB] style_check — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 300,
    },
    "register_check": {
        "task_type": "register_check",
        "system": "[STUB] register_check — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 300,
    },

    # Phase 3 — 主题引擎（占位）
    "theme_extract": {
        "task_type": "theme_extract",
        "system": "[STUB] theme_extract — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },

    # Phase 3 — 经济引擎（占位）
    "economy_check": {
        "task_type": "economy_check",
        "system": "[STUB] economy_check — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1000,
        "estimated_tokens_out": 300,
    },

    # Phase 3 — 读者预期引擎（占位）
    "expectation_analyze": {
        "task_type": "expectation_analyze",
        "system": "[STUB] expectation_analyze — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },

    # Phase 3 — 构思引擎（占位）
    "imagery_detect": {
        "task_type": "imagery_detect",
        "system": "[STUB] imagery_detect — Phase F 补齐",
        "formatter": _stub_formatter,
        "estimated_tokens_in": 1200,
        "estimated_tokens_out": 400,
    },
}
