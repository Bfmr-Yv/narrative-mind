/* Narrative Mind v3.1 — Frontend types (exactly matching backend API) */

// =========================================================================
// API response shapes
// =========================================================================

export interface OrchestratorResponse {
  success: boolean;
  message: string;
  scene_analysis?: SceneAnalysis;
  engine_results: {
    character_engine?: CharacterAnalysis;
    world_engine?: WorldValidation;
  };
  guardian_output?: GuardianOutput;
  extracted_entities?: ExtractedEntities;
}

export interface SceneAnalysis {
  characters: string[];
  locations: string[];
  event_prediction: string;
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
  alarm_level: 'info' | 'warn' | 'critical';
  conflicts: Conflict[];
  action_required: 'none' | 'review' | 'block';
}

export interface Conflict {
  dimension: string;
  level: 'info' | 'warn' | 'critical';
  detail: string;
  suggestion?: string;
}

export interface ExtractedEntities {
  characters: { found: string[]; created: string[]; existing: string[] };
  locations: { found: string[]; created: string[]; existing: string[] };
  updated_settings?: { characters: string[]; locations: string[] };
}

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

export const EMPTY_SETTINGS: ProjectSettings = {
  characters: [],
  locations: [],
  power_system: {
    name: '通用力量体系',
    levels: [{ name: '普通人', capabilities: ['基础体能', '日常技能'] }],
    rules: [],
  },
};

// =========================================================================
// Analysis history
// =========================================================================

export interface AnalysisHistoryEntry {
  id: string;
  timestamp: Date;
  characterId: string;
  location: string;
  chapterId: string;
  response: OrchestratorResponse;
}

// =========================================================================
// API request
// =========================================================================

export interface OrchestratorRequest {
  type: 'analyze' | 'check' | 'predict' | 'finalize';
  payload: Record<string, unknown>;
  project_id?: string;
}

// =========================================================================
// App state
// =========================================================================

export type RightTab = 'analysis' | 'history' | 'compare' | 'references';

export interface AppState {
  projects: ProjectMeta[];
  activeProjectId: string | null;
  projectSettings: ProjectSettings | null;
  chapters: Chapter[];
  activeChapterId: string | null;
  selectedCharacterId: string;
  selectedLocation: string;
  currentAnalysis: OrchestratorResponse | null;
  analysisHistory: AnalysisHistoryEntry[];
  isAnalyzing: boolean;
  analysisError: string | null;
  activeRightTab: RightTab;
  compareSlotA: AnalysisHistoryEntry | null;
  compareSlotB: AnalysisHistoryEntry | null;
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  showProjectSettings: boolean;
  costData: { currentMonth: number; monthlyBudget: number; breakdown: { category: string; cost: number }[] };
  apiConnected: boolean;
}

// =========================================================================
// App actions
// =========================================================================

export type AppAction =
  | { type: 'SET_PROJECTS'; payload: ProjectMeta[] }
  | { type: 'SET_ACTIVE_PROJECT'; payload: string }
  | { type: 'SET_PROJECT_SETTINGS'; payload: ProjectSettings }
  | { type: 'ADD_PROJECT'; payload: ProjectMeta }
  | { type: 'REMOVE_PROJECT'; payload: string }
  | { type: 'TOGGLE_PROJECT_SETTINGS' }
  | { type: 'RETURN_TO_DASHBOARD' }
  | { type: 'SET_CHAPTERS'; payload: Chapter[] }
  | { type: 'ADD_CHAPTER'; payload: Chapter }
  | { type: 'SELECT_CHAPTER'; payload: string }
  | { type: 'UPDATE_CHAPTER_TITLE'; payload: { id: string; title: string } }
  | { type: 'UPDATE_CHAPTER_TEXT'; payload: { id: string; text: string } }
  | { type: 'DELETE_CHAPTER'; payload: string }
  | { type: 'SELECT_CHARACTER'; payload: string }
  | { type: 'SELECT_LOCATION'; payload: string }
  | { type: 'ANALYSIS_START' }
  | { type: 'ANALYSIS_SUCCESS'; payload: OrchestratorResponse }
  | { type: 'ANALYSIS_FAILURE'; payload: string }
  | { type: 'LOAD_ANALYSIS_HISTORY'; payload: AnalysisRecord[] }
  | { type: 'SELECT_COMPARE_SLOT'; payload: { slot: 'A' | 'B'; entryId: string } }
  | { type: 'CLEAR_COMPARE' }
  | { type: 'SELECT_TAB'; payload: RightTab }
  | { type: 'SELECT_HISTORY_ENTRY'; payload: string }
  | { type: 'TOGGLE_LEFT_PANEL' }
  | { type: 'TOGGLE_RIGHT_PANEL' }
  | { type: 'SET_API_STATUS'; payload: boolean };

// =========================================================================
// Analysis records (for history persistence)
// =========================================================================

export interface AnalysisRecord {
  analysis_id: string;
  timestamp: string;
  character_id: string;
  location: string;
  response_summary: {
    message: string;
    character_confidence?: number;
    pad_state?: { pleasure: number; arousal: number; dominance: number };
    predicted_action?: string;
    alarm_level: string;
    conflict_count: number;
    needs_human_review: boolean;
  };
}
