---
name: dev-handoff-2026-07-14
description: 2026-07-14 维护者审查后交给开发者的修复清单
metadata:
  type: project
---

## 背景

维护者审查了 Phase A-D 产出（5 commits）+ 启动前端测试，发现 1 个阻塞性编译错误 + 2 个 bug + 4 个改进项。

## 优先级

### 🔴 P0 — 阻塞：前端编译错误

**文件**: `src-frontend/src/components/StickyBoard.tsx` 第 406-417 行
**症状**: 整个应用黑屏，React 无法渲染
**原因**: TSX 语法错误。`.map()` 回调内嵌套了 `{condition ? null : (<Component />)}` — TSX 解析器无法在 `{}` 表达式内处理三元 + JSX 括号组合
**期望**: 用 `.filter().map()` 替代当前的三元模式，或调整括号结构使 TSX 可解析

### 🟡 P1 — Bug 修复 (2)

**B1 — `continue_golden_three` 死变量**
- `src-tauri/crates/xmgl-tauri/src/commands.rs:515-519`
- 第 518 行 `let project_id = gts.project_id.clone()` 从未使用（编译器 warning）
- 变量名 `pctx` 暗示 ProjectContext 但实际是 GoldenThreeState，与 522 行的 `pctx_full` 混淆

**B2 — 黄金三章"重新生成"按钮行为错误**
- `src-frontend/src/components/GoldenThreeWizard.tsx:234`
- "🔄 重新生成"调用了 `handleContinue`，会递增 stage 跳到下一章
- 期望：重新生成当前章，不递增 stage

### 🟢 P2 — 改进 (4)

**E1** — 黄金三章 session 仅存内存，重启丢失 (`src-tauri/crates/xmgl-tauri/src/lib.rs:33`)
**E2** — `run_continuation` ProjectContext 注入了两次 metadata (`commands.rs:418-428`)
**M1** — `main.rs` 顶部 doc comment 过期（仍写 Phase B/D）
**M2** — TypeScript AgentId 类型缺 6 个新增 Agent (`types/index.ts:22-32`)

## 验证

1. `npx tsc --noEmit` — 零错误
2. `cargo check --workspace` — B1 warning 消失
3. `cargo test --workspace` — 全绿
4. 启动应用 → 看到白色界面 + 顶部工具栏（不再是黑屏）
5. 黄金三章：生成第一章 → 点"重新生成" → 确认重新生成的是第一章
