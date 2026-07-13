/**
 * 分析 API — Tauri IPC 封装
 *
 * 通过 invoke() 调用 Rust 端的 run_analysis 命令。
 */

import { invoke } from "@tauri-apps/api/core";
import type { AgentFinding, Character, ContextSuggestion, Location, ProjectContext } from "../types";

export interface AgentOutput {
  agent_id: string;
  agent_name: string;
  output: string;
}

export interface AnalysisOutput {
  request_id: string;
  agent_outputs: AgentOutput[];
  topology: string;
  complexity: string;
  /** 结构化的 Agent 发现 */
  findings: AgentFinding[];
  /** 累计成本 (USD) */
  total_cost_usd: number;
  /** 累计延迟 (ms) */
  total_latency_ms: number;
  /** Phase L1: 提取的角色 */
  extracted_characters: Character[];
  /** Phase L1: 提取的地点 */
  extracted_locations: Location[];
  /** Phase C: 上下文反思建议 */
  context_suggestions: ContextSuggestion[];
}

/**
 * 触发一次 Agent 分析。
 *
 * @param chapterId - 章节 UUID
 * @param taskType - 分析类型（如 "pad_compute"、"entity_extract"）
 * @returns 分析结果
 */
export async function runAnalysis(
  chapterId: string,
  taskType: string,
): Promise<AnalysisOutput> {
  return invoke<AnalysisOutput>("run_analysis", {
    chapterId,
    taskType,
  });
}

/**
 * 全维度并行分析 — 一键调度全部 10 个 Agent。
 *
 * 每个 Agent 使用自己的主 TaskType，自动注入 ProjectContext。
 * 适用于章节完成后的全面审查。
 *
 * @param chapterId - 章节 UUID
 * @returns 分析结果
 */
export async function runFullAnalysis(
  chapterId: string,
): Promise<AnalysisOutput> {
  return invoke<AnalysisOutput>("run_full_analysis", {
    chapterId,
  });
}

/**
 * AI 辅助填写 — 扩展 ProjectContext 的指定 section。
 *
 * @param section - section 名称 ("world_rules" | "character_profiles" | "plot_outline" | "style_guide" | "theme_map")
 * @param currentJson - 当前已填内容的 JSON 字符串
 * @param projectId - 项目 ID
 * @returns 补充后的 JSON 字符串
 */
export async function expandContextSection(
  section: string,
  currentJson: string,
  projectId: string,
): Promise<string> {
  return invoke<string>("expand_context_section", {
    section,
    currentJson,
    projectId,
  });
}

/**
 * 导入分析 — 从已有小说文本提取创作上下文。
 *
 * @param text - 待分析的文本
 * @param projectId - 项目 ID
 * @returns 提取的 ProjectContext（不自动保存）
 */
export async function runImportAnalysis(
  text: string,
  projectId: string,
): Promise<ProjectContext> {
  return invoke<ProjectContext>("run_import_analysis", {
    text,
    projectId,
  });
}

// ── Phase C: 建议状态管理 ──

export async function setSuggestionState(
  suggestionId: string,
  projectId: string,
  chapterId: string,
  suggestionType: string,
  state: string,
): Promise<void> {
  return invoke<void>("set_suggestion_state", {
    suggestionId,
    projectId,
    chapterId,
    suggestionType,
    suggestionState: state,
  });
}

export async function getDismissedSuggestions(
  projectId: string,
  suggestionType: string,
): Promise<string[]> {
  return invoke<string[]>("get_dismissed_suggestions", {
    projectId,
    suggestionType,
  });
}

export async function clearDismissedSuggestions(
  projectId: string,
): Promise<void> {
  return invoke<void>("clear_dismissed_suggestions", {
    projectId,
  });
}
