import { RefreshCw, Globe } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type { IndexQuote, GlobalIndex } from "@/lib/api";
import { cn } from "@/lib/utils";
import { pctColor } from "./dailyReviewFormatters";

interface Props {
  indices: IndexQuote[];
  globalIdx: GlobalIndex[];
  idxErr: boolean;
  loading: boolean;
  onRefresh: () => void;
}

export function MarketIndices({ indices, globalIdx, idxErr, loading, onRefresh }: Props) {
  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-muted-foreground">大盘指数</h3>
        <button onClick={onRefresh} className="text-muted-foreground hover:text-primary" title="刷新"><RefreshCw className="h-3.5 w-3.5" /></button>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {indices.length === 0
          ? [1, 2, 3, 4].map((i) => (
              <GlassCard key={i} className="p-3">
                <p className="text-xs text-muted-foreground">{idxErr ? "行情未接通" : loading ? "加载中…" : "暂无数据"}</p>
                <p className="mt-1 font-mono text-lg font-bold text-muted-foreground/40">—</p>
              </GlassCard>
            ))
          : indices.map((i) => (
              <GlassCard key={i.name} className="p-3">
                <p className="truncate text-xs text-muted-foreground">{i.name}</p>
                <p className={cn("mt-1 font-mono text-lg font-bold", pctColor(i.change_pct))}>{i.price}</p>
                <p className={cn("text-xs", pctColor(i.change_pct))}>{i.change_pct > 0 ? "+" : ""}{i.change_pct}%</p>
              </GlassCard>
            ))}
      </div>

      {globalIdx.length > 0 && (
        <>
          <div className="mb-3 flex items-center gap-2">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground"><Globe className="h-4 w-4" /> 全球市场</h3>
            <span className="text-[11px] text-muted-foreground/50">隔夜外围 · A 股常看美股 / 港股脸色</span>
          </div>
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
            {globalIdx.map((g) => (
              <GlassCard key={g.key} className="p-3">
                <p className="truncate text-xs text-muted-foreground">{g.name} <span className="text-muted-foreground/40">{g.region}</span></p>
                <p className={cn("mt-1 font-mono text-lg font-bold", g.change_pct == null ? "text-foreground" : pctColor(g.change_pct))}>{g.price ?? "—"}</p>
                <p className={cn("text-xs", g.change_pct == null ? "text-muted-foreground" : pctColor(g.change_pct))}>
                  {g.change_pct == null ? "—" : `${g.change_pct > 0 ? "+" : ""}${g.change_pct}%`}
                </p>
              </GlassCard>
            ))}
          </div>
        </>
      )}
    </>
  );
}
