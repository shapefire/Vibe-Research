import { describe, it, expect } from "vitest";
import { buildStockContext } from "../buildStockContext";
import type { StockDataState } from "../buildStockContext";

const base: StockDataState = {
  val: null, reports: [], anns: [], pctl: null, fin: null, gstock: null,
};

describe("buildStockContext", () => {
  it("returns placeholder when no data", () => {
    expect(buildStockContext(base)).toContain("还没查询个股");
  });

  it("includes stock name and PE for full A-share data", () => {
    const ctx = buildStockContext({
      ...base,
      val: {
        name: "贵州茅台", code: "600519", price: 1800, pe_ttm: 25, pb: 8,
        mcap_yi: 22000, eps_26e: 70, pe_26e: 22, peg: 1.2, digest_years: 3,
        analyst_count: 40, forecast_note: null,
      },
      pctl: {
        period: "近5年",
        metrics: { pe_ttm: { current: 25, percentile: 60, min: 10, p20: 15, p50: 22, p80: 30, max: 40, n: 100 }, pb: null },
      },
    });
    expect(ctx).toContain("贵州茅台");
    expect(ctx).toContain("PE(TTM) 25");
    expect(ctx).toContain("60% 分位");
  });

  it("handles partial null without NaN", () => {
    const ctx = buildStockContext({
      ...base,
      val: {
        name: "测试", code: "000001", price: 10, pe_ttm: null, pb: null,
        mcap_yi: 100, eps_26e: null, pe_26e: null, peg: null, digest_years: null,
        analyst_count: 0, forecast_note: null,
      },
    });
    expect(ctx).not.toContain("NaN");
    expect(ctx).toContain("测试");
  });

  it("includes market label for global stock", () => {
    const ctx = buildStockContext({
      ...base,
      gstock: {
        name: "Apple", code: "AAPL", market: "US",
        quote: { price: 200, change_pct: 1.5, mcap: 3e12, amount: 1e10, open: 199, high: 201, low: 198, prev_close: 197 },
        metrics: null,
      },
    });
    expect(ctx).toContain("美股");
    expect(ctx).toContain("Apple");
  });
});
