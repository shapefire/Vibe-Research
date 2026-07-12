import { useState, useEffect, useCallback, useRef } from "react";
import { ApiError } from "@/lib/api";

export function useApiQuery<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options?: { enabled?: boolean },
) {
  const enabled = options?.enabled ?? true;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const genRef = useRef(0);

  const run = useCallback(async () => {
    const gen = ++genRef.current;
    setLoading(true);
    setError(null);
    setDone(false);
    try {
      const result = await fetcher();
      if (gen !== genRef.current) return;
      setData(result);
    } catch (e) {
      if (gen !== genRef.current) return;
      setError(e instanceof ApiError ? e.message : "请求失败");
      setData(null);
    } finally {
      if (gen === genRef.current) {
        setLoading(false);
        setDone(true);
      }
    }
  }, [fetcher]);

  useEffect(() => {
    if (enabled) run();
  }, [enabled, run, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, done, refetch: run };
}
