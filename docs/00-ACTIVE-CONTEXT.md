# 活跃上下文

> **最后更新**: 2026-06-09  
> **状态**: Phase 1 M6 完成 — LLM 集成 + 语料自扩充回路

## 当前焦点

**Phase 1 M6 完成**：LLM 集成完毕，MiMo v2.5-pro API 接入，语料自扩充回路运转，前端自动保存已修复，EXE 打包配置更新。

## 阻塞项

无

## 已完成项

1. ~~`src/` 目录骨架搭建~~ ✅ 完成（2026-06-03）
2. ~~创建 `CODING-STANDARDS.md`~~ ✅ 完成（2026-06-08）
3. ~~运行 NGP 守卫脚本测试~~ ✅ 通过（2026-06-03）
4. ~~创建 `src/corpus_anchor/` 代码框架~~ ✅ 完成（2026-06-08）
5. ~~准备语料切片~~ ✅ 完成（20 切片，人工审核）
6. ~~放宽切片长度标准~~ ✅ 完成（450-800 字）
7. ~~实现语料检索功能~~ ✅ 完成（TF-IDF + 余弦相似度）
8. ~~实现角色引擎核心功能~~ ✅ 完成（LLM PAD 分析 + 行为预测）
9. ~~实现世界引擎核心功能~~ ✅ 完成（LLM 规则校验 + 空间一致性）
10. ~~实现一致性守卫~~ ✅ 完成（3 维检查 + 警报）
11. ~~实现编排器~~ ✅ 完成（事件路由 + 引擎调度）
12. ~~实现记忆系统~~ ✅ 完成（工作记忆 + 读写接口）
13. ~~端到端集成测试~~ ✅ 通过
14. ~~创建前端项目结构~~ ✅ 完成（React + TypeScript）
15. ~~实现章节编辑器~~ ✅ 完成
16. ~~实现侧边栏建议卡片~~ ✅ 完成
17. ~~实现成本追踪~~ ✅ 完成
18. ~~创建 API 服务器~~ ✅ 完成（Flask）
19. **M6: LLM 集成 + 语料自扩充回路** ✅ 完成（2026-06-09）
20. **EXE 打包配置更新** ✅ 完成（2026-06-09）

## 待办队列

1. **静态语料标注优化回路**（Refiner）：LLM 分析结果反哺静态切片元数据
2. **角色/地点自动提取**：从分析结果中提取建议的角色和地点
3. **前端分析结果多次对比**：支持同一章节多次分析并对比结果
4. **前端历史记录持久化**：分析历史不因刷新丢失

## 最后操作

- **2026-06-09**: M6 LLM 集成完成（MiMo v2.5-pro API）
- **2026-06-09**: 语料自扩充回路实现（Enricher + 动态索引）
- **2026-06-09**: EXE 打包配置更新（包含 LLM 模块 + openai SDK）
- **2026-06-09**: 前端自动保存修复 + 文本截断修复（500→4000 字）
- **2026-06-08**: 前端组件创建完成（ChapterEditor, SuggestionPanel, CostTracker）

## 会话历史

- **2026-06-02**: 文档闭环（27 文件冻结）
- **2026-06-03**: NGP 搭建完成（Step 1-3）
- **2026-06-03**: src/ 目录骨架搭建完成
- **2026-06-08**: M2 语料冷启动完成
- **2026-06-08**: M3 引擎核心完成（角色+世界+语料检索）
- **2026-06-08**: M4 编排+守卫完成
- **2026-06-08**: M5 前端组件和 API 服务器创建完成
- **2026-06-09**: M6 LLM 集成 + 语料自扩充回路完成

## 活跃模块

| 模块 | 状态 | 文件 |
|------|------|------|
| LLM 集成层 | ✅ M6 完成 | `src/llm/` |
| 角色引擎 | ✅ LLM 升级完成 | `src/engines/character.py` |
| 世界引擎 | ✅ LLM 升级完成 | `src/engines/world.py` |
| 语料锚定层 | ✅ 检索 + 扩充完成 | `src/corpus_anchor/` |
| 语料自扩充器 | ✅ M6 新增 | `src/corpus_anchor/enricher.py` |
| 一致性守卫 | ✅ 实现完成 | `src/consistency_guardian/guardian.py` |
| 编排器 | ✅ 扩充回路集成 | `src/orchestrator/router.py` |
| 记忆系统 | ✅ 实现完成 | `src/memory/working_memory.py` |
| API 服务器 | ✅ LLM 集成完成 | `src/api_server.py` |
| 前端 | ✅ 自动保存修复 | `src/frontend/` |
| EXE 打包 | ✅ M6 配置更新 | `NarrativeMind.spec` |

## LLM 配置

| 项目 | 值 |
|------|-----|
| Provider | 小米 MiMo TokenPlan |
| Model | mimo-v2.5-pro |
| API Endpoint | https://token-plan-cn.xiaomimimo.com/v1 |
| 配置文件 | `config/llm.json`（gitignored） |
| 月度预算 | $20（三层熔断：50%/80%/95%） |

## NGP Skills

| Skill | 文件 | 状态 |
|-------|------|------|
| 编排器 | `prompts/ngp-skills/orchestrator.md` | ✅ 已创建 |
| 角色引擎 | `prompts/ngp-skills/character-engine.md` | ✅ 已创建 |
| 世界引擎 | `prompts/ngp-skills/world-engine.md` | ✅ 已创建 |

## 冻结决策

- ADR-001: PAD 情感模型
- ADR-003: 禁用自动修正
- ADR-007: Phase 1 范围裁剪
- ADR-008: 人类决策优先
- ADR-009: Tier 0-4 分级定价
- ADR-011: Phase 1 仅激活 2 引擎
- ADR-012: 本地 7B 处理 70% 任务（**已修订**：实际使用 MiMo 云 API 替代本地模型）
- ADR-015: MiMo API 替代本地模型 + 成本追踪（新增）

## 命名冻结

| 中文名 | 英文名 | 状态 |
|--------|--------|------|
| 角色引擎 | Character Engine | ✅ Phase 1 |
| 世界引擎 | World Engine | ✅ Phase 1 |
| 语料锚定层 | Corpus Anchor | ✅ Phase 1 |
| 语料自扩充器 | Enricher | ✅ Phase 1 M6 |
| 级联修正器 | Cascade Fixer | ✅ Phase 1 |
| 编排器 | Orchestrator | ✅ Phase 1 |
| 叙事引擎 | Narrative Engine | Phase 2+ |
| 文辞引擎 | Prose Engine | Phase 2+ |
| 主题引擎 | Theme Engine | Phase 3+ |
| 经济引擎 | Economy Engine | Phase 3+ |
| 读者预期引擎 | Reader Expectation Engine | Phase 3+ |
| 构思引擎 | Conception Engine | Phase 3+ |

## Phase 1 排除项

- ❌ 叙事/文辞/主题/经济/读者预期/构思引擎
- ❌ 永久记忆
- ❌ 级联修正器的因果推理
- ❌ 意图标记系统
- ❌ 章节级快照
- ❌ 复杂 Dashboard
- ❌ 本地 Qwen2.5-7B 部署（改为 MiMo 云 API）

## 成本约束

- **实际使用**: MiMo TokenPlan（API key: `tp-cpj9...`）
- **月度上限**: $20（硬性熔断）
- **禁止改动**: `04-COST-BUDGET.md`
