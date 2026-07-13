/**
 * API 模块 barrel export。
 *
 * 前端统一通过此模块调用 Tauri IPC：
 *   import { listProjects, createChapter } from "@/api";
 */

export {
  listProjects,
  createProject,
  getProject,
  deleteProject,
} from "./projects";
export type { ProjectMeta } from "./projects";

export {
  listChapters,
  createChapter,
  getChapter,
  updateChapter,
  deleteChapter,
} from "./chapters";
export type { ChapterData } from "./chapters";

export {
  onAgentProgress,
  onProposalReady,
  onAnalysisComplete,
} from "./events";
export type { AgentProgress, ProposalReady, AnalysisComplete } from "./events";

export {
  runAnalysis,
  runFullAnalysis,
  expandContextSection,
  runImportAnalysis,
} from "./analysis";
export type { AnalysisOutput, AgentOutput } from "./analysis";

// Phase L1: 实体 CRUD
export {
  listCharacters,
  getCharacter,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  listLocations,
  getLocation,
  createLocation,
  updateLocation,
  deleteLocation,
  listForeshadows,
  getForeshadow,
  createForeshadow,
  updateForeshadow,
  deleteForeshadow,
  listTimeline,
  // Phase L2: 项目设置
  listProjectSettings,
  setProjectSetting,
  deleteProjectSetting,
} from "./entities";
