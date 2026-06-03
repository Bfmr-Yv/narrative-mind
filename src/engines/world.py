"""
世界引擎 (World Engine) — Phase 1

职责：校验事件是否符合世界观设定（力量体系、空间规则、社会结构等）。

契约（来源：02-CONTRACTS.md）：
- 设定库由人类作者维护，引擎只查询不修改
- 规则冲突时返回 conflict 状态 + 冲突详情，不做自动裁决

依赖：无（只读设定库）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class PowerLevel(Enum):
    """力量等级枚举（Phase 1 通用占位）

    具体等级定义由作者在设定库中维护。
    """

    UNRATED = "unrated"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    CONFLICT = "conflict"  # 规则冲突，需人类裁决


@dataclass
class RuleCheck:
    """单条规则校验结果"""

    rule_name: str
    passed: bool
    detail: str = ""
    conflict_description: Optional[str] = None


@dataclass
class WorldQuery:
    """世界引擎查询输入"""

    event_description: str
    location: str
    involved_characters: list[str] = field(default_factory=list)


@dataclass
class WorldResponse:
    """世界引擎查询输出"""

    rule_checks: list[RuleCheck] = field(default_factory=list)
    spatial_consistency: bool = True
    power_level_validation: PowerLevel = PowerLevel.UNRATED


# ---------------------------------------------------------------------------
# 引擎骨架
# ---------------------------------------------------------------------------

class WorldEngine:
    """世界引擎 — Phase 1 骨架

    校验事件是否符合世界观设定。
    只读设定库，不做自动裁决。
    """

    def __init__(self) -> None:
        """初始化世界引擎（Phase 1 无持久化资源）"""
        pass

    def validate(self, query: WorldQuery) -> WorldResponse:
        """校验事件是否符合世界观设定

        Args:
            query: 包含事件描述、地点、涉及角色的查询

        Returns:
            WorldResponse: 规则校验结果、空间一致性、力量等级
        """
        raise NotImplementedError("Phase 1 骨架 — 待实现")

    def load_settings(self, settings_path: str) -> None:
        """加载世界观设定库

        Args:
            settings_path: 设定库文件路径
        """
        raise NotImplementedError("Phase 1 骨架 — 待实现")
