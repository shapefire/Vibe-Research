import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useApiQuery } from "../useApiQuery";
import { ApiError } from "@/lib/api";

describe("useApiQuery", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads data on mount when enabled", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(() => useApiQuery(fetcher, []));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.done).toBe(true));
    expect(result.current.data).toEqual({ ok: true });
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("sets error on ApiError", async () => {
    const fetcher = vi.fn().mockRejectedValue(new ApiError("连接不到后端", 0));
    const { result } = renderHook(() => useApiQuery(fetcher, []));
    await waitFor(() => expect(result.current.done).toBe(true));
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("连接不到后端");
  });

  it("does not fetch when enabled=false", async () => {
    const fetcher = vi.fn().mockResolvedValue("x");
    const { result } = renderHook(() => useApiQuery(fetcher, [], { enabled: false }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetcher).not.toHaveBeenCalled();
    expect(result.current.done).toBe(false);
  });

  it("refetch updates data", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce("first")
      .mockResolvedValueOnce("second");
    const { result } = renderHook(() => useApiQuery(fetcher, []));
    await waitFor(() => expect(result.current.data).toBe("first"));
    await act(async () => { await result.current.refetch(); });
    expect(result.current.data).toBe("second");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("discards stale response on race", async () => {
    let resolveSlow: (v: string) => void;
    const slow = new Promise<string>((r) => { resolveSlow = r; });
    const fetcher = vi.fn()
      .mockReturnValueOnce(slow)
      .mockResolvedValueOnce("fast");
    const { result } = renderHook(() => useApiQuery(fetcher, []));
    await act(async () => { await result.current.refetch(); });
    await waitFor(() => expect(result.current.data).toBe("fast"));
    resolveSlow!("slow");
    await waitFor(() => expect(result.current.data).toBe("fast"));
  });

  it("re-fetches when deps change", async () => {
    const fetcher = vi.fn().mockResolvedValue("a");
    let dep = 1;
    const { result, rerender } = renderHook(() => useApiQuery(fetcher, [dep]));
    await waitFor(() => expect(result.current.done).toBe(true));
    expect(fetcher).toHaveBeenCalledTimes(1);
    dep = 2;
    rerender();
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  });
});
