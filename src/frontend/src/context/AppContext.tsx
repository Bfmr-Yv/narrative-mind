import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import type {
  AppState,
  AppAction,
  Chapter,
  ProjectMeta,
  ProjectSettings,
  OrchestratorResponse,
  AnalysisHistoryEntry,
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
  analysisError: null,

  activeRightTab: 'analysis',
  leftPanelOpen: true,
  rightPanelOpen: true,
  showProjectSettings: false,

  costData: { currentMonth: 0, monthlyBudget: 20, breakdown: [] },
  apiConnected: false,
};

// =========================================================================
// Reducer
// =========================================================================

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {

    // ---- Project management ----
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };

    case 'SET_ACTIVE_PROJECT': {
      // Entering editor — reset editor state
      return {
        ...state,
        activeProjectId: action.payload,
        chapters: [],
        activeChapterId: null,
        currentAnalysis: null,
        analysisHistory: [],
        analysisError: null,
        activeRightTab: 'analysis',
      };
    }

    case 'SET_PROJECT_SETTINGS':
      return {
        ...state,
        projectSettings: action.payload,
        selectedCharacterId: action.payload.characters[0] || '',
        selectedLocation: action.payload.locations[0] || '',
      };

    case 'ADD_PROJECT':
      return { ...state, projects: [action.payload, ...state.projects] };

    case 'REMOVE_PROJECT':
      return { ...state, projects: state.projects.filter(p => p.id !== action.payload) };

    case 'TOGGLE_PROJECT_SETTINGS':
      return { ...state, showProjectSettings: !state.showProjectSettings };

    case 'RETURN_TO_DASHBOARD':
      return {
        ...initialState,
        projects: state.projects,
        apiConnected: state.apiConnected,
        costData: state.costData,
      };

    // ---- Chapters ----
    case 'SET_CHAPTERS':
      return { ...state, chapters: action.payload };

    case 'ADD_CHAPTER':
      return {
        ...state,
        chapters: [...state.chapters, action.payload],
        activeChapterId: action.payload.id,
      };

    case 'SELECT_CHAPTER':
      return { ...state, activeChapterId: action.payload };

    case 'UPDATE_CHAPTER_TITLE':
      return {
        ...state,
        chapters: state.chapters.map(ch =>
          ch.id === action.payload.id ? { ...ch, title: action.payload.title } : ch
        ),
      };

    case 'UPDATE_CHAPTER_TEXT':
      return {
        ...state,
        chapters: state.chapters.map(ch =>
          ch.id === action.payload.id ? { ...ch, text: action.payload.text } : ch
        ),
      };

    case 'DELETE_CHAPTER': {
      if (state.chapters.length <= 1) return state;
      const filtered = state.chapters.filter(ch => ch.id !== action.payload);
      return {
        ...state,
        chapters: filtered,
        activeChapterId: state.activeChapterId === action.payload ? filtered[0]?.id ?? null : state.activeChapterId,
      };
    }

    // ---- Selection ----
    case 'SELECT_CHARACTER':
      return { ...state, selectedCharacterId: action.payload };
    case 'SELECT_LOCATION':
      return { ...state, selectedLocation: action.payload };

    // ---- Analysis ----
    case 'ANALYSIS_START':
      return { ...state, isAnalyzing: true, analysisError: null };

    case 'ANALYSIS_SUCCESS': {
      const entry: AnalysisHistoryEntry = {
        id: `hist-${Date.now()}`,
        timestamp: new Date(),
        characterId: state.selectedCharacterId,
        location: state.selectedLocation,
        chapterId: state.activeChapterId || '',
        response: action.payload,
      };
      return {
        ...state,
        isAnalyzing: false,
        currentAnalysis: action.payload,
        analysisHistory: [entry, ...state.analysisHistory],
        analysisError: null,
        costData: {
          ...state.costData,
          currentMonth: state.costData.currentMonth + 0.01,
          breakdown: [...state.costData.breakdown, { category: '章节分析 (Tier 1)', cost: 0.01 }],
        },
      };
    }

    case 'ANALYSIS_FAILURE':
      return { ...state, isAnalyzing: false, analysisError: action.payload };

    // ---- UI ----
    case 'SELECT_TAB':
      return { ...state, activeRightTab: action.payload };

    case 'SELECT_HISTORY_ENTRY': {
      const entry = state.analysisHistory.find(e => e.id === action.payload);
      if (!entry) return state;
      return { ...state, currentAnalysis: entry.response, activeRightTab: 'analysis' };
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

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Load projects on mount
  useEffect(() => {
    apiClient.listProjects().then(projects => {
      dispatch({ type: 'SET_PROJECTS', payload: projects });
    }).catch(() => {});
  }, []);

  // Check API health
  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        await apiClient.checkHealth();
        if (!cancelled) dispatch({ type: 'SET_API_STATUS', payload: true });
      } catch {
        if (!cancelled) dispatch({ type: 'SET_API_STATUS', payload: false });
      }
    }
    check();
    const interval = setInterval(check, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppProvider');
  return ctx;
}

// =========================================================================
// Composite actions (async, multi-step)
// =========================================================================

export function useAppActions() {
  const { state, dispatch } = useAppContext();

  // --- Project actions ---

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
    } catch { /* use defaults */ }
    try {
      const chapters = await apiClient.listChapters(projectId);
      dispatch({ type: 'SET_CHAPTERS', payload: chapters });
      if (chapters.length > 0) {
        dispatch({ type: 'SELECT_CHAPTER', payload: chapters[0].id });
      }
    } catch { /* no chapters yet */ }
  }, [dispatch]);

  const deleteProject = useCallback(async (projectId: string) => {
    await apiClient.deleteProject(projectId);
    dispatch({ type: 'REMOVE_PROJECT', payload: projectId });
  }, [dispatch]);

  const returnToDashboard = useCallback(() => {
    apiClient.listProjects().then(projects => {
      dispatch({ type: 'SET_PROJECTS', payload: projects });
    }).catch(() => {});
    dispatch({ type: 'RETURN_TO_DASHBOARD' });
  }, [dispatch]);

  // --- Settings ---

  const saveSettings = useCallback(async (settings: ProjectSettings) => {
    if (!state.activeProjectId) return;
    await apiClient.saveProjectSettings(state.activeProjectId, settings);
    dispatch({ type: 'SET_PROJECT_SETTINGS', payload: settings });
  }, [state.activeProjectId, dispatch]);

  // --- Chapter actions ---

  const addChapter = useCallback(async (title?: string) => {
    if (!state.activeProjectId) return;
    const ch = await apiClient.createChapter(state.activeProjectId, title || '新章节');
    dispatch({ type: 'ADD_CHAPTER', payload: ch });
  }, [state.activeProjectId, dispatch]);

  const saveChapter = useCallback(async (chapterId: string, title: string, text: string) => {
    if (!state.activeProjectId) return;
    await apiClient.saveChapter(state.activeProjectId, chapterId, title, text);
  }, [state.activeProjectId]);

  const deleteChapter = useCallback(async (chapterId: string) => {
    if (!state.activeProjectId) return;
    await apiClient.deleteChapter(state.activeProjectId, chapterId);
    dispatch({ type: 'DELETE_CHAPTER', payload: chapterId });
  }, [state.activeProjectId, dispatch]);

  // --- Analysis ---

  const runAnalysis = useCallback(async () => {
    const chapter = state.chapters.find(ch => ch.id === state.activeChapterId);
    if (!chapter || !chapter.text.trim()) return;

    dispatch({ type: 'ANALYSIS_START' });
    try {
      const payload: Record<string, unknown> = {
        character_id: state.selectedCharacterId,
        scene_text: chapter.text,
        event_description: chapter.text.slice(0, 1500),
        location: state.selectedLocation,
        involved_characters: state.selectedCharacterId ? [state.selectedCharacterId] : [],
      };
      const result = await apiClient.executeOrchestrator({
        type: 'analyze',
        payload,
        project_id: state.activeProjectId || undefined,
      });
      dispatch({ type: 'ANALYSIS_SUCCESS', payload: result });
    } catch (err) {
      dispatch({ type: 'ANALYSIS_FAILURE', payload: err instanceof Error ? err.message : '分析请求失败' });
    }
  }, [state.chapters, state.activeChapterId, state.selectedCharacterId, state.selectedLocation, state.activeProjectId, dispatch]);

  // --- Simple dispatches ---
  const selectChapter = useCallback((id: string) => dispatch({ type: 'SELECT_CHAPTER', payload: id }), [dispatch]);
  const updateChapterTitle = useCallback((id: string, title: string) => dispatch({ type: 'UPDATE_CHAPTER_TITLE', payload: { id, title } }), [dispatch]);
  const updateChapterText = useCallback((id: string, text: string) => dispatch({ type: 'UPDATE_CHAPTER_TEXT', payload: { id, text } }), [dispatch]);
  const selectCharacter = useCallback((id: string) => dispatch({ type: 'SELECT_CHARACTER', payload: id }), [dispatch]);
  const selectLocation = useCallback((loc: string) => dispatch({ type: 'SELECT_LOCATION', payload: loc }), [dispatch]);
  const selectTab = useCallback((tab: AppState['activeRightTab']) => dispatch({ type: 'SELECT_TAB', payload: tab }), [dispatch]);
  const selectHistoryEntry = useCallback((id: string) => dispatch({ type: 'SELECT_HISTORY_ENTRY', payload: id }), [dispatch]);
  const toggleLeftPanel = useCallback(() => dispatch({ type: 'TOGGLE_LEFT_PANEL' }), [dispatch]);
  const toggleRightPanel = useCallback(() => dispatch({ type: 'TOGGLE_RIGHT_PANEL' }), [dispatch]);
  const toggleProjectSettings = useCallback(() => dispatch({ type: 'TOGGLE_PROJECT_SETTINGS' }), [dispatch]);

  return {
    state,
    createProject,
    enterProject,
    deleteProject,
    returnToDashboard,
    saveSettings,
    addChapter,
    saveChapter,
    deleteChapter,
    runAnalysis,
    selectChapter,
    updateChapterTitle,
    updateChapterText,
    selectCharacter,
    selectLocation,
    selectTab,
    selectHistoryEntry,
    toggleLeftPanel,
    toggleRightPanel,
    toggleProjectSettings,
  };
}
