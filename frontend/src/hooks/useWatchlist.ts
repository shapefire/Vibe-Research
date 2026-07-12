import { useState, useEffect, useCallback } from "react";
import { api, type Quote } from "@/lib/api";
import { loadWatch, saveWatch, addCodes } from "@/lib/watchlist";

export function useWatchlist() {
  const [codes, setCodes] = useState<string[]>(loadWatch);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback((list: string[]) => {
    if (!list.length) {
      setQuotes({});
      return;
    }
    setLoading(true);
    api.quote(list.join(","))
      .then(setQuotes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh(loadWatch());
  }, [refresh]);

  const add = useCallback(() => {
    const { next, added } = addCodes(codes, input);
    setInput("");
    if (!added) return;
    setCodes(next);
    saveWatch(next);
    refresh(next);
  }, [codes, input, refresh]);

  const remove = useCallback((c: string) => {
    const next = codes.filter((x) => x !== c);
    setCodes(next);
    saveWatch(next);
    refresh(next);
  }, [codes, refresh]);

  return { codes, quotes, input, setInput, add, remove, refresh: () => refresh(codes), loading };
}
