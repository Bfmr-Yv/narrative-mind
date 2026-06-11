# 贡献指南

感谢你对 Narrative Mind 的关注！

## 请先了解实际情况

这个项目目前是**个人业余实验**，离"可用"还有很远。所有引擎的分析质量、前端体验、文档完整性都处于原型阶段。

在考虑贡献之前，请接受以下事实：
- **这不是一个成熟的开源项目**，它更像一个公开的技术实验
- 代码和文档会被频繁大幅修改，不保证向后兼容
- 维护者（就是一个人）的响应时间以"天"甚至"周"计
- 很多 Issue 可能被标记为"远景"然后很久无人处理

如果你看完以上还感兴趣，非常欢迎！提 Issue 讨论想法是最好的开始方式。

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

## 附录：详细编码规范

> 以下内容原为独立的 `CODING-STANDARDS.md`，2026-06-11 精简目录时合并入此文件。

### 语言与环境

- **Python 版本**: 3.11+
- **类型注解**: 必须使用（`from __future__ import annotations`）
- **编码**: UTF-8

### 依赖限制

**核心引擎禁止引入任何外部依赖**，仅使用 Python 标准库。

**例外**：API 服务器（`src/api_server.py`）允许使用 Flask 和 Flask-CORS。LLM 集成层（`src/llm/`）允许使用 `openai` SDK。

### 代码风格

- 缩进：4 空格，行宽 88 字符
- 变量/函数：`snake_case`，类：`PascalCase`，常量：`UPPER_SNAKE_CASE`
- 文档字符串：Google 风格（Args / Returns / Raises）
- 数据模型使用 `@dataclass`
- 不捕获裸异常（`except Exception`）

### 导入顺序

```python
# 1. 标准库
import json
from pathlib import Path

# 2. 项目内模块
from src.llm.config import get_config

# 3. 当前包内
from .retriever import Retriever
```

### 测试

- 测试脚本位于 `scripts/`（如 `scripts/test_integration.py`）
- 测试函数命名：`test_<what>_<expected>`

### 提交格式

```
<type>(<scope>): <description>
```

类型：`feat` / `fix` / `docs` / `refactor` / `test` / `chore`
重大变更需在 `docs/03-DECISIONS.md` 记录。

### 语料切片质量

- 每片 450-800 字（场景级完整性优先于字数限制）
- 仅使用公版作品或自有版权内容
- 切片格式见 `docs/02-CONTRACTS.md`
