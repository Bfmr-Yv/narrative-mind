"""
分析历史持久化存储 (AnalysisStore) — Phase 1 Item 4

职责：将每次编排器分析结果持久化到项目目录，支持跨会话查询。
存储路径：projects/<project_id>/chapters/<chapter_id>/analysis_history.json
"""
from __future__ import annotations

import json
import os
import uuid
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AnalysisRecord:
    """分析记录"""
    analysis_id: str          # "an-<uuid8>"
    timestamp: str            # ISO format
    character_id: str
    location: str
    chapter_id: str
    project_id: str
    response_summary: dict    # 不含完整 response body 的概要
    response: dict            # 完整的 OrchestratorResult 序列化结果


class AnalysisStore:
    """分析历史持久化存储

    每个章节最多 50 条记录，超出时移除最旧的。
    """

    MAX_RECORDS = 50

    def __init__(self, base_dir: str) -> None:
        """初始化

        Args:
            base_dir: 项目根目录（如 projects/）
        """
        self._base_dir = base_dir
        self._total_count = 0

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def save(
        self,
        project_id: str,
        chapter_id: str,
        character_id: str,
        location: str,
        response: dict,
    ) -> AnalysisRecord:
        """保存分析记录

        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            character_id: 角色 ID
            location: 地点名称
            response: 编排器完整响应（已序列化为 dict）

        Returns:
            AnalysisRecord: 新创建的分析记录
        """
        from datetime import datetime, timezone, timedelta

        # 生成 ID 和时间戳
        analysis_id = f"an-{uuid.uuid4().hex[:8]}"
        tz_cst = timezone(timedelta(hours=8))
        timestamp = datetime.now(tz_cst).isoformat(timespec="seconds")

        # 生成概要（不含完整 response body，用于列表视图）
        response_summary = self._make_summary(response)

        record = AnalysisRecord(
            analysis_id=analysis_id,
            timestamp=timestamp,
            character_id=character_id,
            location=location,
            chapter_id=chapter_id,
            project_id=project_id,
            response_summary=response_summary,
            response=response,
        )

        # 加载现有记录
        records = self._load(project_id, chapter_id)

        # 追加新记录
        records.append(record)

        # 上限控制：保留最新的 MAX_RECORDS 条
        if len(records) > self.MAX_RECORDS:
            records = records[-self.MAX_RECORDS:]

        # 原子写入
        self._save(project_id, chapter_id, records)
        self._total_count += 1

        return record

    def get_history(
        self, project_id: str, chapter_id: str
    ) -> list[dict]:
        """获取分析历史列表（不含完整 response body）

        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID

        Returns:
            记录列表（概要），按时间倒序
        """
        records = self._load(project_id, chapter_id)
        return [
            {
                "analysis_id": r.analysis_id,
                "timestamp": r.timestamp,
                "character_id": r.character_id,
                "location": r.location,
                "chapter_id": r.chapter_id,
                "project_id": r.project_id,
                "response_summary": r.response_summary,
            }
            for r in reversed(records)
        ]

    def get_detail(
        self, project_id: str, chapter_id: str, analysis_id: str
    ) -> Optional[dict]:
        """获取单条分析详情（含完整 response body）

        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            analysis_id: 分析记录 ID

        Returns:
            完整记录 dict 或 None
        """
        records = self._load(project_id, chapter_id)
        for r in records:
            if r.analysis_id == analysis_id:
                return {
                    "analysis_id": r.analysis_id,
                    "timestamp": r.timestamp,
                    "character_id": r.character_id,
                    "location": r.location,
                    "chapter_id": r.chapter_id,
                    "project_id": r.project_id,
                    "response_summary": r.response_summary,
                    "response": r.response,
                }
        return None

    def delete(
        self, project_id: str, chapter_id: str, analysis_id: str
    ) -> bool:
        """删除单条分析记录

        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            analysis_id: 分析记录 ID

        Returns:
            是否成功删除
        """
        records = self._load(project_id, chapter_id)
        original_len = len(records)
        records = [r for r in records if r.analysis_id != analysis_id]
        if len(records) == original_len:
            return False
        self._save(project_id, chapter_id, records)
        return True

    def clear(self, project_id: str, chapter_id: str) -> None:
        """清空章节的分析历史

        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
        """
        filepath = self._filepath(project_id, chapter_id)
        if os.path.exists(filepath):
            os.remove(filepath)

    def total_count(self) -> int:
        """返回全局记录总数（近似值）"""
        return self._total_count

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _filepath(self, project_id: str, chapter_id: str) -> str:
        """获取分析历史文件路径"""
        dirpath = os.path.join(
            self._base_dir, project_id, "chapters", chapter_id
        )
        return os.path.join(dirpath, "analysis_history.json")

    def _load(self, project_id: str, chapter_id: str) -> list[AnalysisRecord]:
        """从文件加载分析记录"""
        filepath = self._filepath(project_id, chapter_id)
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [
                AnalysisRecord(
                    analysis_id=item["analysis_id"],
                    timestamp=item["timestamp"],
                    character_id=item.get("character_id", ""),
                    location=item.get("location", ""),
                    chapter_id=item.get("chapter_id", ""),
                    project_id=item.get("project_id", ""),
                    response_summary=item.get("response_summary", {}),
                    response=item.get("response", {}),
                )
                for item in data
            ]
        except (json.JSONDecodeError, KeyError, OSError):
            return []

    def _save(
        self,
        project_id: str,
        chapter_id: str,
        records: list[AnalysisRecord],
    ) -> None:
        """原子写入分析记录到文件

        使用 temp file + os.replace 策略确保写入原子性。
        """
        filepath = self._filepath(project_id, chapter_id)
        dirpath = os.path.dirname(filepath)
        os.makedirs(dirpath, exist_ok=True)

        data = []
        for r in records:
            data.append({
                "analysis_id": r.analysis_id,
                "timestamp": r.timestamp,
                "character_id": r.character_id,
                "location": r.location,
                "chapter_id": r.chapter_id,
                "project_id": r.project_id,
                "response_summary": r.response_summary,
                "response": r.response,
            })

        # 原子写入：先写临时文件，再替换
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix="analysis_", dir=dirpath
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    @staticmethod
    def _make_summary(response: dict) -> dict:
        """从完整响应生成概要（去除冗余数据）"""
        cr = response.get("engine_results", {}).get("character_engine", {})
        g = response.get("guardian_output", {})

        return {
            "message": response.get("message", ""),
            "character_confidence": cr.get("confidence"),
            "pad_state": cr.get("pad_state"),
            "predicted_action": (
                cr.get("behavior_prediction", {}).get("predicted_action")
                if cr.get("behavior_prediction") else None
            ),
            "alarm_level": g.get("alarm_level", "info"),
            "conflict_count": len(g.get("conflicts", [])),
            "needs_human_review": cr.get("needs_human_review", False),
        }
