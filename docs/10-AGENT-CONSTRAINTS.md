# Agent 操作约束 v1

> **版本**：v1 | **日期**：2026-06-02 | **状态**：已冻结

---

## 1. 重复预防（硬规则）

- 生成或修改任何 `.md` 文件前，先运行 `uniq -d` 检查连续重复行
- 若用户提供的是 diff 格式（含 `+`/`-` 行号），必须先提取纯净文本再写入，禁止把 diff 上下文当作新内容追加
- 发现重复时停止写入，要求用户确认后再覆盖

## 2. 命名冻结检查

- 引擎英文名以 `02-CONTRACTS.md` 为唯一真相源
- 禁止出现的废弃名称：
  - ~~Style Engine~~ → **Prose Engine**（文辞引擎）
  - ~~Impact Radar~~ → **Cascade Fixer**（级联修正器）
- 新增引擎必须经过 ADR 流程（见 `03-DECISIONS.md`），不得擅自添加

### 当前冻结命名表

| 中文名 | 英文名 | 文档出处 |
|--------|--------|---------|
| 角色引擎 | Character Engine | `02-CONTRACTS.md` |
| 世界引擎 | World Engine | `02-CONTRACTS.md` |
| 语料锚定层 | Corpus Anchor | `02-CONTRACTS.md` |
| 级联修正器 | Cascade Fixer | `02-CONTRACTS.md` |
| 编排器 | Orchestrator | `02-CONTRACTS.md` |
| 叙事引擎 | Narrative Engine | `02-CONTRACTS.md` `[Phase 2+]` |
| 文辞引擎 | Prose Engine | `02-CONTRACTS.md` `[Phase 2+]` |
| 主题引擎 | Theme Engine | `02-CONTRACTS.md` `[Phase 3+]` |
| 经济引擎 | Economy Engine | `02-CONTRACTS.md` `[Phase 3+]` |
| 读者预期引擎 | Reader Expectation Engine | `02-CONTRACTS.md` `[Phase 3+]` |
| 构思引擎 | Conception Engine | `02-CONTRACTS.md` `[Phase 3+]` |

## 3. Phase 边界守卫

- Phase 1 活跃文件（`00`–`09`、`engines/character-engine.md`、`engines/world-engine.md`）不得引入 Phase 2+ 引擎的依赖或接口引用
- Prompt 示例若使用类型专用内容（如修仙、奇幻），必须加声明：
  > 以下为类型占位示例，实际使用时替换为你的设定库。
- 成本数字改动必须同步更新 `04-COST-BUDGET.md`（Tier 表 + 单次调用成本表）

## 4. 版本一致性

- 修改任何文件时，同步检查 `prompts/README.md` 中的版本列表是否需要更新
- 日期格式统一：`YYYY-MM-DD`
- 变更日志必须记录原因，旧版本保留不删除
- 文档交叉引用使用相对路径（如 `02-CONTRACTS.md`），不含 `docs/` 前缀

## 5. 自检清单（写入前强制执行）

- [ ] `uniq -d` 无输出（连续重复行检测）
- [ ] 命名与 `02-CONTRACTS.md` 对齐（废弃名检查）
- [ ] Phase 标记正确（Phase 1 不引用 Phase 2+ 接口）
- [ ] 成本数字自洽（与 `04-COST-BUDGET.md` 交叉核对）

---

## 变更日志
- v1 (2026-06-02): 初始版本。建立 Agent 操作的五大约束规则和写入前自检清单。
