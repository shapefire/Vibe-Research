import { BarChart3 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type { Financials } from "@/lib/api";

interface Props {
  fin: Financials;
}

export function FinancialPanel({ fin }: Props) {
  if (!fin.revenue && !fin.roe) return null;
  return (
    <GlassCard className="mb-4">
      <h3 className="mb-1 flex items-center gap-1.5 text-sm font-semibold"><BarChart3 className="h-4 w-4 text-primary" /> 财务关键指标{fin.period && <span className="text-xs font-normal text-muted-foreground/60">· {fin.period}</span>}</h3>
      <p className="mb-3 text-[11px] text-muted-foreground/60">同花顺财务摘要,最新报告期。</p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { k: "营业总收入", v: fin.revenue, yoy: fin.revenue_yoy },
          { k: "归母净利润", v: fin.net_profit, yoy: fin.net_profit_yoy },
          { k: "每股收益", v: fin.eps },
          { k: "ROE", v: fin.roe },
          { k: "销售毛利率", v: fin.gross_margin },
          { k: "销售净利率", v: fin.net_margin },
          { k: "每股净资产", v: fin.bvps },
          { k: "每股经营现金流", v: fin.op_cf_ps },
        ].map((m) => (
          <div key={m.k} className="rounded-lg bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">{m.k}</p>
            <p className="mt-0.5 font-mono text-base font-bold">{m.v ?? "—"}</p>
            {m.yoy && <p className="text-[11px] text-muted-foreground">同比 {m.yoy}</p>}
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
