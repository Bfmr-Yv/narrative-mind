/**
 * 分析 API — Tauri IPC 封装
 *
 * 通过 invoke() 调用 Rust 端的 run_analysis 命令。
 */

import { invoke } from "@tauri-apps/api/core";

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
