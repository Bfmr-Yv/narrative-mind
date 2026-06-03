# 项目简报：Narrative Mind v3.1

## 一句话定位
本地优先的 AI 增强型叙事操作系统（Narrative OS），不是 AI 作家，是作者的**思维外骨骼**。

## 项目起源
《龙族》《剑来》《玄鉴仙族》《雪中悍刀行》等顶级网络小说的创作，不是"灵感驱动"的随机过程，而是**"世界观-人物-主题"三轴同步推进的精密工程**。如果要用 AI 辅助这类创作，必须构建一个**理解小说运行规律的系统**，而非简单的文本生成器。

## 五大核心原则（不可动摇）

| 原则 | 含义 | 工程体现 |
|------|------|---------|
| **语料优先于理论** | 所有抽象概念必须有真实文本锚点 | 角色性格不是标签，是语料库中统计出的行为模式；Prompt 中的 few-shot 必须来自真实切片 |
| **成本优先于完美** | 每次 AI 调用必须有预算和降级路径 | Tier 0-4 分级定价；超量自动降级；本地 7B 模型处理 70% 常规任务 |
| **版本优先于覆盖** | 从第一行代码支持版本控制 | 章节级快照；修改传播检测；Git-like 分支（MVP 后实现） |
| **类型优先于通用** | 不做万能工具，先做修仙/玄幻极致 | GenreProfile 从语料统计生成，而非人工编写理论框架 |
| **人类优先于 AI** | 系统永远只给建议，不做决策 | 禁用自动修正正文；所有输出标记为 suggestion；提供确认/忽略/修改三选项 |

## 当前阶段
**Phase 1（地基）**：语料锚定 + 角色引擎 + 世界引擎 + 简化编排器 + 基础前端

目标：**8-12 周内做出能跑通的单章分析器**

## Phase 1 范围（再砍 50%）

| 模块 | 内容 | 排除项 |
|------|------|--------|
| **语料锚定** | 20 切片（红楼 10 + 自有 10）；本地 LanceDB 向量库；语义检索 | 公共域 100 切片；现代标杆语料 |
| **引擎** | **仅 2 个**：角色引擎 + 世界引擎 + 一致性守卫（设定+角色） | 叙事/文辞/主题/经济/读者预期/构思引擎 |
| **记忆** | 工作记忆（会话级）+ 情节记忆（近 10 章）；简化永久记忆 | 完整三层记忆；主动遗忘 |
| **前端** | 章节编辑器（沉浸/分析手动切换）；侧边栏建议卡片 | 大纲编辑器三级；可视化图谱；自动模式切换 |
| **级联修正** | 影响报告 + 待办清单 | 自动修正；分支；A/B 测试 |
| **版本控制** | 章节级快照 + 回滚 | Git-like 分支；合并 |
| **成本层** | 月度配额 + 超量停止 | 复杂 Dashboard；智能降级完整版 |
| **类型配置** | **仅"通用 Profile"** | 修仙 Profile；动态生成 |

## Phase 1 验证标准

> **输入**：用户上传 1 章 Markdown + 该角色历史 2-3 章  
> **输出**：JSON 报告（行为模式对比 + 设定一致性 + 建议）  
> **要求**：报告中的建议**确实有价值**（非废话），证明语料锚定闭环成立

## 完整引擎全景（Phase 1 仅激活 2 个）

| 引擎 | 中文名 | 职责 | Phase |
|------|--------|------|-------|
| **Character Engine** | 角色引擎 | PAD 情感 + 行为预测 | ✅ Phase 1 |
| **World Engine** | 世界引擎 | 设定规则校验 | ✅ Phase 1 |
| Narrative Engine | 叙事引擎 | 伏笔追踪、因果链管理 | Phase 2+ |
| Prose Engine | 文辞引擎 | 风格一致性、语域检测 | Phase 2+ |
| Theme Engine | 主题引擎 | 主题提取与一致性 | Phase 3+ |
| Economy Engine | 经济引擎 | 世界资源系统校验 | Phase 3+ |
| Reader Expectation Engine | 读者预期引擎 | 信息差管理、悬念校准 | Phase 3+ |
| Conception Engine | 构思引擎 | 意象体系管理 | Phase 3+ |

## 技术栈

- 前端：React + TypeScript
- 后端/引擎：Python 3.11
- 数据：SQLite（关系）+ LanceDB（向量，纯文件型）
- AI：MiMo API / DeepSeek（云端深度任务）+ Qwen2.5-7B 本地（常规任务/embedding）
- 提示词管理：YAML + Jinja2 + 版本控制
- 部署：纯桌面端，本地优先

## 项目规模评估

| 指标 | 数值 |
|------|------|
| 完整 v3.1 代码量 | 15 – 25 万行生产级代码 |
| MVP 代码量 | 3 – 5 万行（可独立产生价值） |
| 开发周期（1 人全职） | MVP：3-4 个月；完整版：2-3 年 |
| 运行成本（用户写百万字小说） | 纯云端 ¥100-300；本地混合 ¥30-80 |

## 文档索引

| 文档 | 用途 |
|------|------|
| `01-ARCHITECTURE.md` | 架构总图（全景 + Phase 1 裁剪版） |
| `02-CONTRACTS.md` | 模块接口契约 |
| `03-DECISIONS.md` | 架构决策记录 (ADR) |
| `04-COST-BUDGET.md` | 成本约束（Tier 0-4） |
| `05-MEMORY-SYSTEM.md` | 三层记忆系统设计 |
| `06-CONSISTENCY-GUARDIAN.md` | 八维一致性守卫 |
| `07-PROJECT-STRUCTURE.md` | 代码目录结构 |
| `08-MVP-ROADMAP.md` | Phase 1-4 路线图 |
| `09-RESUME-POSITIONING.md` | 简历定位建议 |
| `10-AGENT-CONSTRAINTS.md` | Agent 操作约束（自检规则） |
| `00-ACTIVE-CONTEXT.md` | 活跃上下文（当前焦点、阻塞项、待办队列） |
| `engines/*.md` | 各引擎详细设计卡片 |
| `prompts/*.md` | Prompt 版本管理 |
| `prompts/ngp-skills/orchestrator.md` | NGP 编排器 Skill |
| `prompts/ngp-skills/character-engine.md` | NGP 角色引擎 Skill |
| `prompts/ngp-skills/world-engine.md` | NGP 世界引擎 Skill |
| `sessions/*.md` | 对话日志 |
| `src/consistency_guardian/naming_phase_guard.py` | 命名+Phase 守卫 |
| `src/orchestrator/post_edit_validator.py` | 编辑后验证器 |
| `CLAUDE.md`（根目录） | 项目操作指南（工具配置） |
