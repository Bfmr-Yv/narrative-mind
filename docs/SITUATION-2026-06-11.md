# 项目状态 — 2026-06-11

> **双 Claude 协作模式**：协作者负责 Phase 2/3 新模块，实践者负责 Phase 1 完善 + 前端 + API 对接。
> **今日产出**：Phase 2 全部完成（4 引擎 + 3 记忆 + 6 维守卫），Phase 3 主题引擎启动。

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

### 引擎全景（5 引擎）

| 引擎 | Phase | 状态 | 维护 |
|------|-------|------|------|
| Character Engine | Phase 1 | ✅ | 实践者 |
| World Engine | Phase 1 | ✅ | 实践者 |
| Narrative Engine | Phase 2 | ✅ | 协作者 |
| Prose Engine | Phase 2 | ✅ | 协作者 |
| Theme Engine | Phase 3 | ✅ | 协作者 |

### 记忆系统（3 层 + 门面）

| 模块 | 文件 | 存储 |
|------|------|------|
| Working Memory | `src/memory/working_memory.py` | 内存 dict |
| Episodic Memory | `src/memory/episodic_memory.py` | SQLite + 热缓存 |
| Permanent Memory | `src/memory/permanent_memory.py` | SQLite |
| Memory Manager | `src/memory/manager.py` | 协调三层 |

### 守卫（6 维）

Phase 1: `character`, `world_rule`, `spatial`
Phase 2: `foreshadowing`, `causal`, `narrative_consistency`

### LLM 任务类型（14 个）

7 Phase 1（实践者）+ 6 Phase 2（协作者）+ 1 Phase 3（协作者）

### 验证命令

```cmd
# 单模块测试
.venv\Scripts\python scripts\test_narrative_engine.py
.venv\Scripts\python scripts\test_prose_engine.py
.venv\Scripts\python scripts\test_memory_system.py

# Phase 2 全链路集成测试
.venv\Scripts\python scripts\test_phase2_integration.py

# Phase 1 集成测试
.venv\Scripts\python scripts\test_integration.py
```

---

## 共享文件清单

| 文件 | 实践者区段 | 协作者区段 |
|------|-----------|-----------|
| `src/llm/prompts.py` | Phase 1 prompts (L15-L78) | Phase 2/3 prompts (L310+) |
| `src/llm/config.py` | Phase 1 cost estimates | Phase 2/3 cost estimates |
| `src/orchestrator/router.py` | character/world engine | narrative/prose/theme engine |
| `src/api_server.py` | 全部现有端点 | 可新增 Phase 2/3 端点 |
| `src/consistency_guardian/guardian.py` | Phase 1 3 维 | Phase 2 3 维 |
| `docs/SHARED-INTERFACE.md` | 实践者日志+信箱 | 协作者日志+信箱 |

---

## 明天的待办

### 🛠️ 实践者
- [ ] 守卫 Phase 2 维度接入 API
- [ ] `api_server.py` 新增 narrative / prose / theme 端点
- [ ] 前端接入新引擎分析结果展示
- [ ] 前端 UX 打磨

### 🧠 协作者
- [ ] Phase 3 经济引擎（如有合同支撑）
- [ ] Phase 3 读者预期引擎
- [ ] Phase 3 构思引擎
- [ ] 守卫 Phase 3 维度扩展（temporal / power / relationship / style）

---

## 接口文档

📄 `docs/11-PHASE2-INTERFACE.md` — 所有新模块的完整 API 参考
📄 `docs/SHARED-INTERFACE.md` — 共享接口注册表 + 信箱
