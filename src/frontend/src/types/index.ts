/* Narrative Mind v3.1 — Shared TypeScript types */

// =========================================================================
// Domain models
// =========================================================================

export interface Chapter {
  id: string;
  title: string;
  text: string;
  created: string;
  updated: string;
}

export interface ProjectMeta {
  id: string;
  name: string;
  created: string;
  updated: string;
  total_words: number;
  chapter_count: number;
}

export interface ProjectSettings {
  characters: string[];
  locations: string[];
  power_system: Record<string, unknown>;
}

export interface AnalysisHistoryEntry {
  id: string;
  timestamp: Date;
  characterId: string;
  location: string;
  chapterId: string;
  response: OrchestratorResponse;
}

// =========================================================================
// API response shapes (mirrors backend)
// =========================================================================

export interface OrchestratorResponse {
  success: boolean;
  engine_results: {
    character_engine?: CharacterAnalysis;
    world_engine?: WorldValidation;
  };
  guardian_output?: GuardianOutput;
  message: string;
}

export interface CharacterAnalysis {
  pad_state: { pleasure: number; arousal: number; dominance: number };
  behavior_prediction: {
    predicted_action: string;
    confidence: number;
    supporting_evidence: string[];
    alternative_actions: string[];
  };
  implicit_triggers: string[];
  confidence: number;
  needs_human_review: boolean;
}

export interface WorldValidation {
  rule_checks: RuleCheck[];
  spatial_consistency: boolean;
  power_level_validation: string;
}

export interface RuleCheck {
  rule_name: string;
  passed: boolean;
  detail: string;
  conflict_description?: string;
}

export interface GuardianOutput {
  is_consistent: boolean;
  dimension_results?: Record<string, DimensionResult>;
  alarm_level: 'info' | 'warn' | 'critical';
  conflicts: Conflict[];
  action_required: 'none' | 'review' | 'block';
}

export interface DimensionResult {
  dimension: string;
  passed: boolean;
  conflicts: Conflict[];
}

export interface Conflict {
  dimension: string;
  level: 'info' | 'warn' | 'critical';
  detail: string;
  suggestion?: string;
}

// =========================================================================
// API request shapes
// =========================================================================

export interface OrchestratorRequest {
  type: 'analyze' | 'check' | 'predict' | 'finalize';
  payload: Record<string, unknown>;
  project_id?: string;
}

// =========================================================================
// App state (for useReducer)
// =========================================================================

export interface AppState {
  // Projects
  projects: ProjectMeta[];
  activeProjectId: string | null;
  projectSettings: ProjectSettings | null;

  // Project-level editor state
  chapters: Chapter[];
  activeChapterId: string | null;
  selectedCharacterId: string;
  selectedLocation: string;

  // Analysis
  currentAnalysis: OrchestratorResponse | null;
  analysisHistory: AnalysisHistoryEntry[];
  isAnalyzing: boolean;
  analysisError: string | null;

  // Right panel
  activeRightTab: 'analysis' | 'history' | 'references';

  // UI
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  showProjectSettings: boolean;

  // Cost
  costData: CostData;

  // System
  apiConnected: boolean;
}

export interface CostData {
  currentMonth: number;
  monthlyBudget: number;
  breakdown: { category: string; cost: number }[];
}

// =========================================================================
// App actions
// =========================================================================

export type AppAction =
  // Project management
  | { type: 'SET_PROJECTS'; payload: ProjectMeta[] }
  | { type: 'SET_ACTIVE_PROJECT'; payload: string }
  | { type: 'SET_PROJECT_SETTINGS'; payload: ProjectSettings }
  | { type: 'ADD_PROJECT'; payload: ProjectMeta }
  | { type: 'REMOVE_PROJECT'; payload: string }
  | { type: 'TOGGLE_PROJECT_SETTINGS' }
  | { type: 'RETURN_TO_DASHBOARD' }
  // Chapters
  | { type: 'SET_CHAPTERS'; payload: Chapter[] }
  | { type: 'ADD_CHAPTER'; payload: Chapter }
  | { type: 'SELECT_CHAPTER'; payload: string }
  | { type: 'UPDATE_CHAPTER_TITLE'; payload: { id: string; title: string } }
  | { type: 'UPDATE_CHAPTER_TEXT'; payload: { id: string; text: string } }
  | { type: 'DELETE_CHAPTER'; payload: string }
  // Selection
  | { type: 'SELECT_CHARACTER'; payload: string }
  | { type: 'SELECT_LOCATION'; payload: string }
  // Analysis
  | { type: 'ANALYSIS_START' }
  | { type: 'ANALYSIS_SUCCESS'; payload: OrchestratorResponse }
  | { type: 'ANALYSIS_FAILURE'; payload: string }
  // Tabs & UI
  | { type: 'SELECT_TAB'; payload: 'analysis' | 'history' | 'references' }
  | { type: 'SELECT_HISTORY_ENTRY'; payload: string }
  | { type: 'TOGGLE_LEFT_PANEL' }
  | { type: 'TOGGLE_RIGHT_PANEL' }
  | { type: 'SET_API_STATUS'; payload: boolean };

// =========================================================================
// Defaults (empty — user projects provide their own)
// =========================================================================

export const EMPTY_SETTINGS: ProjectSettings = {
  characters: [],
  locations: [],
  power_system: {
    name: '通用力量体系',
    levels: [{ name: '普通人', capabilities: ['基础体能', '日常技能'] }],
    rules: [],
  },
};
