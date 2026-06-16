---
name: l1-l4-guard
description: L1-L4 协议合规检查 — 在提交前验证文档和代码是否符合项目规范。当用户提到"检查"、"合规"、"L1"、"L2"、"L3"、"L4"、"提交前"、"commit"时触发。
---

# L1-L4 协议守卫

对修改的文件执行四层合规检查。

## L1: 记忆层（文档卫生）

对 `docs/` 目录下的所有已修改 `.md` 文件：

```bash
# 检查连续重复行（排除空行和表格分隔行，它们是正常的 markdown 模式）
for f in $(git diff --name-only -- docs/); do
  echo "--- $f ---"
  # uniq -d 永远返回 0，必须用 grep -q . 检测是否有实际输出
  uniq -d "$f" | grep -v '^$' | grep -v '^|---' | grep -q . && echo "⚠️ 发现重复行" || echo "✅"
done
```

同时检查：
- 日期格式是否为 YYYY-MM-DD（不是 YYYY/MM/DD 或 MM-DD-YYYY）
- 成本数字是否与 `docs/04-COST-BUDGET.md` 一致

## L2: 扩展层（命名对齐）

检查所有修改文件中的命名：
1. 搜索废弃名称：`Style Engine`、`Impact Radar`
2. 新引用的引擎名是否在 `CLAUDE.md` 命名冻结表中
3. 新引用的引擎是否在当前 Phase 激活

```bash
# 搜索废弃名称（排除重命名说明行，避免假阳性）
git diff --name-only | xargs grep -n "Style Engine\|Impact Radar" 2>/dev/null | grep -v "重命名\|原名\|原名\|废弃\|→\|->" && echo "❌ 发现废弃名称" || echo "✅"
```

## L3: 集成层（跨模块一致性）

1. Phase 标记是否正确（`[Phase 1]` / `[Phase 2]` / `[Phase 3]`）
2. 一致性守卫维度名是否与 `docs/02-CONTRACTS.md` 一致
3. 成本数字跨文件自洽

```bash
# 检查 Phase 标记是否使用了未激活的 Phase
git diff --name-only | xargs grep -n "\[Phase [45]" 2>/dev/null && echo "❌ 引用了未激活的 Phase" || echo "✅"

# 检查成本数字是否与 04-COST-BUDGET.md 一致
echo "⚠️ 人工核对：$20 月度上限、三层熔断 50%/80%/95%"
```

## L4: 编程层（代码规范）

1. Python 核心引擎是否仅使用标准库（`src/engines/` 文件不应 import 非标准库）
2. LLM 集成层（`src/llm/`）允许 `openai` SDK
3. 代码风格与现有模块一致

```bash
# 检查 src/engines/ 是否仅使用标准库（排除 __future__ 和 typing）
git diff --name-only -- src/engines/ | xargs grep "^import\|^from" 2>/dev/null | grep -v "__future__\|typing\|dataclasses\|json\|os\|sys\|re\|math\|collections\|pathlib\|itertools\|functools\|abc\|enum\|hashlib\|logging\|textwrap" && echo "❌ 引擎文件引用了非标准库" || echo "✅"
```

## 输出格式

```
🔍 L1-L4 合规检查报告
═══════════════════════
L1 记忆层: [✅/⚠️]
L2 扩展层: [✅/❌]
L3 集成层: [✅/⚠️]
L4 编程层: [✅/❌]
═══════════════════════
阻断项: [无 / 列出]
建议修复: [列出]
```

如果 L2 或 L4 出现 ❌，必须阻止提交直到修复。
