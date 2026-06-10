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
    pad_annotations: list[dict] = field(default_factory=list)


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
        self._slice_source_files: dict[str, str] = {}  # slice_id → source file path

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
                            self._slice_source_files[slice_obj.slice_id] = str(slice_file)
                            loaded_count += 1
                    else:
                        # 单个对象格式
                        slice_obj = self._parse_slice(data)
                        self._slices[slice_obj.slice_id] = slice_obj
                        self._slice_source_files[slice_obj.slice_id] = str(slice_file)
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

    def update_slice_metadata(self, slice_id: str, updates: dict) -> bool:
        """更新切片 metadata（追加模式，Item 1 Refiner）

        将 LLM 分析生成的新标注追加到静态切片的 metadata 中，
        不覆盖人工标注。同时将更新持久化到源文件。

        Args:
            slice_id: 切片 ID
            updates: 更新字典，支持以下字段：
                - emotion: str — 新的情感标签（替换现有）
                - tags: list[str] — 追加的行为标签（去重）
                - pad_annotations: list[dict] — 追加的 PAD 标注

        Returns:
            是否成功更新
        """
        import os as _os
        import tempfile as _tempfile

        slice_obj = self._slices.get(slice_id)
        if not slice_obj:
            return False

        changed = False

        # emotion：覆盖（LLM 标注优先于人工中性标注）
        new_emotion = updates.get("emotion")
        if new_emotion and isinstance(new_emotion, str):
            slice_obj.metadata.emotion = new_emotion
            changed = True

        # tags：追加去重
        new_tags = updates.get("tags", [])
        if new_tags:
            existing = set(slice_obj.metadata.tags)
            added = [t for t in new_tags if t not in existing]
            if added:
                slice_obj.metadata.tags.extend(added)
                changed = True

        # pad_annotations：追加
        new_pad = updates.get("pad_annotations", [])
        if new_pad:
            slice_obj.metadata.pad_annotations.extend(new_pad)
            changed = True

        if not changed:
            return False

        # 持久化到源文件
        source_file = self._slice_source_files.get(slice_id)
        if source_file and _os.path.exists(source_file):
            self._persist_slice_update(slice_id, source_file)

        return True

    def _persist_slice_update(self, updated_slice_id: str, source_file: str) -> None:
        """将更新后的切片持久化到源文件（处理多切片文件）

        读取整个源文件 → 更新目标切片 → 原子写入。
        """
        import os as _os
        import tempfile as _tempfile

        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        # 将数据标准化为数组
        is_array = isinstance(data, list)
        entries = data if is_array else [data]

        # 找到并更新目标切片
        for i, entry in enumerate(entries):
            if entry.get("slice_id") == updated_slice_id:
                slice_obj = self._slices[updated_slice_id]
                # 更新 metadata 部分
                if "metadata" not in entry:
                    entry["metadata"] = {}
                entry["metadata"]["emotion"] = slice_obj.metadata.emotion
                entry["metadata"]["tags"] = slice_obj.metadata.tags
                entry["metadata"]["pad_annotations"] = slice_obj.metadata.pad_annotations
                entries[i] = entry
                break

        # 原子写入
        dirpath = _os.path.dirname(source_file)
        fd, tmp_path = _tempfile.mkstemp(
            suffix=".json", prefix="refiner_", dir=dirpath
        )
        try:
            with _os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(
                    entries if is_array else entries[0],
                    f, ensure_ascii=False, indent=2
                )
            _os.replace(tmp_path, source_file)
        except Exception:
            if _os.path.exists(tmp_path):
                _os.unlink(tmp_path)
            raise

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
            pad_annotations=data.get("metadata", {}).get("pad_annotations", []),
        )

        return CorpusSlice(
            slice_id=data["slice_id"],
            source=data["source"],
            chapter=data["chapter"],
            text=data["text"],
            metadata=metadata,
        )
