---
name: daily-rhythm
description: 每日开工 + 收工一体。开工：/开工、/start、开工、上班、早上好。收工：/收工、/wrap、收工、下班、结束今天
---

# 每日节律 Skill

一个 Skill，两个模式。根据用户触发词自动选择。

- **开工模式** → 同步代码 → 读交接记忆 → 审查昨夜提交 → 环境快检 → 呈现今日起点
- **收工模式** → 编译检查 → 协调开发者 → 提交 → 推送 → 写交接记忆

---

## 模式判断

用户说 `/开工`、`开工`、`/start`、`上班`、`早上好` → **开工模式**
用户说 `/收工`、`收工`、`/wrap`、`下班`、`结束今天` → **收工模式**

---

# 开工模式

## 核心原则

- **问题前置** — warnings 和待审查项第一眼看到
- **信息密集** — 快速进入状态，不啰嗦
- **可操作** — 每个信息指向下一步行动

## 执行流程

### 1. 同步代码

```bash
git pull --rebase
```

| 结果 | 行为 |
|------|------|
| 成功 | 继续 |
| 有冲突 | 报告冲突文件，**停止** |
| 无网络 | 标 ⚠️ 离线，继续 |

### 2. 读取交接记忆

查找 `memory/session-handoff-*.md`，取最新一份。解析 frontmatter：

```
phase, progress, next, warnings, commits
```

无记忆则从 `git log --since="48 hours ago"` 反推。

### 3. 呈现仪表盘

```
📅 开工 — YYYY-MM-DD

┌─────────────────────────────────────────────────────┐
│ Phase:  <phase>                                      │
│ 进度:   <progress>                                   │
│ 下一步: <next>                                       │
└─────────────────────────────────────────────────────┘
```

如果 `warnings` 非空，在上方先显示：

```
⚠️ 昨日警告
  • <warning 1>
  • <warning 2>
```

### 4. 昨夜提交

根据交接记忆中的 `commits` 或 `git log --since="24 hours ago"`：

```
昨夜提交 (N commits):
  abc1234 feat: <message>                    (+xxx -xx)
  def5678 chore: <message>                   (+xx -xx)
```

### 5. 待审查项

从交接记忆 `## 待审查` 提取：

```
📝 待审查
  • <审查项 1>
  • <审查项 2>
```

### 6. 环境快检

```bash
cd src-tauri && cargo check --workspace 2>&1 | tail -5
python3 --version 2>&1
```

与交接记忆的 `## 环境状态` 对比：

```
环境状态:
  cargo check   ✅ (昨日: ✅)
  Python        ✅ 3.11.15 (昨日: ✅)
  git           干净
  前端          未设置
```

变化项标 ⚠️。

### 7. 今日起点

```
📍 今日起点

Phase:  <phase> — <progress>
下一步: <next>

建议:
  1. 审查昨夜开发者产出（上面 📝 待审查）
  2. 确认方向后在开发者窗口执行
```

**完成后**：停止，让用户决定今天做什么。

---

# 收工模式

## 核心原则

- **开发者负责 commit，维护者负责 push** — 这是铁律
- **交接基于 git log** — 不是对话印象，是实际提交了什么
- **失败即停** — 编译失败/开发者未提交/push 被拒才留步
- **结构化输出** — 交接记忆用标准格式，供明天开工解析

## 与开发者窗口的协作

```
开发者                          维护者
  │                               │
  │ 完成任务 → git commit          │
  │ 收到"收工" → 完成最小任务       │
  │           → git commit         │
  │           → "已提交"            │
  │                               │  /收工
  │                               │  → git 干净 ✅
  │                               │  → 读 git log 写交接
  │                               │  → git push
```

维护者 `/收工` 时：
1. 检查 git 状态
2. 有代码变更 → 停止，等开发者 commit
3. git 干净 → **所有变更都来自已提交的 commits** → 基于 `git log` 写交接
4. push 所有 commits

这样交接记忆的内容 = 开发者实际提交的 = 明天开工看到的 = 完全一致。

维护者自己的文件 (CLAUDE.md, docs/, .claude/, memory/) 直接提交，不算"半成品"。

## 执行流程

### 1. cargo check

```bash
cd src-tauri && cargo check --workspace 2>&1 | tail -10
```

- 通过 → 继续
- 失败 → 报告错误，**停止**。"编译失败，修完再 /收工"

### 2. 判断 git 状态 + 协调开发者

```bash
git status --short
```

| git 状态 | 行为 |
|----------|------|
| **干净** | 跳到 Step 4 (push) |
| **只有维护者文件** (CLAUDE.md, docs/, .claude/, memory/) | 直接 commit，继续 |
| **包含代码文件** (src-tauri/, src-python/, src-frontend/) | **停止** |

检测到代码文件变更时：

```
⏸️  检测到代码文件变更 — 需要先协调开发者提交

当前未提交:
  <列出文件>

步骤:
  1. 切到开发者窗口
  2. 让它完成当前最小任务并 git commit
  3. 回到这里重新 /收工
```

不会绕过。唯一例外：用户明确说"直接提交，开发者已经停了"。

### 3. 提交维护者变更

```bash
git add -A
git commit -m "[maintainer] <维护者侧变更摘要>"
```

### 4. git push

```bash
git push
```

| 结果 | 行为 |
|------|------|
| 成功 | 继续 |
| rejected | 停，"远程有新提交，手动处理" |
| 网络错误 | 继续，"已本地提交，推送失败（网络）。明天手动 push" |
| 分支落后 | `git pull --rebase` 后重试 |

### 5. 写交接记忆

**数据来源**：`git log --since="24 hours ago" --oneline` — 不是对话印象。

```bash
git log --since="24 hours ago" --oneline --stat
```

根据实际提交记录写入 `memory/session-handoff-YYYY-MM-DD.md`。

```markdown
---
phase: <当前 Phase>
progress: <当前进度描述>
next: <下一步任务 ID 或描述>
warnings: <警告列表，无则写 []>
commits: <本次提交的 hash 列表>
---

## 今日产出

- <具体完成的事项>

## 待审查

- <需要明天检查的内容>

## 注意事项

- <踩坑、配置变更、环境问题>

## 环境状态

| 项目 | 状态 |
|------|------|
| cargo check | ✅ / ❌ |
| Python | ✅ / ❌ |
| 前端 | ✅ / ❌ / 未设置 |
| git | 已推送 / ⚠️ 未推送 |
```

frontmatter 的 `phase`、`warnings`、`next` 会被明天开工模式精确解析。

### 6. 打印总结

```
📋 收工完毕 — YYYY-MM-DD

✅ cargo check      通过
✅ git              <状态>
✅ git push         已推送
✅ 交接记忆         session-handoff-YYYY-MM-DD.md

交接要点:
  进度: <progress>
  下一步: <next>
  警告: <warnings，无则显示"无">

明天见 👋
```

---

# 交接格式规范（开工 ↔ 收工纽带）

| 收工产出 | 开工消费 |
|----------|---------|
| frontmatter `phase` | 显示当前阶段 |
| frontmatter `warnings` | **首位**红色高亮 |
| frontmatter `next` | "今日起点"章节 |
| `## 待审查` | 提醒过一遍开发者产出 |
| `## 注意事项` | 环境/配置提醒 |
| `## 环境状态` | 与当前环境逐项对比 |
| commit hashes | `git log` 精确展示昨夜变更 |
