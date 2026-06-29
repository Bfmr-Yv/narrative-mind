/**
 * 章节 API — Tauri IPC invoke 封装
 *
 * 每个函数对应 Rust xmgl-tauri commands.rs 中的一个 #[tauri::command]。
 */

import { invoke } from "@tauri-apps/api/core";
import type { ChapterData } from "../types";

/** 列出项目下所有章节（按 sort_order 升序）。 */
export async function listChapters(projectId: string): Promise<ChapterData[]> {
  return invoke<ChapterData[]>("list_chapters", { projectId });
}

/** 创建新章节（自动生成 ID、sort_order、时间戳、字数统计）。 */
export async function createChapter(
  projectId: string,
  title: string,
  text: string,
): Promise<ChapterData> {
  return invoke<ChapterData>("create_chapter", { projectId, title, text });
}

/** 获取单个章节。 */
export async function getChapter(id: string): Promise<ChapterData | null> {
  return invoke<ChapterData | null>("get_chapter", { id });
}

/** 更新章节（自动刷新 updated_at、重新计算 word_count）。 */
export async function updateChapter(chapter: ChapterData): Promise<void> {
  return invoke<void>("update_chapter", { chapter });
}

/** 删除章节。 */
export async function deleteChapter(id: string): Promise<void> {
  return invoke<void>("delete_chapter", { id });
}
