/**
 * Agent 标注类型定义 — Narrative Mind v4.0
 *
 * Phase E: 标注层、建议、状态栏的共享类型。
 */

/** Agent 分析标注 */
export interface AgentAnnotation {
  /** 标注 ID */
  id: string;
  /** Agent ID */
  agent_id: string;
  /** Agent 中文名 */
  agent_name: string;
  /** 标注消息 */
  message: string;
  /** 严重级别 */
  severity: "info" | "warn" | "critical";
  /** 文本位置 */
  location?: {
    start_line: number;
    start_column: number;
    end_line: number;
    end_column: number;
  };
  /** 修改建议（可选） */
  suggestion?: string;
}

/** Agent 分析进度 */
export interface AgentProgressEvent {
  agent_id: string;
  agent_name: string;
  stage: string;
  progress_pct: number;
}

/** 分析完成事件 */
export interface AnalysisCompleteEvent {
  request_id: string;
  total_cost: number;
  total_latency: number;
  agent_count: number;
  findings_count: number;
}

/** Agent 运行状态 */
export type AgentStatus = "idle" | "running" | "done" | "error";

/** 单个 Agent 的运行状态 */
export interface AgentState {
  agent_id: string;
  agent_name: string;
  status: AgentStatus;
  progress: number;
  error?: string;
}
