# 项目状态 — 2026-06-10

> **双 Claude 协作模式**：协作者负责 Phase 2 新模块，实践者负责 Phase 1 完善和修 Bug。各司其职，不交叉。

---

## 角色定义（明天启动时先确认身份）

### 🛠️ 实践者 — Phase 1 完善

实践者负责：
- 修复现有功能的 Bug
- 前端/后端管道优化
- API 服务器、场景分析、角色/地点管理
- 提交以 `fix:` / `refactor:` / `feat: `（Phase 1 范围内）开头

### 🧠 协作者 — Phase 2 推进

协作者负责：
- Phase 2 新引擎开发（叙事/文辞引擎等）
- 守卫扩展、记忆系统升级
- GitHub 开源维护、文档
- 提交以 `feat: Phase 2` 开头

---

## 启动方式

```cmd
cd C:\Users\userf\Desktop\xmgl_xs
.venv\Scripts\python src\api_server.py
```

浏览器打开 `http://127.0.0.1:5000`

## GitHub 推送

```cmd
set HTTPS_PROXY=http://127.0.0.1:10808
git push
```
仓库: https://github.com/Bfmr-Yv/narrative-mind

---

## 项目当前状态

### 已实现（Phase 1 M6 完成）

- 一键分析：粘贴章节 → LLM 分析 → 右侧面板展示
- 事件推演、角色/地点自动识别+创建、PAD 情感状态（每角色独立）、世界规则校验、冲突报告
- 分析历史持久化 + 对比模式
- 语料扩充 + 静态反哺自动运行

### 验证命令

```cmd
.venv\Scripts\python scripts\test_scene_analysis.py
```
期望: `[PASS] 所有维度数据正常！`

### LLM 配置

| 项目 | 值 |
|------|-----|
| Provider | 小米 MiMo TokenPlan |
| Model | mimo-v2.5-pro |
| API Key | `config/llm.json`（gitignored） |
| 月度预算 | $20（三层熔断 50%/80%/95%） |

### 后端关键模块

| 文件 | 职责 | 归属 |
|------|------|------|
| `src/api_server.py` | Flask API | 实践者 |
| `src/orchestrator/router.py` | 编排器（引擎调度 + 守卫）| 共享⚠️ |
| `src/engines/character.py` | 角色引擎（PAD + 行为预测）| 实践者 |
| `src/engines/world.py` | 世界引擎（规则 + 空间）| 实践者 |
| `src/engines/narrative.py` | **叙事引擎（Phase 2 新增）** | 协作者 |
| `src/llm/prompts.py` | LLM Prompt 模板 | 共享⚠️ |
| `src/llm/config.py` | LLM 配置 + Tier 路由 | 共享⚠️ |
| `src/llm/client.py` | LLM 客户端 | 共享⚠️ |
| `src/corpus_anchor/` | 语料检索 + 扩充 + 反哺 | 实践者 |
| `src/frontend/` | React 前端 | 实践者 |

> ⚠️ 共享文件修改前先 `git pull`，提交前确认不覆盖对方改动

---

---

## 🛠️ 实践者任务队列

### 已知 Bug 修复（已完成，供参考）

1. ~~`api_server.py` 缺少 `from __future__ import annotations`~~ ✅
2. ~~角色选择器数据源单一~~ ✅
3. ~~PAD 不随角色切换更新~~ ✅
4. ~~LLM 调用参数名错误~~ ✅

### Phase 1 待完善

- [ ] 前端 UX 打磨（分析 loading 状态、错误提示优化）
- [ ] 章节编辑器的自动保存体验
- [ ] 集成测试覆盖：端到端输入文本 → 查看分析结果的全流程
- [ ] `scripts/test_scene_analysis.py` 作为 CI 冒烟测试
- [ ] 成本追踪 Dashboard 在前端的展示

### 实践者提交规范

```
fix: 简短描述
feat: Phase 1 简短描述
refactor: 简短描述
```

---

---

## 🧠 协作者任务队列

### 已完成（Phase 2 启动）

- [x] **开源发布**：GitHub 仓库创建、MIT 许可、README 中英双语、AI Agent 声明
- [x] **安全清理**：API key gitignored、版权语料移除、Claude 配置文件移除
- [x] **叙事引擎** (`src/engines/narrative.py`) — 伏笔检测 + 因果链 + 跨章节回收 + 情节推演
- [x] **LLM 扩展**：4 个新 System Prompt + 4 个任务类型 + 成本估算
- [x] **编排器集成**：`narrative` / `full_analyze` 路由 + 守卫维度扩展
- [x] **测试**：`scripts/test_narrative_engine.py`（6 项全部通过）
- [x] **文档**：ADR-016 + 契约更新

### 叙事引擎测试

```cmd
.venv\Scripts\python scripts\test_narrative_engine.py
```
期望: `[ALL PASS] Narrative Engine test suite complete!`

### Phase 2 待推进（优先级排序）

| # | 模块 | 新建文件 | 说明 |
|---|------|---------|------|
| 1 | **文辞引擎** | `src/engines/prose.py` | 对话风格一致性和角色用语检测 |
| 2 | **守卫 8 维扩展** | 扩展 `guardian.py` | 从 3 维→8 维（时间/力量/关系/因果/风格/叙事） |
| 3 | **三层永久记忆** | 扩展 `src/memory/` | 冷热分层 + SQLite 持久化 + 自动归档 |
| 4 | **GitHub 社区完善** | README/ISSUE_TEMPLATE | 完善开源项目首页、Issue 模板 |

### 协作者提交规范

```
feat: Phase 2 — 简短描述
docs: 简短描述
chore: 简短描述
```

---

---

## 协作规则（重要！）

1. **启动时**：用户会指明你是实践者还是协作者。读本文件对应角色段落。
2. **独立工作**：各改各的文件，不交叉修改。
3. **共享文件**（`prompts.py`、`config.py`、`router.py`）：修改前拉取最新，追加不覆盖。
4. **提交频率**：每完成一个独立功能就提交，减少冲突。
5. **推送**：需要先设代理 `HTTPS_PROXY=http://127.0.0.1:10808`

## 当前待提交

- `SITUATION-2026-06-10.md`（本文件）

建议明天先用 `git status` 确认工作区干净后再开始。
