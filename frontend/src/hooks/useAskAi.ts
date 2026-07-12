import { useState, useRef, useCallback } from "react";
import { chatStream, type ChatMsg } from "@/lib/llm";
import { ApiError } from "@/lib/api";

export interface AskAiCallbacks {
  onTool?: (tool: string, args: Record<string, unknown>) => void;
  onDelta: (text: string) => void;
}

export function useAskAi() {
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
  }, []);

  const ask = useCallback(async (
    history: ChatMsg[],
    context: string,
    callbacks: AskAiCallbacks,
  ) => {
    setError(null);
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const alive = () => abortRef.current === ac && !ac.signal.aborted;
    setStreaming(true);
    try {
      await chatStream(history, context, {
        onTool: (tool, args) => { if (alive()) callbacks.onTool?.(tool, args); },
        onDelta: (t) => { if (alive()) callbacks.onDelta(t); },
      }, ac.signal);
    } catch (e) {
      if (!ac.signal.aborted) {
        setError(e instanceof ApiError ? e.message : "对话失败");
      }
      throw e;
    } finally {
      if (abortRef.current === ac) {
        abortRef.current = null;
        setStreaming(false);
      }
    }
  }, []);

  return { ask, streaming, error, abort, clearError: () => setError(null) };
}
