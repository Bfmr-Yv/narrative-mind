/**
 * TypeScript 类型定义 — Narrative Mind v4.0
 *
 * 与 Rust xmgl-core 类型对齐，通过 Tauri IPC 传输。
 * 命名约定：JSON 字段使用 snake_case（匹配 Rust serde 序列化）。
 */

// =========================================================================
// PAD 情感模型
// =========================================================================

export interface PADState {
  pleasure: number; // [-1, 1]
  arousal: number; // [-1, 1]
  dominance: number; // [-1, 1]
}

// =========================================================================
// Agent 标识
// =========================================================================

export type AgentId =
  | "Character"
  | "World"
  | "Narrative"
  | "Prose"
  | "Theme"
  | "Economy"
  | "ReaderExpectation"
  | "Conception"
  | "EditorInChief";

// =========================================================================
// 严重级别
// =========================================================================

export type Severity = "Info" | "Warn" | "Critical";

// =========================================================================
// 任务类型 (17 LLM task types)
// =========================================================================

export type TaskType =
  | "pad_compute"
  | "action_infer"
  | "rule_check"
  | "spatial_check"
  | "rerank"
  | "entity_extract"
  | "scene_analysis"
  | "foreshadow_detect"
  | "causal_extract"
  | "resolution_check"
  | "event_predict"
  | "style_check"
  | "register_check"
  | "theme_extract"
  | "economy_check"
  | "expectation_analyze"
  | "imagery_detect";

// =========================================================================
// 文本范围
// =========================================================================

export interface TextRange {
  start_line: number;
  start_column: number;
  end_line: number;
  end_column: number;
  start_byte: number;
  end_byte: number;
}

// =========================================================================
// 项目 & 章节
// =========================================================================

export interface ProjectMeta {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  chapter_count: number;
  total_words: number;
}

export interface ChapterData {
  id: string;
  project_id: string;
  title: string;
  text: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

// =========================================================================
// LLM 调用 (Tauri IPC)
// =========================================================================

export interface LLMCallRequest {
  request_id: string;
  task_type: TaskType;
  system_prompt_key: string;
  user_message: string;
  response_format?: "json" | "text";
  temperature_override?: number;
  max_tokens_override?: number;
}

export interface LLMUsage {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  model: string;
  latency_ms: number;
}

export interface LLMCallResponse {
  request_id: string;
  success: boolean;
  result?: Record<string, unknown>;
  usage?: LLMUsage;
  error?: string;
}

// =========================================================================
// Agent 分析结果（通用）
// =========================================================================

export interface AgentFinding {
  agent_id: AgentId;
  severity: Severity;
  title: string;
  description: string;
  location: TextRange | null;
  suggestion: string | null;
  timestamp: string;
}
