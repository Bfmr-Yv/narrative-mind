"""
项目管理器 — Phase 1

职责：管理用户创作项目的文件存储（JSON 文件系统）。
每个项目独立存储角色、地点、世界设定和章节。
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# =========================================================================
# 数据模型
# =========================================================================

@dataclass
class ProjectMeta:
    """项目元数据"""
    id: str
    name: str
    created: str = ""
    updated: str = ""
    total_words: int = 0
    chapter_count: int = 0


@dataclass
class ProjectSettings:
    """项目设定"""
    characters: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    power_system: dict = field(default_factory=dict)


@dataclass
class ChapterData:
    """章节数据"""
    id: str
    title: str
    text: str = ""
    created: str = ""
    updated: str = ""


# =========================================================================
# 存储层
# =========================================================================

class ProjectManager:
    """项目文件存储管理器"""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    # ---- Project CRUD ----

    def list_projects(self) -> list[ProjectMeta]:
        """列出所有项目"""
        projects: list[ProjectMeta] = []
        if not self._base.exists():
            return projects

        for proj_dir in sorted(self._base.iterdir()):
            if not proj_dir.is_dir():
                continue
            meta_file = proj_dir / "project.json"
            if not meta_file.exists():
                continue
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                chapters_dir = proj_dir / "chapters"
                chapter_count = 0
                total_words = 0
                if chapters_dir.exists():
                    for ch_file in chapters_dir.glob("*.json"):
                        try:
                            ch = json.loads(ch_file.read_text(encoding="utf-8"))
                            chapter_count += 1
                            total_words += len(ch.get("text", ""))
                        except Exception:
                            pass

                projects.append(ProjectMeta(
                    id=data["id"],
                    name=data["name"],
                    created=data.get("created", ""),
                    updated=data.get("updated", ""),
                    total_words=total_words,
                    chapter_count=chapter_count,
                ))
            except Exception:
                continue

        projects.sort(key=lambda p: p.updated, reverse=True)
        return projects

    def get_project(self, project_id: str) -> Optional[dict]:
        """获取单个项目详情"""
        meta_file = self._base / project_id / "project.json"
        if not meta_file.exists():
            return None
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        settings = self.get_settings(project_id)
        data["settings"] = settings.__dict__ if settings else {}
        return data

    def create_project(self, name: str, template_settings: Optional[dict] = None) -> ProjectMeta:
        """创建新项目"""
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        proj_dir = self._base / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "chapters").mkdir(exist_ok=True)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta = {
            "id": project_id,
            "name": name,
            "created": now,
            "updated": now,
        }
        (proj_dir / "project.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 从模板或默认值创建设定
        if template_settings is None:
            template_settings = {
                "characters": [],
                "locations": [],
                "power_system": {
                    "name": "通用力量体系",
                    "levels": [{"name": "普通人", "capabilities": ["基础体能", "日常技能"]}],
                    "rules": [],
                },
            }
        (proj_dir / "settings.json").write_text(
            json.dumps(template_settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return ProjectMeta(
            id=project_id,
            name=name,
            created=now,
            updated=now,
            total_words=0,
            chapter_count=0,
        )

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        proj_dir = self._base / project_id
        if not proj_dir.exists():
            return False
        shutil.rmtree(proj_dir)
        return True

    def update_project_timestamp(self, project_id: str) -> None:
        """更新项目时间戳"""
        meta_file = self._base / project_id / "project.json"
        if meta_file.exists():
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            meta_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- Settings ----

    def get_settings(self, project_id: str) -> Optional[ProjectSettings]:
        """获取项目设定"""
        settings_file = self._base / project_id / "settings.json"
        if not settings_file.exists():
            return None
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        return ProjectSettings(
            characters=data.get("characters", []),
            locations=data.get("locations", []),
            power_system=data.get("power_system", {}),
        )

    def save_settings(self, project_id: str, settings: ProjectSettings) -> bool:
        """保存项目设定"""
        proj_dir = self._base / project_id
        if not proj_dir.exists():
            return False
        settings_file = proj_dir / "settings.json"
        settings_file.write_text(
            json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.update_project_timestamp(project_id)
        return True

    # ---- Chapters ----

    def list_chapters(self, project_id: str) -> list[ChapterData]:
        """列出项目章节"""
        chapters_dir = self._base / project_id / "chapters"
        if not chapters_dir.exists():
            return []

        chapters: list[ChapterData] = []
        for ch_file in sorted(chapters_dir.glob("*.json")):
            try:
                data = json.loads(ch_file.read_text(encoding="utf-8"))
                chapters.append(ChapterData(
                    id=data["id"],
                    title=data.get("title", ""),
                    text=data.get("text", ""),
                    created=data.get("created", ""),
                    updated=data.get("updated", ""),
                ))
            except Exception:
                continue
        return chapters

    def create_chapter(self, project_id: str, title: str = "") -> Optional[ChapterData]:
        """创建新章节"""
        proj_dir = self._base / project_id
        if not proj_dir.exists():
            return None

        chapters_dir = proj_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        ch_id = f"ch-{uuid.uuid4().hex[:6]}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ch_data = {
            "id": ch_id,
            "title": title or f"新章节",
            "text": "",
            "created": now,
            "updated": now,
        }
        (chapters_dir / f"{ch_id}.json").write_text(
            json.dumps(ch_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.update_project_timestamp(project_id)

        return ChapterData(
            id=ch_id,
            title=ch_data["title"],
            text="",
            created=now,
            updated=now,
        )

    def save_chapter(self, project_id: str, chapter_id: str, title: str, text: str) -> bool:
        """保存章节"""
        ch_file = self._base / project_id / "chapters" / f"{chapter_id}.json"
        if not ch_file.exists():
            return False

        data = json.loads(ch_file.read_text(encoding="utf-8"))
        data["title"] = title
        data["text"] = text
        data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ch_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.update_project_timestamp(project_id)
        return True

    def delete_chapter(self, project_id: str, chapter_id: str) -> bool:
        """删除章节"""
        ch_file = self._base / project_id / "chapters" / f"{chapter_id}.json"
        if not ch_file.exists():
            return False
        ch_file.unlink()
        self.update_project_timestamp(project_id)
        return True

    def get_chapter(self, project_id: str, chapter_id: str) -> Optional[ChapterData]:
        """获取单个章节"""
        ch_file = self._base / project_id / "chapters" / f"{chapter_id}.json"
        if not ch_file.exists():
            return None
        data = json.loads(ch_file.read_text(encoding="utf-8"))
        return ChapterData(
            id=data["id"],
            title=data.get("title", ""),
            text=data.get("text", ""),
            created=data.get("created", ""),
            updated=data.get("updated", ""),
        )
