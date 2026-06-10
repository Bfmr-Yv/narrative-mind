# 贡献指南

感谢你对 Narrative Mind 的关注！

## 当前阶段

项目处于 **Phase 1（地基）** 阶段，核心架构仍在快速迭代中。在提交 PR 之前，建议先开 Issue 讨论你的想法。

## 开发流程

### 1. 了解项目

- 阅读 [CLAUDE.md](CLAUDE.md) — 项目操作规范和命名约束
- 阅读 [docs/01-ARCHITECTURE.md](docs/01-ARCHITECTURE.md) — 系统架构
- 阅读 [docs/02-CONTRACTS.md](docs/02-CONTRACTS.md) — 接口契约

### 2. 设置开发环境

```bash
git clone https://github.com/YOUR_USERNAME/xmgl_xs.git
cd xmgl_xs
pip install -r requirements.txt
cp config/llm.example.json config/llm.json
# 编辑 config/llm.json 填入 API Key
```

### 3. 代码规范

- 核心引擎仅使用 **Python 标准库**（`src/engines/`, `src/corpus_anchor/`, `src/memory/`, `src/consistency_guardian/`）
- LLM 集成层允许 `openai` SDK（`src/llm/`）
- 遵循项目命名冻结表（见 CLAUDE.md）
- 提交前运行 `scripts/test_integration.py`

### 4. 提交规范

- 提交信息格式：`模块名: 简短描述`
  - 例如：`character-engine: fix PAD emotion boundary check`
- 重大变更需要在 `docs/03-DECISIONS.md` 记录

## 五大硬边界

贡献代码时必须遵守以下约束：

1. **语料边界** — Phase 1 语料规模 20 片，切片标准 500 字/场景
2. **成本边界** — 月度 LLM 成本上限 $20，三层熔断
3. **版本边界** — 文档版本以 `docs/` 为准，代码版本以 `src/` 为准
4. **类型边界** — Phase 1 仅支持通用 Profile
5. **人类优先** — AI 只生成建议，不自动修改

## 版权与语料

- **禁止**提交受版权保护的文本内容作为语料
- 语料切片仅使用公版作品（已进入公有领域）或你自己拥有完整权利的内容
- 如果你不确定某段文本是否可以公开，请不要提交

## 许可证

你贡献的代码将采用与项目相同的 [MIT License](LICENSE)。
