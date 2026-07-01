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

export {
  listChapters,
  createChapter,
  getChapter,
  updateChapter,
  deleteChapter,
} from "./chapters";

export {
  onAgentProgress,
  onProposalReady,
  onAnalysisComplete,
} from "./events";
export type { AgentProgress, ProposalReady, AnalysisComplete } from "./events";
