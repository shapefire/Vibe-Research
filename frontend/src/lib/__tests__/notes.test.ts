import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiError } from "../api";
import { addNote, deleteNote, loadNotes, clearNotes, migrateIfNeeded } from "../notes";

const MIGRATED_KEY = "vr-notes-migrated";
const LEGACY_KEY = "vr-notes";

function mockFetch(handlers: Record<string, (init?: RequestInit) => unknown>) {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method || "GET";
    const key = `${method} ${url}`;
    const handler = handlers[key];
    if (!handler) throw new Error(`Unhandled fetch: ${key}`);
    const data = handler(init);
    return {
      ok: true,
      status: 200,
      json: async () => ({ data }),
    } as Response;
  }));
}

describe("notes API client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loadNotes returns items from API", async () => {
    mockFetch({
      "GET /api/notes?limit=500": () => ({
        items: [{ id: "1-a", kind: "复盘", title: "测试", ts: 1000 }],
        total: 1,
      }),
    });
    const notes = await loadNotes();
    expect(notes).toHaveLength(1);
    expect(notes[0].title).toBe("测试");
    expect(notes[0].content).toBe("");
  });

  it("addNote calls POST then reloads list", async () => {
    mockFetch({
      "POST /api/notes": () => ({ id: "2-b", kind: "复盘", title: "新", ts: 2000 }),
      "GET /api/notes?limit=500": () => ({
        items: [{ id: "2-b", kind: "复盘", title: "新", ts: 2000 }],
        total: 1,
      }),
    });
    const list = await addNote("复盘", "新", "# 内容");
    expect(list).toHaveLength(1);
    expect(list[0].title).toBe("新");
  });

  it("addNote sends snapshot code as tag", async () => {
    let body: Record<string, unknown> = {};
    vi.stubGlobal("fetch", vi.fn(async (_input, init?: RequestInit) => {
      const url = String(_input);
      if (url.includes("/notes/migrate")) {
        return { ok: true, status: 200, json: async () => ({ data: { imported: 0, skipped: 0, total: 0 } }) };
      }
      if (init?.method === "POST") {
        body = JSON.parse(init.body as string);
        return { ok: true, status: 200, json: async () => ({ data: { id: "3-c", kind: "问AI", title: "t", ts: 1 } }) };
      }
      return { ok: true, status: 200, json: async () => ({ data: { items: [], total: 0 } }) };
    }));
    await addNote("问AI", "t", "c", { code: "600519", captured_at: "2026-07-12T15:00:00+08:00" });
    expect(body.tags).toEqual(["600519"]);
  });

  it("addNote uses contextCode as tag when snapshot missing", async () => {
    let body: Record<string, unknown> = {};
    vi.stubGlobal("fetch", vi.fn(async (_input, init?: RequestInit) => {
      if (init?.method === "POST") {
        body = JSON.parse(init.body as string);
        return { ok: true, status: 200, json: async () => ({ data: { id: "4-d", kind: "问AI", title: "t", ts: 1 } }) };
      }
      return { ok: true, status: 200, json: async () => ({ data: { items: [], total: 0 } }) };
    }));
    await addNote("问AI", "t", "c", undefined, "600519");
    expect(body.tags).toEqual(["600519"]);
  });

  it("deleteNote calls DELETE then reloads", async () => {
    mockFetch({
      "DELETE /api/notes/abc": () => ({ ok: true, id: "abc" }),
      "GET /api/notes?limit=500": () => ({ items: [], total: 0 }),
    });
    const list = await deleteNote("abc");
    expect(list).toEqual([]);
  });

  it("clearNotes calls bulk DELETE", async () => {
    let deleted = false;
    vi.stubGlobal("fetch", vi.fn(async (_input, init?: RequestInit) => {
      if (init?.method === "DELETE" && String(_input) === "/api/notes") {
        deleted = true;
        return { ok: true, status: 200, json: async () => ({ data: { ok: true, count: 2 } }) };
      }
      return { ok: true, status: 200, json: async () => ({ data: {} }) };
    }));
    await clearNotes();
    expect(deleted).toBe(true);
  });

  it("throws ApiError on 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "未授权" }),
    }));
    await expect(loadNotes()).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiError on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(loadNotes()).rejects.toMatchObject({ status: 0 });
  });
});

describe("migrateIfNeeded", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("skips when already migrated", async () => {
    localStorage.setItem(MIGRATED_KEY, "true");
    const n = await migrateIfNeeded();
    expect(n).toBe(0);
  });

  it("migrates legacy localStorage notes", async () => {
    localStorage.setItem(LEGACY_KEY, JSON.stringify([{
      id: "1719000000000-test1",
      kind: "复盘",
      title: "旧记录",
      content: "body",
      ts: 1719000000000,
    }]));
    mockFetch({
      "POST /api/notes/migrate": () => ({ imported: 1, skipped: 0, total: 1 }),
    });
    const n = await migrateIfNeeded();
    expect(n).toBe(1);
    expect(localStorage.getItem(MIGRATED_KEY)).toBe("true");
  });

  it("marks migrated when legacy empty", async () => {
    const n = await migrateIfNeeded();
    expect(n).toBe(0);
    expect(localStorage.getItem(MIGRATED_KEY)).toBe("true");
  });
});
