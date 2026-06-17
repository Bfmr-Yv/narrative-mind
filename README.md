# Narrative Mind v4.0

> AI 辅助小说创作 IDE —— 多 Agent 协作写作系统

## 这是什么

Narrative Mind 是一个桌面写作 IDE，集成了 9 个 AI Agent 协作系统。它在编辑器中直接提供修改建议，帮助作家提升作品质量。

## 核心特性

- **多 Agent 协作**：9 个专业 Agent（角色、世界、叙事、文辞、主题、经济、预期、构思、总编）协同工作
- **内联修改建议**：Agent 建议直接显示在编辑器原文中，双击即采纳
- **作家主导**：所有决策由作家做出，Agent 只提供建议
- **主动 + 被动**：手动触发分析或自动后台监控（500 字增量）
- **成本可控**：本地规则引擎优先，仅在必要时调用 LLM

## 技术栈

- **桌面框架**: Tauri 2.x (Rust)
- **编辑器**: Monaco Editor
- **前端**: React 18 + Vite + Zustand
- **LLM 集成**: Python FastAPI sidecar
- **存储**: SQLite

## 状态

**Phase A — 脚手架 ✅ 完成**（2026-06-17 验证通过）

### 已有成果

| 组件 | 状态 | 说明 |
|------|------|------|
| Rust 核心 (7 crates) | ✅ | workspace 编译通过，类型系统完整，每 crate ≥1 test |
| Tauri 桌面框架 | ✅ | 窗口弹出正常，前端页面可渲染 |
| Python Sidecar (FastAPI) | ✅ | 健康检查通过，6 个 API 端点骨架就位 |
| 前端骨架 (React + Monaco) | ✅ | Vite dev server + Tauri webview 集成 |
| 语料数据 | 样本 | 红楼梦 4 条 500 字场景切片 |

### 下一步: Phase B — 数据层

- SQLite schema + migration
- 项目/章节 CRUD
- 旧版 v3.1 数据迁移
- 首批 Tauri commands (`list_projects`, `create_project`, `get_chapter`, `update_chapter`)
