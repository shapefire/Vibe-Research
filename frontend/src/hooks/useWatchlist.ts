import { useState, useEffect, useCallback } from "react";
import { api, type Quote } from "@/lib/api";
import {
  loadWatch,
  addWatchRaw,
  removeWatch,
  migrateIfNeeded,
  aShareSymbols,
  type WatchItem,
} from "@/lib/watchlist";

export function useWatchlist() {
  const [items, setItems] = useState<WatchItem[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const codes = aShareSymbols(items);

  const refresh = useCallback(async (list: WatchItem[]) => {
    const aShare = aShareSymbols(list);
    if (!aShare.length) {
      setQuotes({});
      return;
    }
    setLoading(true);
    try {
      const data = await api.quote(aShare.join(","));
      setQuotes(data);
    } catch {
      /* quote failure shouldn't wipe list */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await migrateIfNeeded();
        const list = await loadWatch();
        if (cancelled) return;
        setItems(list);
        setError(null);
        await refresh(list);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载自选失败");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const add = useCallback(async () => {
    const raw = input;
    if (!raw.trim()) return;
    try {
      const { items: next, added } = await addWatchRaw(raw);
      setItems(next);
      setInput("");
      setError(added ? null : "没识别到新的有效代码（可能已在自选里）");
      await refresh(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "添加失败");
    }
  }, [input, refresh]);

  const remove = useCallback(
    async (c: string) => {
      try {
        const next = await removeWatch(c);
        setItems(next);
        setError(null);
        await refresh(next);
      } catch (e) {
        setError(e instanceof Error ? e.message : "删除失败");
      }
    },
    [refresh],
  );

  return {
    codes,
    items,
    quotes,
    input,
    setInput,
    add: () => void add(),
    remove: (c: string) => void remove(c),
    refresh: () => void refresh(items),
    loading,
    error,
  };
}
