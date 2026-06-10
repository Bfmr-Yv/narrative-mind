"""
编排器 (Orchestrator) — Phase 1

职责：接收用户操作，路由到相应引擎，协调引擎返回结果，统一写入记忆。
唯一有记忆写入权限的模块。

契约（来源：02-CONTRACTS.md）：
- 所有引擎返回后，由一致性守卫交叉验证
- 验证通过后统一写入记忆，不允许多个引擎直接写记忆
- 单引擎超时 30s 触发降级
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..engines.character import CharacterEngine, CharacterQuery
from ..engines.world import WorldEngine, WorldQuery
from ..consistency_guardian.guardian import (
    ConsistencyGuardian,
    GuardianInput,
    GuardianOutput,
    AlarmLevel,
    ActionRequired,
)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class UserAction:
    """用户操作"""
    type: str  # "analyze" / "check" / "predict" / "impact" / "finalize"
    payload: dict = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """执行计划"""
    engines_to_call: list[str]
    call_order: list[str]
    fallback_strategy: str = "skip"


@dataclass
class OrchestratorResult:
    """编排器结果"""
    success: bool
    engine_results: dict[str, Any]
    guardian_output: Optional[GuardianOutput]
    message: str = ""


# ---------------------------------------------------------------------------
# 路由规则
# ---------------------------------------------------------------------------

ROUTE_MAP = {
    "analyze": ["character_engine", "world_engine"],
    "check": ["world_engine"],
    "predict": ["character_engine"],
    "finalize": ["character_engine", "world_engine"],
}


# ---------------------------------------------------------------------------
# 编排器实现
# ---------------------------------------------------------------------------

class Orchestrator:
    """编排器 — Phase 1

    接收用户操作，路由到相应引擎，协调引擎返回结果。
    唯一有记忆写入权限的模块。
    """

    def __init__(
        self,
        character_engine: Optional[CharacterEngine] = None,
        world_engine: Optional[WorldEngine] = None,
        guardian: Optional[ConsistencyGuardian] = None,
        enricher: Optional[object] = None,
        retriever: Optional[object] = None,
        refiner: Optional[object] = None,
    ) -> None:
        """初始化编排器

        Args:
            character_engine: 角色引擎实例
            world_engine: 世界引擎实例
            guardian: 一致性守卫实例
            enricher: 语料自扩充器（可选，用于触发扩充回路）
            retriever: 语料检索器（可选，用于重建动态索引）
            refiner: 静态语料标注优化器（可选，用于反哺静态切片）
        """
        self._character_engine = character_engine
        self._world_engine = world_engine
        self._guardian = guardian or ConsistencyGuardian()
        self._enricher = enricher
        self._retriever = retriever
        self._refiner = refiner

    def execute(self, action: UserAction) -> OrchestratorResult:
        """执行用户操作

        Args:
            action: 用户操作

        Returns:
            OrchestratorResult: 执行结果
        """
        # 1. 生成执行计划
        plan = self._create_plan(action)

        # 2. 执行引擎调用
        engine_results = self._execute_engines(plan, action)

        # 3. 调用一致性守卫
        guardian_output = self._run_guardian(engine_results)

        # 4. 根据守卫结果决定后续动作
        if guardian_output.action_required == ActionRequired.BLOCK:
            return OrchestratorResult(
                success=False,
                engine_results=engine_results,
                guardian_output=guardian_output,
                message="一致性守卫阻断：存在 CRITICAL 冲突",
            )

        # 5. 写入记忆（Phase 1 简化：暂不实现实际写入）
        self._write_to_memory(engine_results, guardian_output)

        # 6. 触发语料扩充回路（M6 新增）
        self._trigger_enrichment(action, engine_results, guardian_output)

        # 7. 返回结果
        message = "执行成功"
        if guardian_output.action_required == ActionRequired.REVIEW:
            message = "执行成功，但存在 WARN 冲突，建议审查"

        return OrchestratorResult(
            success=True,
            engine_results=engine_results,
            guardian_output=guardian_output,
            message=message,
        )

    def _create_plan(self, action: UserAction) -> ExecutionPlan:
        """创建执行计划

        Args:
            action: 用户操作

        Returns:
            ExecutionPlan: 执行计划
        """
        engines = ROUTE_MAP.get(action.type, [])

        return ExecutionPlan(
            engines_to_call=engines,
            call_order=engines,  # Phase 1 串行执行
            fallback_strategy="skip",
        )

    def _execute_engines(
        self,
        plan: ExecutionPlan,
        action: UserAction
    ) -> dict[str, Any]:
        """执行引擎调用

        Args:
            plan: 执行计划
            action: 用户操作

        Returns:
            引擎结果字典
        """
        results = {}

        for engine_name in plan.call_order:
            try:
                if engine_name == "character_engine" and self._character_engine:
                    result = self._execute_character_engine(action)
                    results["character_engine"] = result

                elif engine_name == "world_engine" and self._world_engine:
                    result = self._execute_world_engine(action)
                    results["world_engine"] = result

            except Exception as e:
                # 降级策略：记录错误，继续执行
                results[engine_name] = {"error": str(e)}

        return results

    def _execute_character_engine(self, action: UserAction) -> Any:
        """执行角色引擎

        Args:
            action: 用户操作

        Returns:
            角色引擎结果
        """
        if not self._character_engine:
            return None

        payload = action.payload

        # 构建查询
        query = CharacterQuery(
            character_id=payload.get("character_id", ""),
            scene_text=payload.get("scene_text", ""),
        )

        return self._character_engine.analyze(query)

    def _execute_world_engine(self, action: UserAction) -> Any:
        """执行世界引擎

        Args:
            action: 用户操作

        Returns:
            世界引擎结果
        """
        if not self._world_engine:
            return None

        payload = action.payload

        # 构建查询
        query = WorldQuery(
            event_description=payload.get("event_description", ""),
            location=payload.get("location", ""),
            involved_characters=payload.get("involved_characters", []),
        )

        return self._world_engine.validate(query)

    def _run_guardian(self, engine_results: dict[str, Any]) -> GuardianOutput:
        """运行一致性守卫

        Args:
            engine_results: 引擎结果

        Returns:
            GuardianOutput: 守卫输出
        """
        input_data = GuardianInput(
            engine_results=engine_results,
            active_dimensions=["character", "world_rule", "spatial"],
        )

        return self._guardian.check(input_data)

    def _write_to_memory(
        self,
        engine_results: dict[str, Any],
        guardian_output: GuardianOutput
    ) -> None:
        """写入记忆

        Phase 1 简化：暂不实现实际写入。

        Args:
            engine_results: 引擎结果
            guardian_output: 守卫输出
        """
        # Phase 1 骨架：后续实现实际记忆写入
        pass

    def _trigger_enrichment(
        self,
        action: UserAction,
        engine_results: dict[str, Any],
        guardian_output: GuardianOutput,
    ) -> None:
        """触发语料扩充回路

        将高置信度的 LLM 分析结果转化为扩充切片，
        存入动态索引供后续检索使用。

        Args:
            action: 用户操作
            engine_results: 引擎结果
            guardian_output: 守卫输出
        """
        if not self._enricher:
            return

        try:
            scene_text = action.payload.get("scene_text", "")
            character_id = action.payload.get("character_id", "")

            if not scene_text:
                return

            self._enricher.enrich(
                scene_text=scene_text,
                character_id=character_id,
                engine_results=engine_results,
                guardian_output=guardian_output,
            )

            # 扩充后触发检索器重建动态索引
            if self._retriever:
                self._retriever.rebuild_dynamic_index()

            # 触发静态语料反哺回路（Item 1: Refiner）
            if self._refiner:
                self._refiner.refine(
                    engine_results=engine_results,
                    scene_text=scene_text,
                    character_id=character_id,
                )

        except Exception:
            pass  # 扩充/反哺失败不影响主流程
