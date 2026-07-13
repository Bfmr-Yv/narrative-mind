/**
 * 实体 CRUD API — Phase L1
 *
 * 封装 Tauri IPC invoke() 调用，与 Rust commands.rs 对齐。
 */

import { invoke } from "@tauri-apps/api/core";
import type {
  Character,
  CharacterRelation,
  ForeshadowEntry,
  Location,
  ProjectContext,
  TimelineEvent,
} from "../types";

// ── 角色 ──

export async function listCharacters(projectId: string): Promise<Character[]> {
  return invoke<Character[]>("list_characters", { projectId });
}

export async function getCharacter(id: string): Promise<Character | null> {
  return invoke<Character | null>("get_character", { id });
}

export async function createCharacter(character: Character): Promise<void> {
  return invoke<void>("create_character", { character });
}

export async function updateCharacter(character: Character): Promise<void> {
  return invoke<void>("update_character", { character });
}

export async function deleteCharacter(id: string): Promise<void> {
  return invoke<void>("delete_character", { id });
}

// ── 地点 ──

export async function listLocations(projectId: string): Promise<Location[]> {
  return invoke<Location[]>("list_locations", { projectId });
}

export async function getLocation(id: string): Promise<Location | null> {
  return invoke<Location | null>("get_location", { id });
}

export async function createLocation(location: Location): Promise<void> {
  return invoke<void>("create_location", { location });
}

export async function updateLocation(location: Location): Promise<void> {
  return invoke<void>("update_location", { location });
}

export async function deleteLocation(id: string): Promise<void> {
  return invoke<void>("delete_location", { id });
}

// ── 伏笔 ──

export async function listForeshadows(projectId: string): Promise<ForeshadowEntry[]> {
  return invoke<ForeshadowEntry[]>("list_foreshadows", { projectId });
}

export async function getForeshadow(id: string): Promise<ForeshadowEntry | null> {
  return invoke<ForeshadowEntry | null>("get_foreshadow", { id });
}

export async function createForeshadow(entry: ForeshadowEntry): Promise<void> {
  return invoke<void>("create_foreshadow", { entry });
}

export async function updateForeshadow(entry: ForeshadowEntry): Promise<void> {
  return invoke<void>("update_foreshadow", { entry });
}

export async function deleteForeshadow(id: string): Promise<void> {
  return invoke<void>("delete_foreshadow", { id });
}

// ── 时间线（只读） ──

export async function listTimeline(projectId: string): Promise<TimelineEvent[]> {
  return invoke<TimelineEvent[]>("list_timeline", { projectId });
}

// ── 项目设置 ──

export async function listProjectSettings(projectId: string): Promise<[string, string][]> {
  return invoke<[string, string][]>("list_project_settings", { projectId });
}

export async function setProjectSetting(projectId: string, key: string, value: string): Promise<void> {
  return invoke<void>("set_project_setting", { projectId, key, value });
}

export async function deleteProjectSetting(projectId: string, key: string): Promise<void> {
  return invoke<void>("delete_project_setting", { projectId, key });
}

// ── ProjectContext ──

export async function getProjectContext(projectId: string): Promise<ProjectContext | null> {
  return invoke<ProjectContext | null>("get_project_context", { projectId });
}

export async function saveProjectContext(
  context: ProjectContext,
  expectedVersion?: number,
): Promise<ProjectContext> {
  return invoke<ProjectContext>("save_project_context", {
    context,
    expectedVersion: expectedVersion ?? null,
  });
}
