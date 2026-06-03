"""
Narrative Mind v3.1 — CLI 入口

Phase 1 骨架：命令行参数解析 + 引擎路由入口。
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器

    Returns:
        配置好的 ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog="narrative-mind",
        description="Narrative Mind v3.1 — AI 辅助小说创作系统",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # analyze — 全量分析
    analyze_parser = subparsers.add_parser("analyze", help="全量分析（角色 + 世界）")
    analyze_parser.add_argument("--character-id", type=str, help="角色唯一标识")
    analyze_parser.add_argument("--scene-text", type=str, help="当前场景文本")

    # check — 设定校验
    check_parser = subparsers.add_parser("check", help="世界设定校验")
    check_parser.add_argument("--event", type=str, help="事件描述")
    check_parser.add_argument("--location", type=str, help="发生地点")

    # predict — 行为预测
    predict_parser = subparsers.add_parser("predict", help="角色行为预测")
    predict_parser.add_argument("--character-id", type=str, required=True, help="角色唯一标识")
    predict_parser.add_argument("--scene-text", type=str, required=True, help="当前场景文本")

    # impact — 级联影响检查
    subparsers.add_parser("impact", help="级联影响检查（Phase 1 关键词扫描）")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI 主入口

    Args:
        argv: 命令行参数列表，None 时使用 sys.argv

    Returns:
        退出码（0 成功，非 0 失败）
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Phase 1 骨架：命令路由未实现
    print(f"[Phase 1 骨架] 命令 '{args.command}' 已识别，引擎路由待实现")
    return 0


if __name__ == "__main__":
    sys.exit(main())
