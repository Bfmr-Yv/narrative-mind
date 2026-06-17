# Narrative Mind v4.0 — 长期开发路线图

> **性质**: 参考文档，不用于执行
> **创建**: 2026-06-16
> **阶段**: 12 周 / 7 阶段

---

## 项目当前状态

**Phase A — 脚手架 ✅ 完成（2026-06-17）**

| 组件 | 实际状态 | 完成度 |
|------|---------|--------|
| Cargo workspace | 7 crates，workspace 依赖完整，cargo check 通过 | ✅ 100% |
| `xmgl-core` | 核心类型全部定义（AgentId/PADState/TaskType 等）+ 3 tests | ✅ 100% |
| `xmgl-agent` | 文档注释就位 + 1 test | ✅ 100%（支架） |
| `xmgl-orchestrator` | 文档注释就位 + 1 test | ✅ 100%（支架） |
| `xmgl-memory` | 文档注释就位 + 1 test | ✅ 100%（支架） |
| `xmgl-project` | 文档注释就位 + 1 test | ✅ 100%（支架） |
| `xmgl-python-bridge` | 文档注释就位 + 1 test | ✅ 100%（支架） |
| `xmgl-tauri` | 文档注释就位 + 1 test | ✅ 100%（支架） |
| `main.rs` | Tauri v2 Builder 入口，窗口弹出通过 | ✅ 100% |
| Python sidecar `main.py` | FastAPI 骨架完整（6 个端点），健康检查通过 | ✅ 100%（支架） |
| Python `llm/` | config.py + client.py stub 就位 | ✅ 100%（支架） |
| Python `prompts/` | registry.py + PROMPT_REGISTRY stub | ✅ 100%（支架） |
| Python `corpus/` | SliceManager/Retriever/Embedder stub | ✅ 100%（支架） |
| Frontend `App.tsx` | 占位 div，Tauri 窗口可渲染 | ✅ 100%（支架） |
| `tauri.conf.json` | 窗口 1400×900，devUrl/build 配置完整 | ✅ 100% |
| `capabilities/default.json` | Tauri v2 权限声明 | ✅ 100% |
| `docs/` | 4 份设计文档 | ✅ 100% |
| `corpus/` | 红楼梦 4 条样本切片 | 样本 |
| Claude Code 环境 | 双角色 + MCP + Skills + Hooks | ✅ 100% |

---

## Phase A: 脚手架（第 1-2 周）

**目标**: Rust ↔ Python 健康检查通过

- [x] Python sidecar 可启动（修复 llm/client.py, llm/config.py, prompts/registry.py, corpus/*.py 导入链）
- [x] `xmgl-core` Cargo.toml 补齐 serde 依赖
- [x] `cargo check` 全 workspace 通过
- [x] `GET /v1/llm/health` → `{"status": "ok"}`
- [x] Tauri 空壳可启动（创建 `tauri.conf.json`，集成到 `main.rs`）
- [x] 前端 Vite dev 可启动（localhost:1420）
- [x] `cargo tauri dev` 打开桌面窗口

**可验证产出**: Tauri 窗口中显示前端占位页，Python sidecar 健康检查通过

---

## Phase B: 数据层（第 2-3 周）

**目标**: 项目/章节 CRUD 通过 Tauri command 可用

- [ ] `xmgl-memory`: SQLite 初始化 + schema migration（projects/chapters/episodic_memory/causality_graph/foreshadowing_registry/pad_history/permanent_memory/analysis_history/cost_log/monthly_budget）
- [ ] `xmgl-project`: ProjectManager + 项目/章节 CRUD
- [ ] `xmgl-project`: 旧数据迁移模块（从 `../xmgl_xs/` 迁移 JSON 数据）
- [ ] `xmgl-tauri`: 首批 Tauri commands（list_projects, create_project, get_chapter, update_chapter）
- [ ] TypeScript 类型定义（镜像 Rust serde 类型）

**可验证产出**: Tauri command `list_projects` 返回迁移后的项目列表

---

## Phase C: Agent 基础（第 3-5 周）

**目标**: 2 个 Agent 通过 Python sidecar 调 LLM 产出结果

- [ ] `xmgl-agent`: Agent trait 定义
- [ ] `xmgl-agent`: AgentRegistry + SharedContext
- [ ] `xmgl-agent`: CharacterAgent 实现
- [ ] `xmgl-agent`: WorldAgent 实现
- [ ] `xmgl-python-bridge`: PythonBridge HTTP 客户端（调用 `/v1/llm/call`）
- [ ] `src-python/llm/client.py`: OpenAI SDK 封装（从旧 `xmgl_xs/src/llm/client.py` 移植）
- [ ] `src-python/llm/config.py`: LLM 配置（从旧 `xmgl_xs/src/llm/config.py` 移植）
- [ ] `src-python/prompts/registry.py`: Prompt 注册表（从旧 `src/llm/prompts.py` 移植两条：角色 + 世界）

**可验证产出**: CharacterAgent.form_position() 返回 PAD 分析结果

---

## Phase D: 编排器（第 5-7 周）

**目标**: 3+ Agent 并行 → 交叉审问 → 综合输出

- [ ] `xmgl-orchestrator`: ComplexityJudge（复杂度预判）
- [ ] `xmgl-orchestrator`: TopologySelector（拓扑选择：简单/中等/复杂）
- [ ] `xmgl-orchestrator`: RoundManager（轮次管理）
- [ ] `xmgl-orchestrator`: HCP-MAD 三级渐进升级引擎
- [ ] `xmgl-orchestrator`: Hermes Council 五阶段协议（Premortem→Position→Probe→Reflect→AssumptionMap）
- [ ] `xmgl-tauri`: analysis 相关 Tauri commands + SSE 事件流

**可验证产出**: 3 Agent 并行分析一段文本，交叉审问日志可见，产出合并建议

---

## Phase E: 前端集成（第 7-9 周）

**目标**: 编辑器黄点 → 展开建议 → 双击替换完整闭环

- [ ] Monaco 编辑器独立嵌入（移除 placeholder div）
- [ ] 装饰系统（黄点 gutter 标记 + 替换文字 inline decoration）
- [ ] 建议交互（点击展开/双击替换/右键退回/Ctrl+左键 Tips）
- [ ] Zustand store（分析触发/建议管理/Agent 讨论查看）
- [ ] RightPanel: Agent 讨论历史 + 建议列表
- [ ] LeftSidebar: 项目/章节导航
- [ ] Tauri 事件 → Zustand 自动 dispatch

**可验证产出**: 写 500 字后 Monaco 编辑器中出现黄点，点击展开建议，双击替换生效

---

## Phase F: 剩余 Agent（第 9-11 周）

**目标**: 全功能 9 Agent 协作

- [ ] 剩余 7 个 Agent 实现（叙事/文辞/主题/经济/预期/构思/总编）
- [ ] 17 个 System Prompt 全部从 v3.1 移植
- [ ] `src-python/corpus/`: SliceManager + Retriever + Embedder（从旧 corpus_anchor 移植）
- [ ] `/v1/corpus/search` 端点可用

**可验证产出**: FullScene 分析 → 全部 9 Agent 协作 → 黄点 + 建议 + 讨论历史完整

---

## Phase G: 打磨（第 11-12 周）

**目标**: 可分发安装包

- [ ] 被动模式（写够 500 字后台自动触发轻量检查）
- [ ] 快捷键系统
- [ ] 成本面板（CostDashboard）
- [ ] 全文测试覆盖
- [ ] PyInstaller 打包 Python sidecar
- [ ] Tauri 打包生成 .msi 安装包

**可验证产出**: 全新 Windows 机器安装运行通过

---

## 旧代码复用清单

| 旧文件 | 复用阶段 | 去向 |
|--------|---------|------|
| `src/llm/prompts.py` (749行) | Phase C | `src-python/prompts/` |
| `src/llm/client.py` (166行) | Phase C | `src-python/llm/client.py` |
| `src/llm/config.py` | Phase C | `src-python/llm/config.py` |
| `src/corpus_anchor/` (1527行) | Phase F | `src-python/corpus/` |
| `src/memory/` SQL schema | Phase B | `xmgl-memory/` |
| `src/engines/character.py` PAD | Phase C | `xmgl-agent/` (概念移植) |
| `src/frontend/src/types/` | Phase B | `src-frontend/src/types/` (参考) |
| `src/project_manager.py` | Phase B | `xmgl-project/` (概念移植) |

---

## 关键架构约束（贯穿所有阶段）

1. 只有 `xmgl-orchestrator` 有记忆写入权
2. 只有 `xmgl-python-bridge` 做 HTTP
3. `xmgl-core` 零外部依赖（仅 serde）
4. Agent 间通信通过 Orchestrator 的 SharedContext，不直接互相调用
5. 前端不直接调 LLM API，全部通过 Tauri IPC
6. 成本月上限 $20，三层熔断（50%/80%/95%）
