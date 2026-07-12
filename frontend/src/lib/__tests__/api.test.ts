import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError, authHeaders, loadAccessKey, saveAccessKey, api, downloadReport } from "../api";

describe("ApiError", () => {
  it("carries message and status", () => {
    const err = new ApiError("测试错误", 502);
    expect(err.message).toBe("测试错误");
    expect(err.status).toBe(502);
    expect(err).toBeInstanceOf(Error);
  });
});

describe("authHeaders", () => {
  beforeEach(() => {
    saveAccessKey("");
  });

  it("returns empty when no key stored", () => {
    expect(authHeaders()).toEqual({});
  });

  it("returns Bearer header when key is set", () => {
    saveAccessKey("secret-key");
    expect(authHeaders()).toEqual({ Authorization: "Bearer secret-key" });
  });

  it("loadAccessKey reads persisted value", () => {
    saveAccessKey("my-key");
    expect(loadAccessKey()).toBe("my-key");
  });

  it("saveAccessKey with empty string removes key", () => {
    saveAccessKey("temp");
    saveAccessKey("");
    expect(loadAccessKey()).toBe("");
  });
});

describe("api request errors", () => {
  beforeEach(() => {
    saveAccessKey("");
    vi.restoreAllMocks();
  });

  it("throws 401 with Chinese hint when backend requires VR_API_KEY", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "未授权" }),
    }));
    await expect(api.health()).rejects.toMatchObject({
      message: "后端开启了访问鉴权（VR_API_KEY）：请在「接入 AI」页底部填写后端访问密钥",
      status: 401,
    });
  });

  it("throws connection error when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.health()).rejects.toMatchObject({
      message: "连接不到后端，请先启动 backend（uvicorn app:app --port 8900）",
      status: 0,
    });
  });

  it("returns data on successful response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: { ok: true } }),
    }));
    const result = await api.health();
    expect(result).toEqual({ ok: true });
  });

  it("uses auth header in requests when key is set", async () => {
    saveAccessKey("test-token");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: { ok: true } }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.health();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      }),
    );
  });

  it("throws 503 with friendly message for AllSourcesFailed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        detail: {
          detail: "行情所有数据源不可用",
          chain: "quote",
          attempts: [{ source: "tencent", error: "timeout" }],
        },
      }),
    }));
    await expect(api.quote("600519")).rejects.toMatchObject({
      message: "行情所有数据源不可用",
      status: 503,
    });
  });

  it("healthSources returns full payload without data wrapper", async () => {
    const payload = {
      sources: { tencent: { status: "ok", last_ok: "2026-07-12T10:00:00+08:00", last_fail: null, last_error: null } },
      chains: { quote: "ok", kline: "down", news: "down" },
      updated_at: "2026-07-12T10:00:01+08:00",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    }));
    const result = await api.healthSources();
    expect(result.chains.quote).toBe("ok");
    expect(result.sources.tencent.status).toBe("ok");
  });

  it("quoteWithMeta returns data and stale meta", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        data: { "600519": { name: "茅台", price: 1, last_close: 1, change_pct: 0, pe_ttm: 1, pb: 1, mcap_yi: 1, turnover_pct: 0, limit_up: 0, limit_down: 0 } },
        _meta: { source: "stale_cache", stale: true, chain: "quote", partial: true },
      }),
    }));
    const result = await api.quoteWithMeta("600519,000001");
    expect(result.data["600519"].name).toBe("茅台");
    expect(result.meta?.stale).toBe(true);
    expect(result.meta?.partial).toBe(true);
  });

  it("throws ApiError with detail from JSON body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "代码必须是 6 位数字" }),
    }));
    await expect(api.quote("abc")).rejects.toMatchObject({
      message: "代码必须是 6 位数字",
      status: 400,
    });
  });

  it("falls back to HTTP status when response is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => { throw new Error("not json"); },
    }));
    await expect(api.health()).rejects.toMatchObject({
      message: "HTTP 502",
      status: 502,
    });
  });

  it("sends POST with JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: { holdings: [] } }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.addHolding("600519", 100, 50);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/portfolio/holding",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
        body: JSON.stringify({ code: "600519", shares: 100, cost: 50 }),
      }),
    );
  });
});

describe("api client methods", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: {} }),
    }));
  });

  it("calls expected paths for common endpoints", async () => {
    const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
    await api.indices();
    await api.marketOverview();
    await api.emotion();
    await api.turnoverTop();
    await api.globalIndices();
    await api.globalStock("AAPL");
    await api.radar();
    await api.portfolio();
    await api.valuation("600519");
    await api.percentile("600519");
    await api.quote("600519");
    await api.healthSources();
    expect(fetchMock).toHaveBeenCalledWith("/api/indices", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/market/overview", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/market/emotion", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/market/turnover-top", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/global/indices", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/global/stock?symbol=AAPL", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/radar", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/portfolio", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/valuation?code=600519", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/valuation/percentile?code=600519", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/quote?codes=600519", expect.any(Object));
  });

  it("covers remaining api methods", async () => {
    const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
    const code = "600519";
    await api.radarRefresh();
    await api.removeHolding(code);
    await api.refreshPortfolio();
    await api.closePosition(code, "2026-07-12", 100, 50, 80);
    await api.removeClosed(0);
    await api.financials(code);
    await api.announcements(code);
    await api.reports(code);
    await api.news(code);
    await api.margin(code);
    await api.blockTrade(code);
    await api.holders(code);
    await api.dividend(code);
    await api.fundFlow(code);
    await api.dragonTiger(code);
    await api.lockup(code);
    await api.blocks(code);
    await api.hotConcepts(code);
    await api.investorQa(code);
    await api.industry(10);
    await api.myReports();
    await api.uploadReport("r.pdf", "base64");
    await api.deleteReport("rid-1");
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(22);
  });
});

describe("downloadReport", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches file and triggers download", async () => {
    const click = vi.fn();
    const anchor = { href: "", download: "", click, remove: vi.fn() } as unknown as HTMLAnchorElement;
    vi.spyOn(document, "createElement").mockReturnValue(anchor);
    vi.spyOn(document.body, "appendChild").mockImplementation(() => anchor);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:test"),
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => new Blob(["data"]),
    }));
    await downloadReport("rid-1", "report.pdf");
    expect(click).toHaveBeenCalled();
    expect(anchor.download).toBe("report.pdf");
  });

  it("throws ApiError on failed download", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      blob: async () => new Blob([]),
    }));
    await expect(downloadReport("x", "f.pdf")).rejects.toMatchObject({ status: 404 });
  });
});
