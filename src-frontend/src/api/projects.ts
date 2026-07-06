/**
 * 项目 API — Tauri IPC invoke 封装
 *
 * 每个函数对应 Rust xmgl-tauri commands.rs 中的一个 #[tauri::command]。
 */

import { invoke } from "@tauri-apps/api/core";
import type { ProjectMeta } from "../types";
export type { ProjectMeta };

/** 列出所有项目（按更新时间降序）。 */
export async function listProjects(): Promise<ProjectMeta[]> {
  return invoke<ProjectMeta[]>("list_projects");
}

/** 创建新项目。 */
export async function createProject(name: string): Promise<ProjectMeta> {
  return invoke<ProjectMeta>("create_project", { name });
}

/** 获取单个项目。 */
export async function getProject(id: string): Promise<ProjectMeta | null> {
  return invoke<ProjectMeta | null>("get_project", { id });
}

/** 删除项目（级联删除其下所有章节）。 */
export async function deleteProject(id: string): Promise<void> {
  return invoke<void>("delete_project", { id });
}
