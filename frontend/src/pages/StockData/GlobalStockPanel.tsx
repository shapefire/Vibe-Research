import { BarChart3 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type { GlobalStock } from "@/lib/api";
import { cn } from "@/lib/utils";
import { fmt, pctColor, pctStr, bigMoney, round2, mktName } from "./stockFormatters";

interface Props {
  gstock: GlobalStock;
}

export function GlobalStockPanel({ gstock }: Props) {
  return (
    <>
      <GlassCard glow className="mb-4">
        <div className="mb-4 flex items-baseline gap-2">
          <h2 className="text-xl font-bold">{gstock.name}</h2>
          <span className="font-mono text-sm text-muted-foreground">{gstock.code}</span>
          <span className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary">{gstock.market}</span>
          <span className="ml-auto text-xs text-muted-foreground">{mktName(gstock.market)}</span>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { k: "现价", v: fmt(gstock.quote.price), cls: pctColor(gstock.quote.change_pct) },
            { k: "涨跌幅", v: pctStr(gstock.quote.change_pct), cls: pctColor(gstock.quote.change_pct) },
            { k: "总市值", v: bigMoney(gstock.quote.mcap, gstock.market), cls: "" },
            { k: "成交额", v: bigMoney(gstock.quote.amount, gstock.market), cls: "" },
            { k: "开盘", v: fmt(gstock.quote.open), cls: "" },
            { k: "最高", v: fmt(gstock.quote.high), cls: "" },
            { k: "最低", v: fmt(gstock.quote.low), cls: "" },
            { k: "昨收", v: fmt(gstock.quote.prev_close), cls: "" },
          ].map((m) => (
            <div key={m.k} className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">{m.k}</p>
              <p className={cn("mt-0.5 font-mono text-base font-bold", m.cls)}>{m.v}</p>
            </div>
          ))}
        </div>
      </GlassCard>

      {gstock.metrics && (
        <GlassCard className="mb-4">
          <h3 className="mb-1 flex items-center gap-1.5 text-sm font-semibold">
            <BarChart3 className="h-4 w-4 text-primary" /> 关键财务指标
            <span className="text-xs font-normal text-muted-foreground/60">· {gstock.metrics.report_date}</span>
          </h3>
          <p className="mb-3 text-[11px] text-muted-foreground/60">东财 GMAININDICATOR，最新报告期。金额为原生币种。</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { k: "营业收入", v: bigMoney(gstock.metrics.revenue, gstock.market), yoy: gstock.metrics.revenue_yoy != null ? round2(gstock.metrics.revenue_yoy, "%") : "" },
              { k: "归母净利", v: bigMoney(gstock.metrics.net_profit, gstock.market), yoy: "" },
              { k: "每股收益 EPS", v: round2(gstock.metrics.eps), yoy: "" },
              { k: "ROE", v: round2(gstock.metrics.roe, "%"), yoy: "" },
              { k: "毛利率", v: round2(gstock.metrics.gross_margin, "%"), yoy: "" },
              { k: "净利率", v: round2(gstock.metrics.net_margin, "%"), yoy: "" },
              { k: "资产负债率", v: round2(gstock.metrics.debt_ratio, "%"), yoy: "" },
            ].map((m) => (
              <div key={m.k} className="rounded-lg bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">{m.k}</p>
                <p className="mt-0.5 font-mono text-base font-bold">{m.v}</p>
                {m.yoy && <p className="text-[11px] text-muted-foreground">同比 {m.yoy}</p>}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      <p className="text-xs text-muted-foreground/60">
        美股 / 港股数据来自 <a href="https://github.com/simonlin1212/global-stock-data" target="_blank" rel="noreferrer" className="hover:text-primary">global-stock-data</a>（东财域内源）· 金额为原生币种 · 仅客观数据，不含买卖建议。
      </p>
    </>
  );
}
