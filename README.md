# Narrative Mind v3.1

> **本地优先的 AI 增强型叙事操作系统** — 不是 AI 作家，是作者的**思维外骨骼**。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Phase: 1](https://img.shields.io/badge/Phase-1%20M6-orange)](docs/08-MVP-ROADMAP.md)
[![Python: 3.11](https://img.shields.io/badge/Python-3.11-green)]()
[![AI Agent Built](https://img.shields.io/badge/AI%20Agent-Built-8A2BE2)]()

> 🧠 **本项目使用 AI Agent 工具辅助开发**（Claude Code、Cursor 等）。AI 参与了架构设计讨论、代码生成、文档撰写和测试编写，但所有 AI 输出均经过人类 review 和决策。

Narrative Mind 是一个 AI 辅助长篇小说创作系统，基于**语料锚定**和**多引擎协作**架构。它从作者的已有文本中提取角色行为模式、世界规则和叙事逻辑，在写作过程中提供一致性检查和创作建议。

## 核心设计理念

| 原则 | 含义 |
|------|------|
| **语料优先于理论** | 所有抽象概念必须有真实文本锚点 — 角色性格来自语料统计，不是标签 |
| **成本优先于完美** | 每次 AI 调用有预算和降级路径，Tier 0-4 分级定价 |
| **版本优先于覆盖** | 从第一行代码支持版本控制，章节级快照 |
| **人类优先于 AI** | 系统永远只给建议，不做决策，不自动修正正文 |

## 架构概览

```
xmgl_xs/
├── src/
│   ├── engines/           # 角色引擎 + 世界引擎
│   ├── corpus_anchor/     # 语料锚定层（切片管理、向量检索）
│   ├── consistency_guardian/  # 一致性守卫（八维校验）
│   ├── orchestrator/      # 编排器（多引擎调度）
│   ├── memory/            # 记忆系统（工作/情节/永久记忆）
│   ├── llm/               # LLM 集成层（OpenAI 兼容 SDK）
│   ├── frontend/          # React 前端（章节编辑器 + 建议卡片）
│   └── api_server.py      # Flask API 服务器
├── corpus/                # 语料库（公版 + 用户语料）
├── docs/                  # 设计文档（真相源）
├── config/                # 配置文件
├── prompts/               # Prompt 模板 + NGP Skills
└── projects/              # 用户项目数据
```

## 引擎全景

| 引擎 | 中文名 | 职责 | 状态 |
|------|--------|------|------|
| Character Engine | 角色引擎 | PAD 情感 + 行为预测 | ✅ Phase 1 |
| World Engine | 世界引擎 | 设定规则校验 | ✅ Phase 1 |
| Narrative Engine | 叙事引擎 | 伏笔追踪、因果链 | Phase 2+ |
| Prose Engine | 文辞引擎 | 风格一致性 | Phase 2+ |
| Theme Engine | 主题引擎 | 主题提取与一致性 | Phase 3+ |

→ [完整架构文档](docs/01-ARCHITECTURE.md)

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（前端）
- LLM API Key（支持 OpenAI 兼容接口）

### 安装

```bash
# 克隆仓库
git clone https://github.com/Bfmr-Yv/narrative-mind.git
cd xmgl_xs

# 安装 Python 依赖
pip install -r requirements.txt

# 配置 LLM API
cp config/llm.example.json config/llm.json
# 编辑 config/llm.json 填入你的 API Key

# 安装前端依赖
cd src/frontend
npm install
```

### 运行

```bash
# 启动 API 服务器
python launcher.py

# 或直接启动 Flask
python src/api_server.py
```

### 运行测试

```bash
python scripts/test_corpus_anchor.py
python scripts/test_character_engine.py
python scripts/test_world_engine.py
python scripts/test_integration.py
```

## 技术栈

- **后端/引擎**: Python 3.11（核心引擎仅使用标准库）
- **前端**: React + TypeScript
- **LLM**: OpenAI 兼容 API（MiMo / DeepSeek / Qwen 等）
- **向量检索**: 纯 Python 实现（TF-IDF + 余弦相似度）
- **数据**: JSON 文件存储

## 当前阶段

**Phase 1（地基）** — 语料锚定 + 角色引擎 + 世界引擎 + 基础编排器

目标：单章分析器 — 输入一章文本，输出角色行为模式对比 + 设定一致性报告

→ [路线图详情](docs/08-MVP-ROADMAP.md)

## 文档

| 文档 | 用途 |
|------|------|
| [项目简报](docs/00-PROJECT-BRIEF.md) | 定位与愿景 |
| [架构设计](docs/01-ARCHITECTURE.md) | 系统架构 |
| [接口契约](docs/02-CONTRACTS.md) | 模块接口 |
| [决策记录](docs/03-DECISIONS.md) | ADR 架构决策 |
| [成本预算](docs/04-COST-BUDGET.md) | Tier 0-4 |
| [路线图](docs/08-MVP-ROADMAP.md) | Phase 1-4 |

## 贡献

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

⚠️ **版权提醒**：本项目语料仅包含公版作品（如《红楼梦》节选）。请勿提交受版权保护的文本内容。

## 许可证

MIT License © 2026 Narrative Mind Contributors — 详见 [LICENSE](LICENSE)
