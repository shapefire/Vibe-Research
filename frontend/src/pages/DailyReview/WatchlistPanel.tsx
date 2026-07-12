import { Loader2, RefreshCw, Plus, X } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { useWatchlist } from "@/hooks/useWatchlist";
import { cn } from "@/lib/utils";
import { pctColor } from "./dailyReviewFormatters";

export function WatchlistPanel() {
  const { codes, quotes, input, setInput, add, remove, refresh, loading } = useWatchlist();

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-muted-foreground">关注股票</h3>
        {codes.length > 0 && (
          <button onClick={refresh} className="text-muted-foreground hover:text-primary" title="刷新价格">
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      <GlassCard className="mb-6">
        <div className="mb-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value.replace(/[^\d,\s]/g, "").slice(0, 80))}
            onKeyDown={(e) => e.key === "Enter" && add()}
            placeholder="加自选：可批量，如 600519 000858"
            className="w-60 rounded-lg border border-border bg-black/20 px-3 py-2 text-sm outline-none focus:border-primary/50"
          />
          <button onClick={add}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary/15 px-4 py-2 text-sm font-medium text-primary shadow-glow hover:bg-primary/25">
            <Plus className="h-4 w-4" /> 增加
          </button>
        </div>
        {codes.length === 0 ? (
          <p className="text-sm text-muted-foreground/60">加上你关注的股票，随时看它们的实时价格与涨跌。数据存本地，不上传。</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {codes.map((c) => {
              const q = quotes[c];
              return (
                <div key={c} className="group relative rounded-lg bg-muted/25 p-3">
                  <button onClick={() => remove(c)} title="移除"
                    className="absolute right-1.5 top-1.5 text-muted-foreground/40 opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100">
                    <X className="h-3.5 w-3.5" />
                  </button>
                  <p className="truncate text-xs text-muted-foreground">{q?.name || c}</p>
                  <p className={cn("mt-1 font-mono text-lg font-bold", q ? pctColor(q.change_pct) : "text-muted-foreground/40")}>{q ? q.price : "—"}</p>
                  <p className={cn("text-xs", q ? pctColor(q.change_pct) : "text-muted-foreground/40")}>
                    {q ? `${q.change_pct > 0 ? "+" : ""}${q.change_pct}%` : c}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </GlassCard>
    </>
  );
}
