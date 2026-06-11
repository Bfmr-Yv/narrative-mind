# Narrative Mind v3.1

> ⚠️ **早期原型阶段 — 目前尚不可用于实际写作。** 这个项目是一个 AI 辅助小说创作系统的实验性原型，正在从概念验证向最小可用版本迭代。欢迎围观和讨论想法，但请勿用于生产环境。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Prototype](https://img.shields.io/badge/Status-Early%20Prototype-red)](docs/08-MVP-ROADMAP.md)
[![Python: 3.11](https://img.shields.io/badge/Python-3.11-green)]()
[![AI Agent Built](https://img.shields.io/badge/AI%20Agent-Built-8A2BE2)]()

> 🧠 **本项目使用 AI Agent 工具辅助开发**（Claude Code 等）。几乎所有代码、文档和测试均由 AI 在人类指导下生成。

## 这是什么？

Narrative Mind 是一个**实验性的** AI 辅助长篇小说创作系统，基于*语料锚定*和*多引擎协作*架构。它的想法是：从作者的已有文本中提取角色行为模式、世界规则和叙事逻辑，在写作过程中提供一致性检查和创作建议。

**但说实话**：它目前只是能跑通流程的原型。后端引擎可以处理文本并输出分析结果，前端能展示，但分析质量、可用性和稳定性都远未达到实际使用的水平。把它当成一个有趣的技术实验来看就好。

## 核心设计理念

这些是我们在探索的方向，能不能做到还是另一回事：

| 原则 | 含义 |
|------|------|
| **语料优先于理论** | 所有抽象概念应该有真实文本锚点 |
| **成本优先于完美** | 每次 AI 调用有预算和降级路径 |
| **版本优先于覆盖** | 从第一行代码考虑版本控制 |
| **人类优先于 AI** | 系统只给建议，不做决策，不自动修正正文 |

## 架构概览

```
xmgl_xs/
├── src/
│   ├── engines/           # 角色引擎 + 世界引擎 + 叙事引擎 + 文辞引擎
│   ├── corpus_anchor/     # 语料锚定层（切片管理、向量检索）
│   ├── consistency_guardian/  # 一致性守卫
│   ├── orchestrator/      # 编排器（多引擎调度）
│   ├── memory/            # 记忆系统（工作/情节/永久）
│   ├── llm/               # LLM 集成层
│   ├── frontend/          # React 前端
│   └── api_server.py      # Flask API 服务器
├── corpus/                # 语料库（公版作品 + 用户语料）
├── docs/                  # 设计文档
└── scripts/               # 测试和工具脚本
```

## 引擎现状

> ⚠️ 所有引擎目前都属于「能跑通但分析质量待验证」的状态。

| 引擎 | 中文名 | 计划做的事 | 当前状态 |
|------|--------|-----------|---------|
| Character Engine | 角色引擎 | PAD 情感追踪 + 行为预测 | 🧪 原型可用，LLM 分析结果仅供参考 |
| World Engine | 世界引擎 | 设定规则校验 + 空间一致性 | 🧪 原型可用 |
| Narrative Engine | 叙事引擎 | 伏笔追踪 + 因果链 | 🧪 Phase 2 原型 |
| Prose Engine | 文辞引擎 | 风格一致性检测 | 🧪 Phase 2 原型 |
| Theme Engine | 主题引擎 | 主题提取与演变 | 📋 仅设计文档 |

→ [完整架构文档（也是半成品）](docs/01-ARCHITECTURE.md)

## 试一下（仅供开发者和好奇者）

### 前提

- Python 3.11+
- Node.js 18+（前端）
- LLM API Key（支持 OpenAI 兼容接口，如 MiMo/DeepSeek 等）

### 跑起来看看

```bash
git clone https://github.com/Bfmr-Yv/narrative-mind.git
cd xmgl_xs

# Python 依赖
pip install -r requirements.txt

# LLM API 配置
cp config/llm.example.json config/llm.json
# 编辑 config/llm.json 填入你的 API Key

# 前端（可选，也可以用后端直接跑）
cd src/frontend && npm install && cd ../..

# 启动
python scripts/launcher.py
# 浏览器打开 http://127.0.0.1:5000
```

### 跑测试

```bash
python scripts/test_scene_analysis.py
python scripts/test_narrative_engine.py
python scripts/test_prose_engine.py
python scripts/test_memory_system.py
```

## 当前局限

- **分析质量**：LLM 输出的准确性和一致性未经系统验证，很多时候是"看起来合理但实际没用"
- **性能**：无任何优化，单次分析依赖 LLM API 延迟（2-5 秒），无缓存
- **前端**：功能极简，UI 未经设计，错误处理不完善
- **文档**：设计文档写了很多，但和实际代码有偏差（文档是理想，代码是现实）
- **测试覆盖**：仅有冒烟测试，无单元测试覆盖
- **数据持久化**：分析历史会保存，但数据格式随时可能变化

## 技术栈

- **后端/引擎**: Python 3.11（核心引擎仅使用标准库）
- **前端**: React + TypeScript
- **LLM**: OpenAI 兼容 API
- **向量检索**: 纯 Python 实现（TF-IDF + 余弦相似度）
- **存储**: JSON 文件 + SQLite

## 路线图

实际上我们也不知道能不能走到 Phase 2，但方向大致是：

- **Phase 1（当前）**：跑通单章分析流程 — ✅ 基本完成
- **Phase 2（进行中）**：叙事引擎 + 文辞引擎 + 三层记忆 — 🚧 原型就绪
- **Phase 3+**：主题/经济/读者预期引擎，完整可视化 — 📋 远景

→ [路线图详情](docs/08-MVP-ROADMAP.md)

## 贡献

欢迎任何形式的参与——提 Issue 讨论想法、指出设计问题、或者只是围观。

但在投入时间之前，请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解当前阶段和局限。

⚠️ **版权提醒**：本项目语料仅包含公版作品（如《红楼梦》节选）。请勿提交受版权保护的文本内容。

## 许可证

MIT License © 2026 Narrative Mind Contributors — [LICENSE](LICENSE)
