---
name: golden-three-bugs-2026-07-15
description: 黄金三章 3 个 bug — stage 3 resume 假成功、resume 不加载已生成章节、finalize 先删后存
metadata:
  type: project
---

## 黄金三章已知 Bug（2026-07-15 审查发现）

TG-0~6 修复后的回归审查发现了 3 个 bug：

### Bug 1 (严重): Stage 3 resume 生成垃圾，假报成功

**文件**: `src-tauri/crates/xmgl-tauri/src/commands.rs:554-576` + `src-frontend/src/components/GoldenThreeWizard.tsx:83-106`

**根因**: `handleResume` 对 stage 3 的 session 调用 `continueGoldenThree(session_id, undefined, false)`，Rust 端 `gts.stage += 1` → stage 变成 4。
- `target_stage = 4` 在 `match` 中走 `_ => vec![]` → 零前文上下文传给 LLM
- 生成的"第4章"被 `match target_stage { _ => {} }` 丢弃
- 前端 `result.stage === 4` 不匹配 2 或 3，走 `setStep(4)` → 显示"黄金三章已生成并保存！"
- 实际上什么都没保存（从未调 `handleFinalize`）

### Bug 2 (高): Resume 不加载已生成章节到前端状态

**文件**: `src-frontend/src/components/GoldenThreeWizard.tsx:90-98`

**根因**: `handleResume` 只调 `continueGoldenThree` 生成下一章，不从 DB 恢复已有章节到 `chapters` 状态。
- `chapters.ch1` 保持 `""`（虽然 SQLite + HashMap 里都有）
- 用户看不到已生成的内容

### Bug 3 (高): `finalize_golden_three` 先删 session 再保存章节

**文件**: `src-tauri/crates/xmgl-tauri/src/commands.rs:597-615` + `src-frontend/src/components/GoldenThreeWizard.tsx:172-187`

**根因**: Rust `finalize_golden_three` 立即从 HashMap + SQLite 删除 session，再返回三章文本。前端逐章 `createChapter`，任一失败则无法重试。

## 修复方向

1. **Bug 1**: `handleResume` 对 stage 3 应直接调 `finalizeGoldenThree` 而非 `continueGoldenThree`。或 Rust 端在 stage 3 且 `!regenerate` 时返回错误。
2. **Bug 2**: `handleResume` 前应先从 `resumeGoldenThree` 的返回值中恢复已有章节到 `chapters` 状态。需扩展 `ResumableSession` 接口携带章节文本。
3. **Bug 3**: `finalize_golden_three` 应只标记 session 为完成（如 stage=4），不删除。前端保存成功后再调 `delete_golden_three_session` 清理。

**Why**: TG-1 新增了持久化 + resume 能力，但 resume 路径未充分测试，三个边界条件未覆盖。

**How to apply**: 在开发者窗口按上述方向修复，优先 Bug 1，其次 Bug 2/3。修复后需端到端测试正常流程 + 恢复流程。
