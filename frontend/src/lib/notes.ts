// 研究记录（沉淀）—— 把 AI 复盘 / 今日要点 / 问 AI 的结果存本地服务，形成个人投研记录。
// 数据存 ~/.vibe-research/notes/，不上传、不进仓库。对应投研框架第 7 层「沉淀」。

import { api, type NoteSnapshot } from "./api";

export type { NoteSnapshot };

export interface Note {
  id: string;
  kind: string;   // 复盘 / 今日要点 / 问AI
  title: string;
  content: string; // markdown 正文（列表加载时可能为空，展开后懒加载）
  ts: number;
  tags?: string[];
  snapshot?: NoteSnapshot | null;
}

const KEY = "vr-notes";
const MIGRATED_KEY = "vr-notes-migrated";

function loadLegacyNotes(): Note[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

export async function loadNotes(): Promise<Note[]> {
  const { items } = await api.notes({ limit: 500 });
  return items.map((m) => ({
    id: m.id,
    kind: m.kind,
    title: m.title,
    content: "",
    ts: m.ts,
    tags: m.tags,
    snapshot: m.snapshot,
  }));
}

export async function addNote(
  kind: string,
  title: string,
  content: string,
  snapshot?: NoteSnapshot | null,
  contextCode?: string,
): Promise<Note[]> {
  const tags = new Set<string>();
  if (snapshot?.code) tags.add(snapshot.code);
  if (contextCode && /^\d{6}$/.test(contextCode)) tags.add(contextCode);
  await api.createNote({ kind, title, content, tags: [...tags], snapshot: snapshot ?? undefined });
  return loadNotes();
}

export async function deleteNote(id: string): Promise<Note[]> {
  await api.deleteNote(id);
  return loadNotes();
}

export async function clearNotes(): Promise<void> {
  await api.deleteAllNotes();
}

/** 首次加载时从 localStorage 迁移到服务端（幂等）。返回导入条数，0 表示无需迁移。 */
export async function migrateIfNeeded(): Promise<number> {
  if (localStorage.getItem(MIGRATED_KEY) === "true") return 0;
  const legacy = loadLegacyNotes();
  if (legacy.length === 0) {
    localStorage.setItem(MIGRATED_KEY, "true");
    return 0;
  }
  const result = await api.migrateNotes(legacy);
  if (result.imported > 0 || result.skipped === legacy.length) {
    localStorage.setItem(MIGRATED_KEY, "true");
  }
  return result.imported;
}
