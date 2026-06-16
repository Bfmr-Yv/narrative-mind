---
name: task-type-register
description: 新增 LLM task_type 的三处同步注册向导。当用户提到"新增task_type"、"注册task"、"新任务类型"或修改 prompts.py/config.py 的 task_type 相关区域时触发。
---

# Task Type 三处同步注册

新增 `task_type` 时，必须在三个文件中同步注册。缺少任何一处都会导致运行时错误或协作者接口断裂。

## 注册清单

### 1️⃣ `src/llm/prompts.py`

添加 System Prompt 常量 + format 函数：

```python
# System prompt（命名：<TASK>_SYSTEM）
NEW_TASK_SYSTEM = """你是一个...专家。你的任务是...
输出严格的JSON格式，不要包含任何其他文本：
{"field1": type, "field2": "description"}"""

# Format 函数（命名：format_<task>_prompt）
def format_new_task_prompt(chapter_text: str, ...) -> str:
    """构建 new_task 的 user message"""
    return f"""..."""
```

### 2️⃣ `src/llm/config.py`

在两处添加条目：

```python
# ESTIMATED_COST_PER_CALL 表
ESTIMATED_COST_PER_CALL = {
    ...
    "new_task": 0.00108,  # ~1200 in + ~400 out
}

# TIER_CONFIG 表
TIER_CONFIG: dict[str, TierRoute] = {
    ...
    "new_task": TierRoute(model=DEFAULT_MODEL, max_tokens=512, temperature=0.3),
}
```

成本估算公式：`(预估_input_tokens × COST_PER_1K_INPUT + 预估_output_tokens × COST_PER_1K_OUTPUT) / 1000`

### 3️⃣ `docs/SHARED-INTERFACE.md` §3.1

在 task_type 表中追加一行：

```markdown
| `new_task` | `NEW_TASK_SYSTEM` | `format_new_task_prompt()` | Phase X | 角色 |
```

## 检查命令

注册完成后运行：

```bash
# 验证三处都已注册
echo "=== prompts.py ===" && grep -n "NEW_TASK" src/llm/prompts.py
echo "=== config.py ===" && grep -n "new_task" src/llm/config.py
echo "=== SHARED-INTERFACE.md ===" && grep -n "new_task" docs/SHARED-INTERFACE.md
```

三个 grep 都必须有输出，否则注册不完整。

## 同步更新

如果新增 task_type 对应新引擎，还需同步更新：
- `docs/02-CONTRACTS.md` — 新引擎的输入/输出契约
- `src/orchestrator/router.py` — `ROUTE_MAP` 添加新路由
- `docs/00-ACTIVE-CONTEXT.md` — 活跃模块表 + LLM 任务类型表
