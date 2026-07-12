import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useAskAi } from "../useAskAi";
import { ApiError } from "@/lib/api";

vi.mock("@/lib/llm", () => ({
  chatStream: vi.fn(),
}));

import { chatStream } from "@/lib/llm";

const mockedChatStream = vi.mocked(chatStream);

describe("useAskAi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("streams deltas via callbacks", async () => {
    mockedChatStream.mockImplementation(async (_h, _c, cb) => {
      cb.onDelta("你好");
      cb.onDelta("世界");
      return { content: "你好世界", trace: [], rounds: 1 };
    });
    const { result } = renderHook(() => useAskAi());
    const deltas: string[] = [];
    await act(async () => {
      await result.current.ask(
        [{ role: "user", content: "hi" }],
        "ctx",
        { onDelta: (t) => deltas.push(t) },
      );
    });
    expect(deltas).toEqual(["你好", "世界"]);
    expect(result.current.streaming).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets error when chatStream throws", async () => {
    mockedChatStream.mockRejectedValue(new ApiError("模型超时", 502));
    const { result } = renderHook(() => useAskAi());
    await act(async () => {
      try {
        await result.current.ask(
          [{ role: "user", content: "q" }],
          "ctx",
          { onDelta: () => {} },
        );
      } catch { /* expected */ }
    });
    expect(result.current.error).toBe("模型超时");
    expect(result.current.streaming).toBe(false);
  });

  it("abort stops streaming without error", async () => {
    mockedChatStream.mockImplementation((_h, _c, _cb, signal) => new Promise((_res, rej) => {
      signal?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
    }));
    const { result } = renderHook(() => useAskAi());
    let askPromise: Promise<void>;
    act(() => {
      askPromise = result.current.ask(
        [{ role: "user", content: "q" }],
        "ctx",
        { onDelta: () => {} },
      );
    });
    await waitFor(() => expect(result.current.streaming).toBe(true));
    act(() => { result.current.abort(); });
    await act(async () => {
      try { await askPromise!; } catch { /* AbortError */ }
    });
    expect(result.current.streaming).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("forwards onTool callbacks", async () => {
    mockedChatStream.mockImplementation(async (_h, _c, cb) => {
      cb.onTool?.("query_quote", { code: "600519" });
      return { content: "", trace: [], rounds: 0 };
    });
    const { result } = renderHook(() => useAskAi());
    const onTool = vi.fn();
    await act(async () => {
      await result.current.ask(
        [{ role: "user", content: "q" }],
        "ctx",
        { onDelta: () => {}, onTool },
      );
    });
    expect(onTool).toHaveBeenCalledWith("query_quote", { code: "600519" });
  });
});
