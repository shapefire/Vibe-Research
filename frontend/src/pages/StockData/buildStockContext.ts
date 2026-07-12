import type {
  Valuation, Report, ValPercentile, Financials, Announcement, GlobalStock,
} from "@/lib/api";
import { bigMoney, mktName, pctStr, round2 } from "./stockFormatters";

export interface StockDataState {
  val: Valuation | null;
  reports: Report[];
  anns: Announcement[];
  pctl: ValPercentile | null;
  fin: Financials | null;
  gstock: GlobalStock | null;
}

export function buildStockContext(data: StockDataState): string {
  const { val, reports, anns, pctl, fin, gstock } = data;

  if (gstock) {
    return `个股（${mktName(gstock.market)}）：${gstock.name}（${gstock.code}）\n` +
      `现价 ${gstock.quote.price ?? "—"} · 涨跌 ${pctStr(gstock.quote.change_pct)} · 总市值 ${bigMoney(gstock.quote.mcap, gstock.market)}\n` +
      (gstock.metrics
        ? `财务(${gstock.metrics.report_date})：营收 ${bigMoney(gstock.metrics.revenue, gstock.market)}(同比${round2(gstock.metrics.revenue_yoy, "%")})、归母净利 ${bigMoney(gstock.metrics.net_profit, gstock.market)}、EPS ${gstock.metrics.eps ?? "—"}、ROE ${round2(gstock.metrics.roe, "%")}、毛利率 ${round2(gstock.metrics.gross_margin, "%")}、净利率 ${round2(gstock.metrics.net_margin, "%")}、资产负债率 ${round2(gstock.metrics.debt_ratio, "%")}`
        : "");
  }

  if (val) {
    return `个股：${val.name}（${val.code}）\n现价 ${val.price} · PE(TTM) ${val.pe_ttm} · PB ${val.pb} · 市值 ${val.mcap_yi}亿\n` +
      `26E EPS ${val.eps_26e ?? "—"} · 前向PE ${val.pe_26e ?? "—"} · PEG ${val.peg ?? "—"} · 消化 ${val.digest_years ?? "—"}年 · 机构覆盖 ${val.analyst_count} 家\n` +
      (pctl?.metrics.pe_ttm ? `估值历史分位(近5年)：PE-TTM 处于 ${pctl.metrics.pe_ttm.percentile}% 分位、PB 处于 ${pctl.metrics.pb?.percentile ?? "—"}% 分位\n` : "") +
      (fin?.revenue ? `财务(${fin.period ?? "—"})：营收 ${fin.revenue}(同比${fin.revenue_yoy ?? "—"})、净利 ${fin.net_profit ?? "—"}(同比${fin.net_profit_yoy ?? "—"})、ROE ${fin.roe ?? "—"}、毛利率 ${fin.gross_margin ?? "—"}\n` : "") +
      (anns.length ? `近期公告：${anns.slice(0, 5).map((a) => a.title.replace(/^[^:：]*[:：]/, "")).join("；")}\n` : "") +
      `近期研报：${reports.slice(0, 5).map((r) => r.title).join("；") || "无"}`;
  }

  return "还没查询个股。输入 6 位代码后可让 AI 基于客观数据帮你分析。";
}
