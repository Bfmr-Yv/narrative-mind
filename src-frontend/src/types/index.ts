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
  | "EditorInChief"
  | "EntityExtract"
  | "WorldRuleExtract"
  | "CharacterProfileExtract"
  | "PlotStructureExtract"
  | "StyleExtract"
  | "ContextReflection"
  | "Continuation";

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
  sort_order: number;
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

// =========================================================================
// Phase E: Agent 标注 & 前端 UI 类型
// =========================================================================

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
  /** 严重级别（与 Rust Severity PascalCase 对齐） */
  severity: Severity;
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

/** 分析完成事件（与 Rust analysis:complete payload 对齐） */
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

// =========================================================================
// Phase L1: 实体类型（与 Rust xmgl-core 对齐）
// =========================================================================

export type CharacterStatus = "Alive" | "Dead" | "Unknown";

export interface Character {
  id: string;
  project_id: string;
  name: string;
  aliases: string[];
  status: CharacterStatus;
  current_location: string | null;
  role: string;
  summary: string;
  first_appearance_chapter: string | null;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface CharacterRelation {
  id: string;
  character_a: string;
  character_b: string;
  relation_type: string;
  description: string;
  created_at: string;
}

export interface Location {
  id: string;
  project_id: string;
  name: string;
  aliases: string[];
  location_type: string;
  parent_location: string | null;
  description: string;
  features: string[];
  created_at: string;
  updated_at: string;
}

export type ForeshadowStatus = "Planted" | "Hinted" | "PayingOff" | "Resolved";

export interface ForeshadowEntry {
  id: string;
  project_id: string;
  title: string;
  description: string;
  quote: string | null;
  setup_chapter_id: string;
  payoff_chapter_id: string | null;
  status: ForeshadowStatus;
  related_characters: string[];
  related_locations: string[];
  created_at: string;
  updated_at: string;
}

export type TimelineEventType =
  | "CharacterIntro"
  | "CharacterDeath"
  | "LocationIntro"
  | "ForeshadowPlanted"
  | "ForeshadowResolved"
  | "MajorPlotPoint"
  | "WorldRuleChange";

export interface TimelineEvent {
  id: string;
  chapter_id: string;
  chapter_title: string;
  event_type: TimelineEventType;
  description: string;
  related_entities: string[];
  sort_order: number;
}

// =========================================================================
// Phase A: ProjectContext — 类型化创作上下文
// =========================================================================

export interface ProjectContext {
  project_id: string;
  context_version: number;
  updated_at: string;
  world_rules: WorldRules | null;
  character_profiles: CharacterProfile[];
  plot_outline: PlotOutline | null;
  style_guide: StyleGuide | null;
  theme_map: ThemeMap | null;
}

export interface WorldRules {
  magic_system: string;
  technology_level: string;
  social_structure: string;
  geography: string;
  custom_rules: string[];
}

export interface CharacterProfile {
  character_id: string;
  name: string;
  background: string;
  personality: string;
  goals: string[];
  speech_patterns: string;
}

export interface PlotOutline {
  main_plot: string;
  subplots: string[];
  foreshadow_plan: string[];
  chapter_outlines: ChapterOutline[];
}

export interface ChapterOutline {
  chapter_index: number;
  summary: string;
  key_events: string[];
}

export interface StyleGuide {
  prose_style: string;
  sentence_preferences: string;
  dialogue_conventions: string;
  narrative_distance: string;
}

export interface ThemeMap {
  primary_themes: string[];
  imagery_motifs: string[];
  theme_arcs: ThemeArc[];
}

export interface ThemeArc {
  theme: string;
  current_stage: string;
  planned_development: string;
}

// =========================================================================
// Phase C: 上下文反思建议
// =========================================================================

export interface ContextSuggestion {
  id: string;
  field_path: string;
  current_value: string;
  suggested_value: string;
  evidence: string;
  confidence: number;
  agent_id: string;
  chapter_id: string;
  timestamp: string;
}
