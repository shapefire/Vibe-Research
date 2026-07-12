import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  loadLlm, saveLlm, clearLlm, hasLlm, chatStream, chat,
  type LlmConfig,
} from "../llm";
const validApi: LlmConfig = {
  provider: "deepseek",
  baseURL: "https://api.deepseek.com",
  apiKey: "sk-test",
  model: "deepseek-v4-flash",
};

const validCli: LlmConfig = {
  provider: "cli-claude",
  baseURL: "",
  apiKey: "",
  model: "claude-code",
};

describe("loadLlm / saveLlm", () => {
  beforeEach(() => {
    clearLlm();
  });

  it("returns null when nothing stored", () => {
    expect(loadLlm()).toBeNull();
    expect(hasLlm()).toBe(false);
  });

  it("loads valid API config", () => {
    saveLlm(validApi);
    expect(loadLlm()).toEqual(validApi);
    expect(hasLlm()).toBe(true);
  });

  it("loads valid CLI config without baseURL or apiKey", () => {
    saveLlm(validCli);
    expect(loadLlm()).toEqual(validCli);
    expect(hasLlm()).toBe(true);
  });

  it("returns null when API config missing baseURL", () => {
    saveLlm({ ...validApi, baseURL: "" });
    expect(loadLlm()).toBeNull();
  });

  it("returns null when API config missing apiKey", () => {
    saveLlm({ ...validApi, apiKey: "" });
    expect(loadLlm()).toBeNull();
  });

  it("returns null when model is empty", () => {
    saveLlm({ ...validApi, model: "" });
    expect(loadLlm()).toBeNull();
  });

  it("returns null for CLI with empty model", () => {
    saveLlm({ ...validCli, model: "" });
    expect(loadLlm()).toBeNull();
  });

  it("clearLlm removes stored config", () => {
    saveLlm(validApi);
    clearLlm();
    expect(loadLlm()).toBeNull();
    expect(hasLlm()).toBe(false);
  });

  it("returns null on corrupted JSON", () => {
    localStorage.setItem("vr-llm", "{bad json");
    expect(loadLlm()).toBeNull();
  });

  it("persists all fields through save/load cycle", () => {
    const cfg: LlmConfig = {
      provider: "openrouter",
      baseURL: "https://openrouter.ai/api/v1",
      apiKey: "or-key",
      model: "openai/gpt-4o",
    };
    saveLlm(cfg);
    expect(loadLlm()).toEqual(cfg);
  });

  it("CLI provider with baseURL set still valid if model present", () => {
    saveLlm({ ...validCli, baseURL: "ignored" });
    expect(loadLlm()?.provider).toBe("cli-claude");
    expect(hasLlm()).toBe(true);
  });
});

function ndjsonStream(lines: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const line of lines) {
        controller.enqueue(encoder.encode(line + "\n"));
      }
      controller.close();
    },
  });
}

describe("chatStream", () => {
  beforeEach(() => {
    clearLlm();
    saveLlm(validApi);
    vi.restoreAllMocks();
  });

  it("throws when no llm config", async () => {
    clearLlm();
    await expect(chatStream([], "")).rejects.toMatchObject({
      message: "尚未接入 AI，请先在「接入 AI」里配置",
      status: 400,
    });
  });

  it("streams delta and done events", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: ndjsonStream([
        '{"type":"delta","text":"你好"}',
        '{"type":"done","trace":[{"tool":"quote","args":{}}],"rounds":1}',
      ]),
    }));
    const onDelta = vi.fn();
    const onTool = vi.fn();
    const result = await chatStream(
      [{ role: "user", content: "hi" }],
      "ctx",
      { onDelta, onTool },
    );
    expect(result.content).toBe("你好");
    expect(result.rounds).toBe(1);
    expect(result.trace).toHaveLength(1);
    expect(onDelta).toHaveBeenCalledWith("你好");
  });

  it("calls onTool for tool events", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: ndjsonStream([
        '{"type":"tool","tool":"valuation","args":{"code":"600519"}}',
        '{"type":"done","trace":[],"rounds":0}',
      ]),
    }));
    const onTool = vi.fn();
    await chatStream([{ role: "user", content: "q" }], "", { onTool });
    expect(onTool).toHaveBeenCalledWith("valuation", { code: "600519" });
  });

  it("throws ApiError on stream error event", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: ndjsonStream(['{"type":"error","message":"模型超时"}']),
    }));
    await expect(chatStream([{ role: "user", content: "q" }], "")).rejects.toMatchObject({
      message: "模型超时",
      status: 502,
    });
  });

  it("throws on HTTP error before stream", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "缺少模型配置" }),
    }));
    await expect(chatStream([{ role: "user", content: "q" }], "")).rejects.toMatchObject({
      message: "缺少模型配置",
      status: 400,
    });
  });

  it("throws 401 with auth hint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "未授权" }),
    }));
    await expect(chatStream([{ role: "user", content: "q" }], "")).rejects.toMatchObject({
      message: "后端开启了访问鉴权（VR_API_KEY）：请在「接入 AI」页底部填写后端访问密钥",
      status: 401,
    });
  });

  it("throws when response has no body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: null,
    }));
    await expect(chatStream([{ role: "user", content: "q" }], "")).rejects.toMatchObject({
      message: "后端无响应流",
      status: 502,
    });
  });

  it("rethrows AbortError", async () => {
    const abortErr = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortErr));
    await expect(chatStream([{ role: "user", content: "q" }], "")).rejects.toBe(abortErr);
  });
});

describe("chat", () => {
  beforeEach(() => {
    clearLlm();
    saveLlm(validApi);
    vi.restoreAllMocks();
  });

  it("delegates to chatStream", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: ndjsonStream([
        '{"type":"delta","text":"ok"}',
        '{"type":"done","trace":[],"rounds":1}',
      ]),
    }));
    const result = await chat([{ role: "user", content: "q" }], "ctx");
    expect(result.content).toBe("ok");
  });
});