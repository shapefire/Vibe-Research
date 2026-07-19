// 自选股 —— 服务端 ~/.vibe-research/watchlist.json；localStorage 仅作一次性迁移源。

import { api, type WatchItem, type WatchMarket } from "@/lib/api";

export type { WatchItem, WatchMarket };

const KEY = "vr-watchlist";
const MIGRATED_KEY = "vr-watchlist-migrated";

/** 读旧版 localStorage（仅迁移用）；过滤 6 位 A 股。 */
export function loadLocalWatch(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(v) ? v.filter((c) => /^\d{6}$/.test(c)) : [];
  } catch {
    return [];
  }
}

/** @deprecated 主路径已改 API；保留给测试读旧数据 */
export function loadWatchSync(): string[] {
  return loadLocalWatch();
}

export async function loadWatch(): Promise<WatchItem[]> {
  const res = await api.watchlist();
  return res.items ?? [];
}

export async function addWatchRaw(raw: string): Promise<{ items: WatchItem[]; added: number }> {
  const res = await api.watchlistAdd({ raw });
  return { items: res.items ?? [], added: res.added ?? 0 };
}

export async function removeWatch(symbol: string): Promise<WatchItem[]> {
  const res = await api.watchlistRemove(symbol);
  return res.items ?? [];
}

export async function replaceWatch(items: WatchItem[]): Promise<WatchItem[]> {
  const res = await api.watchlistReplace(items);
  return res.items ?? [];
}

/**
 * 首次启动：若 localStorage 有旧数据且未标记 migrated，则 POST migrate。
 * 仅成功后写 migrated 标记（方案 B / Q-08-09）。
 */
export async function migrateIfNeeded(): Promise<number> {
  if (typeof localStorage === "undefined") return 0;
  if (localStorage.getItem(MIGRATED_KEY)) return 0;
  const codes = loadLocalWatch();
  if (!codes.length) {
    localStorage.setItem(MIGRATED_KEY, "1");
    return 0;
  }
  const res = await api.watchlistMigrate(codes);
  localStorage.setItem(MIGRATED_KEY, "1");
  return res.migrated ?? 0;
}

/** 本地预览解析（不做服务端写入）；多市场粗解析。 */
export function parseCodes(raw: string): string[] {
  const tokens = raw.split(/[\s,，、;；]+/).filter(Boolean);
  const out: string[] = [];
  const seen = new Set<string>();
  for (const t of tokens) {
    const s = t.trim().toUpperCase();
    let sym = "";
    if (/^\d{6}(\.SH|\.SZ)?$/i.test(s)) sym = s.replace(/\.(SH|SZ)$/i, "");
    else if (/^\d{1,5}(\.HK)?$/i.test(s)) {
      const body = s.replace(/\.HK$/i, "");
      sym = body.padStart(5, "0");
    } else if (/^[A-Z]{1,5}$/.test(s)) sym = s;
    else if (/^\d{1,6}\.KS$/i.test(s)) sym = s;
    if (sym && !seen.has(sym)) {
      seen.add(sym);
      out.push(sym);
    }
  }
  return out;
}

/** @deprecated 改用 addWatchRaw；保留兼容旧测试逻辑的本地合并预览 */
export function addCodes(existing: string[], raw: string): { next: string[]; added: number } {
  const incoming = parseCodes(raw).filter((c) => !existing.includes(c));
  return { next: [...existing, ...incoming], added: incoming.length };
}

/** @deprecated 主路径不再写 localStorage */
export function saveWatch(codes: string[]) {
  localStorage.setItem(KEY, JSON.stringify(codes));
}

export function aShareSymbols(items: WatchItem[]): string[] {
  return items.filter((i) => i.market === "a-share").map((i) => i.symbol);
}
