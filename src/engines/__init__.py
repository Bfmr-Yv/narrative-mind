"""
Narrative Mind v3.1 — Engines Package

Phase 1 激活引擎:
- Character Engine (角色引擎)
- World Engine (世界引擎)

Phase 2+ 引擎（禁止在 Phase 1 引用）:
- Narrative Engine, Prose Engine, Theme Engine,
  Economy Engine, Reader Expectation Engine, Conception Engine
"""

from .character import CharacterEngine
from .world import WorldEngine

__all__ = ["CharacterEngine", "WorldEngine"]
