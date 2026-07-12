import { GlassCard } from "@/components/ui/GlassCard";
import { StaleBadge } from "@/components/ui/StaleBadge";
import type { Valuation, FetchMeta } from "@/lib/api";
import { fmt } from "./stockFormatters";

interface Props {
  val: Valuation;
  quoteMeta: FetchMeta | null;
}

export function QuoteOverview({ val, quoteMeta }: Props) {
  const metrics = [
    { k: "现价", v: fmt(val.price) },
    { k: "PE(TTM)", v: fmt(val.pe_ttm) },
    { k: "PB", v: fmt(val.pb) },
    { k: "总市值", v: fmt(val.mcap_yi, " 亿") },
    { k: "26E EPS", v: fmt(val.eps_26e) },
    { k: "前向PE", v: fmt(val.pe_26e) },
    { k: "PEG", v: fmt(val.peg) },
    { k: "消化年数", v: fmt(val.digest_years, " 年") },
  ];

  return (
    <GlassCard glow className="mb-4">
      <div className="mb-4 flex items-baseline gap-2">
        <h2 className="text-xl font-bold">{val.name}</h2>
        <span className="font-mono text-sm text-muted-foreground">{val.code}</span>
        {quoteMeta?.stale && <StaleBadge partial={quoteMeta.partial} />}
        {val.analyst_count > 0 && (
          <span className="ml-auto text-xs text-muted-foreground">机构覆盖 {val.analyst_count} 家</span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {metrics.map((m) => (
          <div key={m.k} className="rounded-lg bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">{m.k}</p>
            <p className="mt-0.5 font-mono text-lg font-bold">{m.v}</p>
          </div>
        ))}
      </div>
      {val.forecast_note && (
        <p className="mt-3 text-xs text-warning">{val.forecast_note}</p>
      )}
    </GlassCard>
  );
}
