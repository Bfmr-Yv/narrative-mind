import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import type {
  AppState, AppAction, Chapter, ProjectMeta, ProjectSettings,
  OrchestratorResponse, AnalysisHistoryEntry, AnalysisRecord, RightTab,
} from '../types';
import { EMPTY_SETTINGS } from '../types';
import { apiClient } from '../api/client';

// =========================================================================
// Initial state
// =========================================================================

const initialState: AppState = {
  projects: [],
  activeProjectId: null,
  projectSettings: null,
  chapters: [],
  activeChapterId: null,
  selectedCharacterId: '',
  selectedLocation: '',
  currentAnalysis: null,
  analysisHistory: [],
  isAnalyzing: false,
  padLoading: false,
  padCharacterId: '',
  analysisError: null,
  activeRightTab: 'analysis',
  compareSlotA: null,
  compareSlotB: null,
  leftPanelOpen: true,
  rightPanelOpen: true,
  showProjectSettings: false,
  costData: { currentMonth: 0, monthlyBudget: 20, breakdown: [] },
  apiConnected: false,
};

// =========================================================================
// Helper: merge characters/locations from analysis into settings
// =========================================================================

function mergeDiscoveredEntities(state: AppState, response: OrchestratorResponse): {
  settings: ProjectSettings | null;
  chars: string[];
  locs: string[];
} {
  const base = state.projectSettings || EMPTY_SETTINGS;
  const sa = response.scene_analysis;
  const eu = response.extracted_entities?.updated_settings;

  // Collect from all sources
  const fromSA = { chars: sa?.characters ?? [], locs: sa?.locations ?? [] };
  const fromEU = { chars: eu?.characters ?? [], locs: eu?.locations ?? [] };

  const mergedChars = Array.from(new Set([...base.characters, ...fromSA.chars, ...fromEU.chars]));
  const mergedLocs = Array.from(new Set([...base.locations, ...fromSA.locs, ...fromEU.locs]));

  const changed = mergedChars.length !== base.characters.length || mergedLocs.length !== base.locations.length;

  return {
    settings: changed ? { ...base, characters: mergedChars, locations: mergedLocs } : state.projectSettings,
    chars: mergedChars,
    locs: mergedLocs,
  };
}

// =========================================================================
// Reducer
// =========================================================================

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {

    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };

    case 'SET_ACTIVE_PROJECT':
      return {
        ...state, activeProjectId: action.payload,
        chapters: [], activeChapterId: null,
        currentAnalysis: null, analysisHistory: [],
        analysisError: null, activeRightTab: 'analysis',
      };

    case 'SET_PROJECT_SETTINGS': {
      const settings = action.payload;
      return {
        ...state, projectSettings: settings,
        selectedCharacterId: settings.characters[0] || state.selectedCharacterId || '',
        selectedLocation: settings.locations[0] || state.selectedLocation || '',
      };
    }

    case 'ADD_PROJECT':
      return { ...state, projects: [action.payload, ...state.projects] };

    case 'REMOVE_PROJECT':
      return { ...state, projects: state.projects.filter(p => p.id !== action.payload) };

    case 'TOGGLE_PROJECT_SETTINGS':
      return { ...state, showProjectSettings: !state.showProjectSettings };

    case 'RETURN_TO_DASHBOARD':
      return { ...initialState, projects: state.projects, apiConnected: state.apiConnected, costData: state.costData };

    case 'SET_CHAPTERS':
      return { ...state, chapters: action.payload };

    case 'ADD_CHAPTER':
      return { ...state, chapters: [...state.chapters, action.payload], activeChapterId: action.payload.id };

    case 'SELECT_CHAPTER':
      return { ...state, activeChapterId: action.payload, currentAnalysis: null, analysisError: null };

    case 'UPDATE_CHAPTER_TITLE':
      return { ...state, chapters: state.chapters.map(ch =>
        ch.id === action.payload.id ? { ...ch, title: action.payload.title } : ch) };

    case 'UPDATE_CHAPTER_TEXT':
      return { ...state, chapters: state.chapters.map(ch =>
        ch.id === action.payload.id ? { ...ch, text: action.payload.text } : ch) };

    case 'DELETE_CHAPTER': {
      if (state.chapters.length <= 1) return state;
      const filtered = state.chapters.filter(ch => ch.id !== action.payload);
      return { ...state, chapters: filtered,
        activeChapterId: state.activeChapterId === action.payload ? filtered[0]?.id ?? null : state.activeChapterId };
    }

    case 'SELECT_CHARACTER':
      return { ...state, selectedCharacterId: action.payload };

    case 'SELECT_LOCATION':
      return { ...state, selectedLocation: action.payload };

    case 'ANALYSIS_START':
      return { ...state, isAnalyzing: true, analysisError: null };

    case 'ANALYSIS_SUCCESS': {
      const response = action.payload;
      const entry: AnalysisHistoryEntry = {
        id: `hist-${Date.now()}`,
        timestamp: new Date(),
        characterId: state.selectedCharacterId,
        location: state.selectedLocation,
        chapterId: state.activeChapterId || '',
        response,
      };
      // Merge discovered entities into project settings
      const merged = mergeDiscoveredEntities(state, response);
      // Auto-select first character if none selected
      const autoChar = (!state.selectedCharacterId && merged.chars.length > 0)
        ? merged.chars[0] : state.selectedCharacterId;
      return {
        ...state,
        isAnalyzing: false,
        padCharacterId: state.selectedCharacterId,
        currentAnalysis: response,
        analysisHistory: [entry, ...state.analysisHistory],
        analysisError: null,
        projectSettings: merged.settings,
        selectedCharacterId: autoChar,
      };
    }

    case 'ANALYSIS_FAILURE':
      return { ...state, isAnalyzing: false, analysisError: action.payload };

    case 'PAD_LOADING':
      return { ...state, padLoading: true };

    case 'UPDATE_CHARACTER_PAD': {
      if (!state.currentAnalysis) return state;
      const cr = action.payload;
      return {
        ...state,
        padLoading: false,
        padCharacterId: state.selectedCharacterId,
        currentAnalysis: {
          ...state.currentAnalysis,
          engine_results: {
            ...state.currentAnalysis.engine_results,
            character_engine: cr,
          },
        },
      };
    }

    case 'LOAD_ANALYSIS_HISTORY': {
      const entries: AnalysisHistoryEntry[] = action.payload.map(r => ({
        id: r.analysis_id, timestamp: new Date(r.timestamp),
        characterId: r.character_id, location: r.location,
        chapterId: '', response: r.response_summary as unknown as OrchestratorResponse,
      }));
      const existingIds = new Set(state.analysisHistory.map(e => e.id));
      return { ...state, analysisHistory: [...entries.filter(e => !existingIds.has(e.id)), ...state.analysisHistory] };
    }

    case 'SELECT_COMPARE_SLOT': {
      const entry = state.analysisHistory.find(e => e.id === action.payload.entryId) || null;
      return action.payload.slot === 'A'
        ? { ...state, compareSlotA: entry, activeRightTab: 'compare' }
        : { ...state, compareSlotB: entry, activeRightTab: 'compare' };
    }

    case 'CLEAR_COMPARE':
      return { ...state, compareSlotA: null, compareSlotB: null };

    case 'SELECT_TAB':
      return { ...state, activeRightTab: action.payload };

    case 'SELECT_HISTORY_ENTRY': {
      const entry = state.analysisHistory.find(e => e.id === action.payload);
      return entry ? { ...state, currentAnalysis: entry.response, activeRightTab: 'analysis' } : state;
    }

    case 'TOGGLE_LEFT_PANEL':
      return { ...state, leftPanelOpen: !state.leftPanelOpen };

    case 'TOGGLE_RIGHT_PANEL':
      return { ...state, rightPanelOpen: !state.rightPanelOpen };

    case 'SET_API_STATUS':
      return { ...state, apiConnected: action.payload };

    default:
      return state;
  }
}

// =========================================================================
// Context
// =========================================================================

interface AppContextValue { state: AppState; dispatch: React.Dispatch<AppAction>; }
const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    apiClient.listProjects().then(p => dispatch({ type: 'SET_PROJECTS', payload: p })).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try { await apiClient.checkHealth(); if (!cancelled) dispatch({ type: 'SET_API_STATUS', payload: true }); }
      catch { if (!cancelled) dispatch({ type: 'SET_API_STATUS', payload: false }); }
    }
    check();
    const interval = setInterval(check, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppProvider');
  return ctx;
}

// =========================================================================
// Composite actions
// =========================================================================

export function useAppActions() {
  const { state, dispatch } = useAppContext();

  const createProject = useCallback(async (name: string) => {
    const proj = await apiClient.createProject(name);
    dispatch({ type: 'ADD_PROJECT', payload: proj });
    return proj;
  }, [dispatch]);

  const enterProject = useCallback(async (projectId: string) => {
    dispatch({ type: 'SET_ACTIVE_PROJECT', payload: projectId });
    try {
      const settings = await apiClient.getProjectSettings(projectId);
      dispatch({ type: 'SET_PROJECT_SETTINGS', payload: settings });
    } catch { /* defaults */ }
    try {
      const chapters = await apiClient.listChapters(projectId);
      dispatch({ type: 'SET_CHAPTERS', payload: chapters });
      if (chapters.length > 0) {
        dispatch({ type: 'SELECT_CHAPTER', payload: chapters[0].id });
        apiClient.getAnalysisHistory(projectId, chapters[0].id).then(r => {
          dispatch({ type: 'LOAD_ANALYSIS_HISTORY', payload: r });
        }).catch(() => {});
      }
    } catch { /* no chapters */ }
  }, [dispatch]);

  const deleteProject = useCallback(async (id: string) => {
    await apiClient.deleteProject(id);
    dispatch({ type: 'REMOVE_PROJECT', payload: id });
  }, [dispatch]);

  const returnToDashboard = useCallback(() => {
    apiClient.listProjects().then(p => dispatch({ type: 'SET_PROJECTS', payload: p })).catch(() => {});
    dispatch({ type: 'RETURN_TO_DASHBOARD' });
  }, [dispatch]);

  const saveSettings = useCallback(async (settings: ProjectSettings) => {
    if (!state.activeProjectId) return;
    await apiClient.saveProjectSettings(state.activeProjectId, settings);
    dispatch({ type: 'SET_PROJECT_SETTINGS', payload: settings });
  }, [state.activeProjectId, dispatch]);

  const addChapter = useCallback(async (title?: string) => {
    if (!state.activeProjectId) return;
    const ch = await apiClient.createChapter(state.activeProjectId, title || '新章节');
    dispatch({ type: 'ADD_CHAPTER', payload: ch });
  }, [state.activeProjectId, dispatch]);

  const saveChapter = useCallback(async (id: string, title: string, text: string) => {
    if (!state.activeProjectId) return;
    await apiClient.saveChapter(state.activeProjectId, id, title, text);
  }, [state.activeProjectId]);

  const deleteChapter = useCallback(async (id: string) => {
    if (!state.activeProjectId) return;
    await apiClient.deleteChapter(state.activeProjectId, id);
    dispatch({ type: 'DELETE_CHAPTER', payload: id });
  }, [state.activeProjectId, dispatch]);

  const runAnalysis = useCallback(async () => {
    const chapter = state.chapters.find(ch => ch.id === state.activeChapterId);
    if (!chapter || !chapter.text.trim()) return;
    dispatch({ type: 'ANALYSIS_START' });
    try {
      const result = await apiClient.executeOrchestrator({
        type: 'analyze',
        payload: {
          character_id: state.selectedCharacterId,
          scene_text: chapter.text,
          event_description: chapter.text.slice(0, 1500),
          location: state.selectedLocation,
          involved_characters: state.selectedCharacterId ? [state.selectedCharacterId] : [],
        },
        project_id: state.activeProjectId || undefined,
      });
      dispatch({ type: 'ANALYSIS_SUCCESS', payload: result });
      // Persist to server (fire-and-forget)
      if (state.activeProjectId && state.activeChapterId) {
        apiClient.saveAnalysis(state.activeProjectId, state.activeChapterId, {
          character_id: state.selectedCharacterId,
          location: state.selectedLocation,
          response: result,
        }).catch(() => {});
      }
    } catch (err) {
      dispatch({ type: 'ANALYSIS_FAILURE', payload: err instanceof Error ? err.message : '分析请求失败' });
    }
  }, [state.chapters, state.activeChapterId, state.selectedCharacterId, state.selectedLocation, state.activeProjectId, dispatch]);

  const selectChapter = useCallback((id: string) => {
    dispatch({ type: 'SELECT_CHAPTER', payload: id });
    if (state.activeProjectId) {
      apiClient.getAnalysisHistory(state.activeProjectId, id).then(r => {
        dispatch({ type: 'LOAD_ANALYSIS_HISTORY', payload: r });
      }).catch(() => {});
    }
  }, [state.activeProjectId, dispatch]);

  return {
    state,
    createProject, enterProject, deleteProject, returnToDashboard,
    saveSettings, addChapter, saveChapter, deleteChapter, runAnalysis, selectChapter,
    updateChapterTitle: (id: string, title: string) => dispatch({ type: 'UPDATE_CHAPTER_TITLE', payload: { id, title } }),
    updateChapterText: (id: string, text: string) => dispatch({ type: 'UPDATE_CHAPTER_TEXT', payload: { id, text } }),
    selectCharacter: async (charId: string) => {
      dispatch({ type: 'SELECT_CHARACTER', payload: charId });
      // Auto-refetch PAD for the newly selected character
      const chapter = state.chapters.find(ch => ch.id === state.activeChapterId);
      if (charId && chapter?.text && state.currentAnalysis) {
        dispatch({ type: 'PAD_LOADING' });
        try {
          const cr = await apiClient.analyzeCharacter({
            character_id: charId,
            scene_text: chapter.text,
          });
          dispatch({ type: 'UPDATE_CHARACTER_PAD', payload: cr });
        } catch {
          // PAD re-fetch failed — keep showing old PAD
          dispatch({ type: 'UPDATE_CHARACTER_PAD', payload: state.currentAnalysis.engine_results.character_engine! });
        }
      }
    },
    selectLocation: (loc: string) => dispatch({ type: 'SELECT_LOCATION', payload: loc }),
    selectTab: (tab: RightTab) => dispatch({ type: 'SELECT_TAB', payload: tab }),
    selectHistoryEntry: (id: string) => dispatch({ type: 'SELECT_HISTORY_ENTRY', payload: id }),
    toggleLeftPanel: () => dispatch({ type: 'TOGGLE_LEFT_PANEL' }),
    toggleRightPanel: () => dispatch({ type: 'TOGGLE_RIGHT_PANEL' }),
    toggleProjectSettings: () => dispatch({ type: 'TOGGLE_PROJECT_SETTINGS' }),
  };
}
