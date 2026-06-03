# Prompt 版本管理

> **v3.1 更新**：引擎列表从 4 个扩展到 8 个（Phase 1 仅编写角色引擎 + 世界引擎的 Prompt）。

## 规则
- 每个引擎的 Prompt 独立版本管理
- 修改 Prompt 必须记录变更原因
- 旧版本保留，不删除
- Few-shot 示例必须来自真实语料切片（非虚构），变更时同步更新来源标注

## 版本列表

| 引擎 | 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|------|
| 角色引擎 (Character) | v1 | 2026-06-02 | ✅ 已编写 | PAD 情感模型 + 语料锚定行为预测 |
| 世界引擎 (World) | v1 | 2026-06-02 | ✅ 已编写 | 规则引擎校验 + 三级结果 (pass/conflict/warning) |
| 级联修正器 (Cascade Fixer) | v1 | - | 待编写 | Phase 1 简化版：关键词扫描 |
| 叙事引擎 (Narrative) | v1 | - | Phase 2+ | - |
| 文辞引擎 (Prose) | v1 | - | Phase 2+ | - |
| 主题引擎 (Theme) | v1 | - | Phase 3+ | - |
| 经济引擎 (Economy) | v1 | - | Phase 3+ | - |
| 读者预期引擎 (Reader Expectation) | v1 | - | Phase 3+ | - |
| 构思引擎 (Conception) | v1 | - | Phase 3+ | - |

## Prompt 模板

```markdown
# [引擎名称] Prompt v[版本号]

## 系统指令
（角色定义、约束条件）

## 核心约束
（该引擎特有的约束列表）

## 输入格式
（JSON Schema，字段说明）

## 输出格式
（期望的输出结构，JSON Schema + 字段说明）

## 示例
（至少 2 个示例：1 个正常案例，1 个边界/冲突案例）
（示例中的 few-shot 必须标注真实语料来源）

## 变更日志
- v1 (YYYY-MM-DD): 初始版本
```
