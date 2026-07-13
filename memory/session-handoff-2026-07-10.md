---
phase: 内容质量改进 — Prompt 管线修复（TG 1-4 完成）
progress: TG 1 ✅ | TG 2 ✅ | TG 3a ✅ | TG 4 ✅ | TG 3b 待讨论
next: 端到端验证（需 LLM API）+ 死 prompt 处理方案讨论（TG 3b）
warnings:
  - ⚠️ 网络不可用，2 个 commit 未推送（本地已提交）
  - 🟡 7 个 prompt 仍是死代码（TG 3b 待架构讨论）
  - 🟡 实体富提取未端到端验证（需要 LLM API key）
commits:
  - 7bb28ba fix: TG 1-4 实体提取管线+PAD全零+伏笔prompt+前端死代码
  - b40ad1c fix: TG 1b — 实体提取 LLM 输出从字符串升级为富对象
---

## 今日产出

### 维护者：Prompt 管线完整审查
- 审查 `xmgl-llm/src/prompts.rs`（17 个 prompt）+ 关联管线代码
- 发现 4 类问题：实体管线断裂（Critical）、PAD 全零、伏笔检测弱、7 个死 prompt（41%）
- 输出详细审查报告 + 4 任务计划（TG 1-4）

### 开发者：两轮实现

**第一轮（7bb28ba）— TG 1-4 批量修复**
- 修复 `extract_entities()` 字符串→结构体转换（管线断裂修复）
- 修复 PAD key 不匹配 bug（`chapter_text` → `scene_text`）+ metadata 穿透 + 零值防护
- 伏笔 prompt 增加具体示例 + 置信度指导 + 防过度标记
- 前端清理：StickyBoard 移除未用 import，AnalysisPanel 去重

**第二轮（b40ad1c）— TG 1b 实体富对象升级**
- `ENTITY_EXTRACT_SYSTEM` 完整重写：从名字列表升级为富对象（含 role/summary/status/aliases/location_type/description/features/parent_location）
- `extract_entities()` 对象分支改为手动逐字段提取（防御 LLM 输出波动）
- 字符串分支保留作向后兼容

### 审查结果
- 两轮都通过：cargo check ✅ + 116 tests ✅

## 待审查

- 端到端验证：启动应用 → 打开章节 → 触发分析 → 检查 LibraryPanel 实体卡片是否展示名称+角色+描述
- PAD 值是否从全零变为有意义的非零值（需实际 LLM 调用验证）

## 注意事项

- 网络不稳定，push 失败。明天开工先 `git push`
- `uuid` crate 已加入 orchestrator 依赖（Cargo.toml）
- 实体提取现在支持三种格式：纯字符串（旧）→ 简单字段（7bb28ba）→ 富对象（b40ad1c），全部兼容

## 环境状态

| 项目 | 状态 |
|------|------|
| cargo check | ✅（6 pre-existing warnings） |
| cargo test | ✅ 116 passed, 0 failed, 1 ignored |
| 前端 | 未检查（改动仅 import 清理） |
| git | ⚠️ 未推送（2 commits ahead） |
| 网络 | ❌ 不可用 |
