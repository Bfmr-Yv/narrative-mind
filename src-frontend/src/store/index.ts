import { create } from "zustand";
import type {
  ProjectMeta, ChapterData, AgentId, Character, Location,
  ForeshadowEntry, TimelineEvent,
} from "../types";
import type { AnalysisOutput } from "../api";
import * as api from "../api";
import * as entitiesApi from "../api/entities";

/**
 * Zustand 全局状态 — Narrative Mind v4.0
 *
 * Phase B: 项目/章节 CRUD + 编辑器 + Agent 状态。
 * Phase C/D: 逐步接入 Orchestrator 调度、gutter markers、分析结果。
 */

// =========================================================================
// Slice types
// =========================================================================

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
  id: AgentId;
  name: string;
  isBusy: boolean;
  lastResult: string | null;
}

// =========================================================================
// AppState
// =========================================================================

export interface AppState {
  // ── 项目 ──
  projects: ProjectMeta[];
  /** 当前打开的项目（metadata） */
  currentProject: ProjectMeta | null;
  /** 加载项目列表 */
  loadProjects: () => Promise<void>;
  /** 创建项目并刷新列表 */
  createProject: (name: string) => Promise<ProjectMeta>;
  /** 删除项目 */
  deleteProject: (id: string) => Promise<void>;

  // ── 章节 ──
  chapters: ChapterData[];
  /** 当前编辑的章节 */
  currentChapter: ChapterData | null;
  /** 加载当前项目的章节列表 */
  loadChapters: () => Promise<void>;
  /** 创建章节 */
  createChapter: (title: string, text: string) => Promise<ChapterData>;
  /** 更新章节（本地 + 持久化） */
  updateChapter: (chapter: ChapterData) => Promise<void>;
  /** 删除章节 */
  deleteChapter: (id: string) => Promise<void>;
  /** 切换当前编辑章节 */
  setCurrentChapter: (chapter: ChapterData | null) => void;

  // ── 编辑器 ──
  editor: EditorState;
  setDirty: (dirty: boolean) => void;

  // ── Agent ──
  agents: AgentStatus[];
  updateAgentStatus: (id: AgentId, isBusy: boolean) => void;

  // ── 分析结果 ──
  /** 最近一次分析结果（null = 未分析） */
  analysisResult: AnalysisOutput | null;
  /** 是否正在分析中 */
  analyzing: boolean;
  /** 存储分析结果 */
  setAnalysisResult: (result: AnalysisOutput) => void;
  /** 设置分析状态 */
  setAnalyzing: (v: boolean) => void;
  /** 清除分析结果 */
  clearAnalysisResult: () => void;

  // ── Phase L2: 实体 & 创作库 ──
  characters: Character[];
  locations: Location[];
  foreshadows: ForeshadowEntry[];
  timeline: TimelineEvent[];
  settings: [string, string][];  // project_settings key-value pairs
  selectedEntity: { type: "character" | "location" | "foreshadow" | "setting"; id: string } | null;
  editingEntity: boolean;
  loadCharacters: () => Promise<void>;
  loadLocations: () => Promise<void>;
  loadForeshadows: () => Promise<void>;
  loadTimeline: () => Promise<void>;
  loadSettings: () => Promise<void>;
  createCharacter: (c: Character) => Promise<void>;
  updateCharacter: (c: Character) => Promise<void>;
  deleteCharacter: (id: string) => Promise<void>;
  createLocation: (l: Location) => Promise<void>;
  updateLocation: (l: Location) => Promise<void>;
  deleteLocation: (id: string) => Promise<void>;
  createForeshadow: (f: ForeshadowEntry) => Promise<void>;
  updateForeshadow: (f: ForeshadowEntry) => Promise<void>;
  deleteForeshadow: (id: string) => Promise<void>;
  setProjectSetting: (key: string, value: string) => Promise<void>;
  deleteProjectSetting: (key: string) => Promise<void>;
  selectEntity: (type: "character" | "location" | "foreshadow" | "setting", id: string) => void;
  setEditing: (editing: boolean) => void;
  clearSelection: () => void;
}

// =========================================================================
// Store factory
// =========================================================================

export const useAppStore = create<AppState>((set, get) => ({
  // ── 项目初始值 ──
  projects: [],
  currentProject: null,

  loadProjects: async () => {
    const projects = await api.listProjects();
    set({ projects });
  },

  createProject: async (name: string) => {
    const project = await api.createProject(name);
    // 乐观更新：把新项目放进列表
    set((state) => ({ projects: [project, ...state.projects] }));
    return project;
  },

  deleteProject: async (id: string) => {
    await api.deleteProject(id);
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== id),
      // 如果删的是当前项目，清空
      currentProject:
        state.currentProject?.id === id ? null : state.currentProject,
      chapters:
        state.currentProject?.id === id ? [] : state.chapters,
      currentChapter:
        state.currentProject?.id === id ? null : state.currentChapter,
    }));
  },

  // ── 章节初始值 ──
  chapters: [],
  currentChapter: null,

  loadChapters: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    const chapters = await api.listChapters(currentProject.id);
    set({ chapters });
  },

  createChapter: async (title: string, text: string) => {
    const { currentProject } = get();
    if (!currentProject) throw new Error("No current project");
    const chapter = await api.createChapter(currentProject.id, title, text);
    // 刷新列表+统计
    await get().loadChapters();
    await get().loadProjects();
    return chapter;
  },

  updateChapter: async (chapter: ChapterData) => {
    await api.updateChapter(chapter);
    // 从后端 re-fetch：Rust 端会重新计算 word_count、刷新 updated_at，
    // 本地乐观写入会丢失这些服务端计算结果。
    await get().loadChapters();
    // 章节字数变化可能影响项目统计
    await get().loadProjects();
  },

  deleteChapter: async (id: string) => {
    await api.deleteChapter(id);
    set((state) => ({
      chapters: state.chapters.filter((ch) => ch.id !== id),
      currentChapter:
        state.currentChapter?.id === id ? null : state.currentChapter,
    }));
    // 刷新项目统计
    await get().loadProjects();
  },

  setCurrentChapter: (chapter) => set({ currentChapter: chapter }),

  // ── 编辑器初始值 ──
  editor: {
    isDirty: false,
    currentLine: 1,
    currentColumn: 1,
  },

  setDirty: (dirty) =>
    set((state) => ({ editor: { ...state.editor, isDirty: dirty } })),

  // ── Agent 初始值 ──
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
    {
      id: "EntityExtract",
      name: "实体提取 Agent",
      isBusy: false,
      lastResult: null,
    },
  ],

  updateAgentStatus: (id, isBusy) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, isBusy } : a)),
    })),

  // ── 分析结果 ──
  analysisResult: null,
  analyzing: false,

  setAnalysisResult: (result) => set({ analysisResult: result }),

  setAnalyzing: (v) => set({ analyzing: v }),

  clearAnalysisResult: () => set({ analysisResult: null }),

  // ── 实体初始值 ──
  characters: [],
  locations: [],
  foreshadows: [],
  timeline: [],
  settings: [],
  selectedEntity: null,
  editingEntity: false,

  loadCharacters: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    const characters = await entitiesApi.listCharacters(currentProject.id);
    set({ characters });
  },

  loadLocations: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    const locations = await entitiesApi.listLocations(currentProject.id);
    set({ locations });
  },

  loadForeshadows: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    const foreshadows = await entitiesApi.listForeshadows(currentProject.id);
    set({ foreshadows });
  },

  loadTimeline: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    const timeline = await entitiesApi.listTimeline(currentProject.id);
    set({ timeline });
  },

  loadSettings: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    try {
      const settings = await entitiesApi.listProjectSettings(currentProject.id);
      set({ settings });
    } catch {
      set({ settings: [] });
    }
  },

  createCharacter: async (c: Character) => {
    await entitiesApi.createCharacter(c);
    await get().loadCharacters();
  },

  updateCharacter: async (c: Character) => {
    await entitiesApi.updateCharacter(c);
    await get().loadCharacters();
  },

  deleteCharacter: async (id: string) => {
    await entitiesApi.deleteCharacter(id);
    set((s) => ({
      characters: s.characters.filter((ch) => ch.id !== id),
      selectedEntity: s.selectedEntity?.id === id ? null : s.selectedEntity,
    }));
  },

  createLocation: async (l: Location) => {
    await entitiesApi.createLocation(l);
    await get().loadLocations();
  },

  updateLocation: async (l: Location) => {
    await entitiesApi.updateLocation(l);
    await get().loadLocations();
  },

  deleteLocation: async (id: string) => {
    await entitiesApi.deleteLocation(id);
    set((s) => ({
      locations: s.locations.filter((loc) => loc.id !== id),
      selectedEntity: s.selectedEntity?.id === id ? null : s.selectedEntity,
    }));
  },

  createForeshadow: async (f: ForeshadowEntry) => {
    await entitiesApi.createForeshadow(f);
    await get().loadForeshadows();
  },

  updateForeshadow: async (f: ForeshadowEntry) => {
    await entitiesApi.updateForeshadow(f);
    await get().loadForeshadows();
  },

  deleteForeshadow: async (id: string) => {
    await entitiesApi.deleteForeshadow(id);
    set((s) => ({
      foreshadows: s.foreshadows.filter((fs) => fs.id !== id),
      selectedEntity: s.selectedEntity?.id === id ? null : s.selectedEntity,
    }));
  },

  setProjectSetting: async (key: string, value: string) => {
    const { currentProject } = get();
    if (!currentProject) return;
    await entitiesApi.setProjectSetting(currentProject.id, key, value);
    await get().loadSettings();
  },

  deleteProjectSetting: async (key: string) => {
    const { currentProject } = get();
    if (!currentProject) return;
    await entitiesApi.deleteProjectSetting(currentProject.id, key);
    await get().loadSettings();
  },

  selectEntity: (type, id) => set({ selectedEntity: { type, id }, editingEntity: false }),

  setEditing: (editing) => set({ editingEntity: editing }),

  clearSelection: () => set({ selectedEntity: null, editingEntity: false }),
}));
