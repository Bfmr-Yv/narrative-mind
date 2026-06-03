"""
Narrative Mind v3.1 — Memory System Package

Phase 1 简化版: 仅工作记忆 (Working Memory)

三层模型（Phase 2+ 完整实现）:
- 工作记忆 (Working Memory): 会话级，内存存储
- 情节记忆 (Episodic Memory): 章节级，SQLite
- 永久记忆 (Permanent Memory): 跨书级，SQLite + LanceDB

契约（来源：02-CONTRACTS.md）：
- 只有编排器有写入权限
- 读取无限制，返回数据必须带 last_modified 时间戳
- 工作记忆不持久化
"""

from .working_memory import WorkingMemory

__all__ = ["WorkingMemory"]
