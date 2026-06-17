# Narrative Mind

AI 辅助长篇小说创作 IDE。将 9 个专业 AI Agent 嵌入编辑器，在作家写作时实时提供修改建议。

## 设计理念

写作是孤独的。好作品需要反复打磨，但每个人都缺一个好编辑。

Narrative Mind 不是替作家写作，而是像一位坐在身边的好编辑——发现问题、提出建议、但不替你动笔。Agent 的建议直接标注在编辑器原文中，双击采纳，右键退回，作家始终是最终裁决者。

## 架构

```
┌─ Tauri 桌面窗口 ──────────────────────────────┐
│  Monaco Editor  ·  React  ·  Zustand           │
│        ↕ Tauri IPC                             │
│  Rust Core（7 crates）                          │
│        ↕ HTTP :9091                            │
│  Python Sidecar（LLM + 语料 + Prompt 管理）      │
└────────────────────────────────────────────────┘
```

| 层 | 技术 |
|----|------|
| 桌面框架 | Tauri 2.x |
| 编辑器 | Monaco Editor |
| 前端 | React 18 + Vite + Zustand |
| 核心引擎 | Rust（7 crates） |
| LLM 集成 | Python FastAPI Sidecar |
| 存储 | SQLite |

## 当前状态

Phase A 脚手架已完成，项目可编译运行。正在进行 Phase B 数据层开发。

```bash
# 启动
cd src-python && python main.py           # Python Sidecar → :9091
cd src-frontend && npm run dev            # 前端 → :1420
cd src-tauri && cargo tauri dev           # 桌面窗口
```

## 许可

MIT License © 2026 Bfmr
