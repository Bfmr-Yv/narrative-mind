# Narrative Mind v4.0 — 短期计划 2

> **状态**: 待开发者执行
> **创建**: 2026-06-16
> **范围**: 完成 Phase A 剩余部分 — 前端脚手架 + Tauri 集成
> **前置**: 短期计划 1 (T1-T8) 已完成

---

## Phase A 完成标准（剩余）

```
✅ cargo check --workspace 通过
✅ Python sidecar 启动 + 健康检查通过
❌ 前端 npm run dev 可访问 (localhost:1420)
❌ tauri.conf.json 存在
❌ cargo tauri dev 打开桌面窗口
```

---

## 任务列表

### F1: 完善前端 package.json + 安装依赖

当前 `src-frontend/package.json` 存在但依赖未安装。

```bash
cd src-frontend
npm install
npm run dev    # 验证 Vite 启动 → localhost:1420
```

**注意**: Windows 上可能需要检查 `vite.config.ts` 的 host 配置。

---

### F2: 创建前端基础组件结构

当前 `App.tsx` 是占位 div。创建基础架子：

```
src-frontend/src/
├── main.tsx          # 已有，保留
├── App.tsx           # 替换为布局框架（TitleBar + EditorArea + Sidebar 占位）
├── App.css           # 基础布局样式
├── components/
│   ├── TitleBar.tsx       # 顶部标题栏（项目名 + Agent 状态指示）
│   ├── EditorArea.tsx     # Monaco 编辑器占位区
│   └── LeftSidebar.tsx    # 左侧导航占位
├── monaco/
│   └── index.ts           # Monaco 配置入口（暂为占位）
├── store/
│   └── index.ts           # Zustand store 骨架
└── types/
    └── index.ts           # TypeScript 类型定义
```

**关键**: Monaco 编辑器暂不嵌入——先保证组件骨架 + Vite 能跑。Monaco 完整集成留到 Phase E。

---

### F3: 创建 `tauri.conf.json`

**位置**: `src-tauri/tauri.conf.json`

```json
{
  "productName": "Narrative Mind",
  "version": "4.0.0",
  "identifier": "com.narrative-mind.app",
  "build": {
    "frontendDist": "../src-frontend/dist",
    "devUrl": "http://localhost:1420",
    "beforeDevCommand": "cd ../src-frontend && npm run dev",
    "beforeBuildCommand": "cd ../src-frontend && npm run build"
  },
  "app": {
    "title": "Narrative Mind v4.0",
    "windows": [
      {
        "title": "Narrative Mind v4.0 — AI 辅助小说创作",
        "width": 1400,
        "height": 900
      }
    ]
  }
}
```

---

### F4: 更新 `main.rs` 集成 Tauri

当前 `main.rs` 只是 `println!` 占位。替换为 Tauri 入口：

```rust
//! Narrative Mind v4.0 — Tauri 桌面应用入口

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("启动失败");
}
```

同时在 `src-tauri/Cargo.toml` 的 `[dependencies]` 中取消 Tauri 注释或添加 `tauri` 依赖。

---

### F5: 验证集成

```bash
cd src-tauri
cargo tauri dev
```

**预期**: 桌面窗口打开，显示前端占位页面。

**如果 Tauri CLI 未安装**: `cargo install tauri-cli`

---

## 执行顺序

```
F1 (npm install + 验证 Vite)
    │
    ▼
F2 (前端组件骨架)
    │
    ├── F3 (tauri.conf.json) ──┐
    │                           ├── F5 (验证 tauri dev)
    └── F4 (main.rs Tauri)  ──┘
```

F2 和 F3/F4 可由开发者自行并行或串行。

---

## Phase A 完成后验证

```
1. cargo check --workspace     ✅
2. python main.py              ✅
3. curl /v1/llm/health         ✅
4. npm run dev (localhost:1420)  ← 待 F1-F2
5. cargo tauri dev 开窗口        ← 待 F3-F5
```

全部 5 项通过 → Phase A done → 进入 Phase B（数据层）。

---

## 不做的事

- ❌ 不嵌入 Monaco 编辑器（Phase E）
- ❌ 不连接 Tauri IPC（Phase B）
- ❌ 不创建数据库（Phase B）
- ❌ 前端只做布局骨架，不做交互逻辑
