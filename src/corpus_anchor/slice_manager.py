"""
切片管理器 — Phase 1

职责：管理语料切片的加载、存储和元数据。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SliceMetadata:
    """切片元数据"""
    characters: list[str] = field(default_factory=list)
    scene_type: str = "unknown"  # dialogue/action/description/narration
    emotion: str = "neutral"
    tags: list[str] = field(default_factory=list)


@dataclass
class CorpusSlice:
    """语料切片"""
    slice_id: str
    source: str  # 来源作品
    chapter: str  # 章节
    text: str  # 500字场景级文本
    metadata: SliceMetadata = field(default_factory=SliceMetadata)


class SliceManager:
    """切片管理器 — Phase 1

    管理语料切片的加载、存储和元数据。
    切片标准：500字场景级（ADR-013）。
    """

    def __init__(self, corpus_dir: Optional[str] = None) -> None:
        """初始化切片管理器

        Args:
            corpus_dir: 语料目录路径
        """
        self._corpus_dir = Path(corpus_dir) if corpus_dir else None
        self._slices: dict[str, CorpusSlice] = {}

    def load_slices(self, directory: Optional[str] = None) -> int:
        """从目录加载切片

        Args:
            directory: 切片目录路径（覆盖初始化路径）

        Returns:
            加载的切片数量

        Raises:
            FileNotFoundError: 当目录不存在时
        """
        target_dir = Path(directory) if directory else self._corpus_dir
        if not target_dir or not target_dir.exists():
            raise FileNotFoundError(f"Corpus directory not found: {target_dir}")

        loaded_count = 0
        for slice_file in target_dir.glob("*.json"):
            try:
                with open(slice_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 支持两种格式：
                    # 1. 单个切片对象
                    # 2. 切片对象数组
                    if isinstance(data, list):
                        # 数组格式
                        for slice_data in data:
                            slice_obj = self._parse_slice(slice_data)
                            self._slices[slice_obj.slice_id] = slice_obj
                            loaded_count += 1
                    else:
                        # 单个对象格式
                        slice_obj = self._parse_slice(data)
                        self._slices[slice_obj.slice_id] = slice_obj
                        loaded_count += 1
            except (json.JSONDecodeError, KeyError) as e:
                # 记录错误但继续加载其他切片
                print(f"Warning: Failed to load {slice_file}: {e}")

        return loaded_count

    def get_slice(self, slice_id: str) -> Optional[CorpusSlice]:
        """获取切片

        Args:
            slice_id: 切片 ID

        Returns:
            切片对象，若不存在则返回 None
        """
        return self._slices.get(slice_id)

    def get_all_slices(self) -> list[CorpusSlice]:
        """获取所有切片

        Returns:
            切片列表
        """
        return list(self._slices.values())

    def get_slices_by_source(self, source: str) -> list[CorpusSlice]:
        """按来源作品筛选切片

        Args:
            source: 来源作品名称

        Returns:
            该作品的切片列表
        """
        return [s for s in self._slices.values() if s.source == source]

    def get_slices_by_character(self, character_id: str) -> list[CorpusSlice]:
        """按角色筛选切片

        Args:
            character_id: 角色 ID

        Returns:
            包含该角色的切片列表
        """
        return [
            s for s in self._slices.values()
            if character_id in s.metadata.characters
        ]

    def add_slice(self, slice_obj: CorpusSlice) -> None:
        """添加切片

        Args:
            slice_obj: 切片对象
        """
        self._slices[slice_obj.slice_id] = slice_obj

    def remove_slice(self, slice_id: str) -> bool:
        """移除切片

        Args:
            slice_id: 切片 ID

        Returns:
            是否成功移除
        """
        if slice_id in self._slices:
            del self._slices[slice_id]
            return True
        return False

    def save_slice(self, slice_obj: CorpusSlice, directory: Optional[str] = None) -> None:
        """保存切片到文件

        Args:
            slice_obj: 切片对象
            directory: 保存目录（覆盖初始化路径）
        """
        target_dir = Path(directory) if directory else self._corpus_dir
        if not target_dir:
            raise ValueError("No corpus directory specified")

        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{slice_obj.slice_id}.json"

        data = {
            "slice_id": slice_obj.slice_id,
            "source": slice_obj.source,
            "chapter": slice_obj.chapter,
            "text": slice_obj.text,
            "metadata": {
                "characters": slice_obj.metadata.characters,
                "scene_type": slice_obj.metadata.scene_type,
                "emotion": slice_obj.metadata.emotion,
                "tags": slice_obj.metadata.tags,
            }
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _parse_slice(self, data: dict) -> CorpusSlice:
        """解析切片数据

        Args:
            data: 切片字典数据

        Returns:
            切片对象
        """
        metadata = SliceMetadata(
            characters=data.get("metadata", {}).get("characters", []),
            scene_type=data.get("metadata", {}).get("scene_type", "unknown"),
            emotion=data.get("metadata", {}).get("emotion", "neutral"),
            tags=data.get("metadata", {}).get("tags", []),
        )

        return CorpusSlice(
            slice_id=data["slice_id"],
            source=data["source"],
            chapter=data["chapter"],
            text=data["text"],
            metadata=metadata,
        )
