import type {
  CharacterAnalysis,
  WorldValidation,
  GuardianOutput,
  OrchestratorRequest,
  OrchestratorResponse,
  ProjectMeta,
  ProjectSettings,
  Chapter,
  AnalysisRecord,
  AnalysisRecordFull,
} from '../types';

const API_BASE_URL = '/api';

interface HealthResponse {
  status: string;
  slices_loaded: number;
  vocabulary_size: number;
}

class ApiClient {
  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options?.headers },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error((err as any).error || `API error: ${response.status}`);
    }
    return response.json();
  }

  // ---- Existing ----

  async analyzeCharacter(req: { character_id: string; scene_text: string }): Promise<CharacterAnalysis> {
    return this.fetch('/character/analyze', { method: 'POST', body: JSON.stringify(req) });
  }

  async validateWorld(req: { event_description: string; location: string; involved_characters: string[] }): Promise<WorldValidation> {
    return this.fetch('/world/validate', { method: 'POST', body: JSON.stringify(req) });
  }

  async checkConsistency(req: { engine_results: Record<string, unknown>; active_dimensions?: string[] }): Promise<GuardianOutput> {
    return this.fetch('/guardian/check', { method: 'POST', body: JSON.stringify(req) });
  }

  async executeOrchestrator(req: OrchestratorRequest): Promise<OrchestratorResponse> {
    return this.fetch('/orchestrator/execute', { method: 'POST', body: JSON.stringify(req) });
  }

  async checkHealth(): Promise<HealthResponse> {
    return this.fetch('/health');
  }

  // ---- Project CRUD ----

  async listProjects(): Promise<ProjectMeta[]> {
    return this.fetch('/projects');
  }

  async createProject(name: string): Promise<ProjectMeta> {
    return this.fetch('/projects', { method: 'POST', body: JSON.stringify({ name }) });
  }

  async getProject(id: string): Promise<ProjectMeta & { settings: ProjectSettings }> {
    return this.fetch(`/projects/${id}`);
  }

  async deleteProject(id: string): Promise<void> {
    return this.fetch(`/projects/${id}`, { method: 'DELETE' });
  }

  async getProjectSettings(id: string): Promise<ProjectSettings> {
    return this.fetch(`/projects/${id}/settings`);
  }

  async saveProjectSettings(id: string, settings: ProjectSettings): Promise<ProjectSettings> {
    return this.fetch(`/projects/${id}/settings`, { method: 'PUT', body: JSON.stringify(settings) });
  }

  // ---- Chapter CRUD ----

  async listChapters(projectId: string): Promise<Chapter[]> {
    return this.fetch(`/projects/${projectId}/chapters`);
  }

  async createChapter(projectId: string, title: string): Promise<Chapter> {
    return this.fetch(`/projects/${projectId}/chapters`, { method: 'POST', body: JSON.stringify({ title }) });
  }

  async saveChapter(projectId: string, chapterId: string, title: string, text: string): Promise<void> {
    return this.fetch(`/projects/${projectId}/chapters/${chapterId}`, {
      method: 'PUT', body: JSON.stringify({ title, text }),
    });
  }

  async deleteChapter(projectId: string, chapterId: string): Promise<void> {
    return this.fetch(`/projects/${projectId}/chapters/${chapterId}`, { method: 'DELETE' });
  }

  // ---- Analysis History (Item 4) ----

  async getAnalysisHistory(projectId: string, chapterId: string): Promise<AnalysisRecord[]> {
    return this.fetch(`/projects/${projectId}/chapters/${chapterId}/analysis`);
  }

  async getAnalysisDetail(projectId: string, chapterId: string, analysisId: string): Promise<AnalysisRecordFull> {
    return this.fetch(`/projects/${projectId}/chapters/${chapterId}/analysis/${analysisId}`);
  }

  async saveAnalysis(projectId: string, chapterId: string, record: {
    character_id: string;
    location: string;
    response: OrchestratorResponse;
  }): Promise<AnalysisRecord> {
    return this.fetch(`/projects/${projectId}/chapters/${chapterId}/analysis`, {
      method: 'POST', body: JSON.stringify(record),
    });
  }
}

export const apiClient = new ApiClient();
