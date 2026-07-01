/**
 * Tauri Events 监听 — Narrative Mind v4.0
 *
 * Phase D 接入 Orchestrator 后，Rust 端会 emit 这些事件。
 * 当前 API 方法为 ready-to-use 占位。
 */

import { listen } from "@tauri-apps/api/event";
import type { UnlistenFn } from "@tauri-apps/api/event";

export interface AgentProgress {
  agent_id: string;
  agent_name: string;
  stage: string;
  progress_pct: number;
}

export interface ProposalReady {
  proposal_id: string;
  agent_id: string;
  title: string;
  severity: string;
  location?: { start_line: number; start_column: number; end_line: number; end_column: number };
}

export interface AnalysisComplete {
  total_cost: number;
  total_latency: number;
  agent_count: number;
  findings_count: number;
}

export function onAgentProgress(cb: (p: AgentProgress) => void): Promise<UnlistenFn> {
  return listen("agent:progress", (event) => cb(event.payload as AgentProgress));
}

export function onProposalReady(cb: (p: ProposalReady) => void): Promise<UnlistenFn> {
  return listen("proposal:ready", (event) => cb(event.payload as ProposalReady));
}

export function onAnalysisComplete(cb: (p: AnalysisComplete) => void): Promise<UnlistenFn> {
  return listen("analysis:complete", (event) => cb(event.payload as AnalysisComplete));
}
