#!/usr/bin/env python3
"""
检查切片文本长度
"""

import json
from pathlib import Path


def check_file(file_path: Path):
    """检查文件中的切片文本长度"""
    print(f"\n检查文件: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, list):
        print(f"找到 {len(data)} 个切片")
        for i, slice_data in enumerate(data):
            slice_id = slice_data.get("slice_id", f"未知_{i}")
            text = slice_data.get("text", "")
            length = len(text)
            status = "✅" if 450 <= length <= 550 else "❌"
            print(f"  {status} {slice_id}: {length}字")
    else:
        slice_id = data.get("slice_id", "未知")
        text = data.get("text", "")
        length = len(text)
        status = "✅" if 450 <= length <= 550 else "❌"
        print(f"  {status} {slice_id}: {length}字")


def main():
    """主函数"""
    corpus_dir = Path("corpus")
    
    # 检查所有JSON文件
    for json_file in corpus_dir.rglob("*.json"):
        check_file(json_file)


if __name__ == "__main__":
    main()
