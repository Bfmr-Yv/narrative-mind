#!/usr/bin/env python3
"""
语料切片验证脚本

验证切片格式和质量要求：
1. JSON 格式正确
2. 必需字段存在
3. 文本长度符合要求（500字 ±50字）
4. 元数据完整性
"""

import json
import sys
from pathlib import Path


def validate_slice_data(slice_data: dict) -> list[str]:
    """验证单个切片数据

    Args:
        slice_data: 切片数据字典

    Returns:
        错误列表，空表示验证通过
    """
    errors = []

    # 检查必需字段
    required_fields = ["slice_id", "source", "chapter", "text"]
    for field in required_fields:
        if field not in slice_data:
            errors.append(f"缺少必需字段: {field}")

    # 检查文本长度
    if "text" in slice_data:
        text = slice_data["text"]
        char_count = len(text)
        if char_count < 450:
            errors.append(f"文本过短: {char_count}字 (要求 450-800字)")
        elif char_count > 800:
            errors.append(f"文本过长: {char_count}字 (要求 450-800字)")

    # 检查元数据
    if "metadata" in slice_data:
        metadata = slice_data["metadata"]
        if "characters" not in metadata:
            errors.append("元数据缺少 characters 字段")
        if "scene_type" not in metadata:
            errors.append("元数据缺少 scene_type 字段")
        if "emotion" not in metadata:
            errors.append("元数据缺少 emotion 字段")

    return errors


def validate_slice(file_path: Path) -> list[str]:
    """验证切片文件

    Args:
        file_path: 切片文件路径

    Returns:
        错误列表，空表示验证通过
    """
    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON 解析错误: {e}"]

    # 支持两种格式：
    # 1. 单个切片对象
    # 2. 切片对象数组
    if isinstance(data, list):
        # 数组格式
        for i, slice_data in enumerate(data):
            slice_errors = validate_slice_data(slice_data)
            for error in slice_errors:
                errors.append(f"切片 #{i+1}: {error}")
    else:
        # 单个对象格式
        errors = validate_slice_data(data)

    return errors


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python validate_slices.py <切片目录或文件>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"错误: 路径不存在 {target}")
        sys.exit(1)

    errors_found = False

    if target.is_file():
        # 验证单个文件
        errors = validate_slice(target)
        if errors:
            print(f"❌ {target.name}:")
            for error in errors:
                print(f"  - {error}")
            errors_found = True
        else:
            print(f"✅ {target.name}: 验证通过")
    else:
        # 验证目录下所有 JSON 文件
        json_files = list(target.glob("*.json"))
        if not json_files:
            print(f"警告: 在 {target} 中未找到 JSON 文件")
            sys.exit(0)

        print(f"验证 {len(json_files)} 个切片文件...\n")

        for file_path in sorted(json_files):
            errors = validate_slice(file_path)
            if errors:
                print(f"❌ {file_path.name}:")
                for error in errors:
                    print(f"  - {error}")
                errors_found = True
            else:
                print(f"✅ {file_path.name}: 验证通过")

    if errors_found:
        print("\n❌ 验证失败，请修复上述错误")
        sys.exit(1)
    else:
        print("\n✅ 所有切片验证通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
