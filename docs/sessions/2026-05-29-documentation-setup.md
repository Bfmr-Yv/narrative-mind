# 会话记录：2026-05-29

## 目标
建立项目文档体系，作为与 AI 对话的唯一真相源。

## 关键结论
1. 建立三层知识库：项目简报 → 接口契约 → 引擎卡片
2. 所有架构决策记录在 ADR 中，冻结后不再讨论
3. 每次与 AI 对话前，按"三步加载法"准备上下文
4. 成本约束 $20/月，超量降级

## 已创建的文档
- `00-PROJECT-BRIEF.md` - 项目定位
- `01-ARCHITECTURE.md` - 架构总图
- `02-CONTRACTS.md` - 模块接口契约
- `03-DECISIONS.md` - 架构决策记录（8 条 ADR）
- `04-COST-BUDGET.md` - 成本约束
- `engines/character-engine.md` - 角色引擎卡片
- `engines/world-engine.md` - 世界引擎卡片
- `engines/corpus-anchor.md` - 语料锚定层卡片
- `engines/impact-radar.md` - 影响雷达卡片
- `engines/orchestrator.md` - 编排器卡片
- `prompts/README.md` - Prompt 版本管理

## 已冻结的决策
- ADR-001: PAD 情感模型
- ADR-003: 禁用自动修正
- ADR-004: LanceDB 向量数据库
- ADR-006: 事件驱动架构
- ADR-007: Phase 1 范围裁剪
- ADR-008: 人类决策优先

## 待办事项
- [ ] 填充各引擎的 Prompt v1
- [ ] 确定修仙力量体系的境界划分
- [ ] 确定语料切片格式和向量维度
- [ ] 创建 Phase 1 的 MVP 路线图
- [ ] 开始语料库建设（红楼梦 10 场景 + 自有 10 场景）

## 下次对话的上下文包

```
【项目定位】
Narrative Mind v3，Phase 1 开发中。本地优先的多 Agent 叙事一致性系统。
约束：语料优先、成本 $20/月、先做修仙、人类决策优先。

【当前任务】
（根据具体任务填写）

【相关文档片段】
（从对应引擎卡片粘贴）

【相关契约】
（从 02-CONTRACTS.md 粘贴对应接口）
```
