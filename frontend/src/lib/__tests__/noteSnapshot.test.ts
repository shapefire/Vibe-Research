import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchNoteSnapshot } from "../noteSnapshot";

describe("fetchNoteSnapshot", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns snapshot with code and quote fields", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/quote")) {
        return { ok: true, status: 200, json: async () => ({ data: { "600519": { price: 1680, pe_ttm: 28.5, change_pct: -0.3 } } }) };
      }
      if (url.includes("/valuation/percentile")) {
        return { ok: true, status: 200, json: async () => ({ data: { metrics: { pe_ttm: { percentile: 72 } } } }) };
      }
      if (url.includes("/valuation")) {
        return { ok: true, status: 200, json: async () => ({ data: { pe_ttm: 28.5, pb: 8.1, mcap_yi: 21000 } }) };
      }
      return { ok: true, status: 200, json: async () => ({ data: {} }) };
    }));

    const snap = await fetchNoteSnapshot("600519");
    expect(snap?.code).toBe("600519");
    expect(snap?.quote?.price).toBe(1680);
    expect(snap?.valuation_pctile?.pe_5y).toBe(72);
    expect(snap?.captured_at).toContain("+08:00");
  });

  it("returns undefined when quote missing", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ data: {} }),
    })));
    const snap = await fetchNoteSnapshot("600519");
    expect(snap).toBeUndefined();
  });

  it("returns undefined on API failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const snap = await fetchNoteSnapshot("600519");
    expect(snap).toBeUndefined();
  });
});
