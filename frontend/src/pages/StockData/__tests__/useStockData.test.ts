import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useStockData } from "../useStockData";
import { ApiError } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      globalStock: vi.fn(),
      valuation: vi.fn(),
      reports: vi.fn(),
      percentile: vi.fn(),
      financials: vi.fn(),
      announcements: vi.fn(),
      news: vi.fn(),
      margin: vi.fn().mockResolvedValue([]),
      blockTrade: vi.fn().mockResolvedValue([]),
      holders: vi.fn().mockResolvedValue([]),
      dividend: vi.fn().mockResolvedValue([]),
      fundFlow: vi.fn().mockResolvedValue([]),
      dragonTiger: vi.fn().mockResolvedValue(null),
      lockup: vi.fn().mockResolvedValue(null),
      blocks: vi.fn().mockResolvedValue(null),
      hotConcepts: vi.fn().mockResolvedValue([]),
      investorQa: vi.fn().mockResolvedValue([]),
      quoteWithMeta: vi.fn().mockResolvedValue({ meta: null }),
    },
  };
});

import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

describe("useStockData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not fetch on empty code", async () => {
    const { result } = renderHook(() => useStockData());
    await act(async () => { await result.current.search(""); });
    expect(result.current.error).toBe("请输入代码");
    expect(mockedApi.valuation).not.toHaveBeenCalled();
  });

  it("loads A-share data in parallel", async () => {
    mockedApi.valuation.mockResolvedValue({
      name: "茅台", code: "600519", price: 1800, pe_ttm: 25, pb: 8,
      mcap_yi: 22000, eps_26e: null, pe_26e: null, peg: null, digest_years: null,
      analyst_count: 5, forecast_note: null,
    });
    mockedApi.reports.mockResolvedValue([]);
    mockedApi.percentile.mockResolvedValue(null);
    mockedApi.financials.mockResolvedValue(null);
    mockedApi.announcements.mockResolvedValue([]);
    mockedApi.news.mockResolvedValue([]);

    const { result } = renderHook(() => useStockData());
    await act(async () => { await result.current.search("600519"); });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.val?.name).toBe("茅台");
    expect(mockedApi.valuation).toHaveBeenCalledWith("600519");
  });

  it("sets error on API failure", async () => {
    mockedApi.valuation.mockRejectedValue(new ApiError("查询失败", 500));
    mockedApi.reports.mockResolvedValue([]);
    mockedApi.percentile.mockResolvedValue(null);
    mockedApi.financials.mockResolvedValue(null);
    mockedApi.announcements.mockResolvedValue([]);

    const { result } = renderHook(() => useStockData());
    await act(async () => { await result.current.search("600519"); });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("查询失败");
  });
});
