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
      if (url.includes("/fund-flow")) {
        return { ok: true, status: 200, json: async () => ({ data: [{ date: "2026-07-12", main_net: -1.2e8, small_net: 0, mid_net: 0, large_net: 0, super_net: 0 }] }) };
      }
      return { ok: true, status: 200, json: async () => ({ data: {} }) };
    }));

    const snap = await fetchNoteSnapshot("600519");
    expect(snap?.code).toBe("600519");
    expect(snap?.quote?.price).toBe(1680);
    expect(snap?.valuation_pctile?.pe_5y).toBe(72);
    expect(snap?.capital_flow?.main_net).toBe(-1.2e8);
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
