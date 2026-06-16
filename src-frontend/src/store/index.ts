import { create } from "zustand";

/**
 * Zustand 全局状态 — Narrative Mind v4.0
 *
 * Phase A 骨架：最小状态结构。
 * Phase B/C 逐步扩展各领域 slice。
 */

export interface ProjectInfo {
  id: string;
  name: string;
  chapterCount: number;
  totalWords: number;
}

export interface EditorState {
  isDirty: boolean;
  currentLine: number;
  currentColumn: number;
}

export interface AgentStatus {
  id: string;
  name: string;
  isBusy: boolean;
  lastResult: string | null;
}

export interface AppState {
  // 项目
  currentProject: ProjectInfo | null;
  // 编辑器
  editor: EditorState;
  // Agent
  agents: AgentStatus[];
  // 操作
  setProject: (project: ProjectInfo | null) => void;
  setDirty: (dirty: boolean) => void;
  updateAgentStatus: (id: string, isBusy: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentProject: null,
  editor: {
    isDirty: false,
    currentLine: 1,
    currentColumn: 1,
  },
  agents: [
    { id: "Character", name: "角色 Agent", isBusy: false, lastResult: null },
    { id: "World", name: "世界 Agent", isBusy: false, lastResult: null },
    { id: "Narrative", name: "叙事 Agent", isBusy: false, lastResult: null },
    { id: "Prose", name: "文辞 Agent", isBusy: false, lastResult: null },
    { id: "Theme", name: "主题 Agent", isBusy: false, lastResult: null },
    { id: "Economy", name: "经济 Agent", isBusy: false, lastResult: null },
    {
      id: "ReaderExpectation",
      name: "预期 Agent",
      isBusy: false,
      lastResult: null,
    },
    { id: "Conception", name: "构思 Agent", isBusy: false, lastResult: null },
    {
      id: "EditorInChief",
      name: "总编 Agent",
      isBusy: false,
      lastResult: null,
    },
  ],

  setProject: (project) => set({ currentProject: project }),
  setDirty: (dirty) =>
    set((state) => ({ editor: { ...state.editor, isDirty: dirty } })),
  updateAgentStatus: (id, isBusy) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, isBusy } : a)),
    })),
}));
