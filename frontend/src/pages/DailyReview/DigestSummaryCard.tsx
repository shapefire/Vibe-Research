import { FileText, Loader2 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type { DailyDigest } from "@/lib/api";

interface Props {
  digest: DailyDigest | null;
  loading: boolean;
  done: boolean;
  error: string | null;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

export function DigestSummaryCard({ digest, loading, done, error }: Props) {
  if (loading && !digest) {
    return (
      <GlassCard className="mb-6">
        <p className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground/60">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载今日摘要…
        </p>
      </GlassCard>
    );
  }

  if (digest) {
    const sh = digest.market?.sh_index;
    const sz = digest.market?.sz_index;
    const sent = digest.market?.sentiment;
    const wl = digest.watchlist_summary;
    return (
      <GlassCard className="mb-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
            <FileText className="h-4 w-4 text-primary" /> 今日摘要 · {digest.date}
          </h3>
          <span className="text-[11px] text-muted-foreground/50">
            生成于 {digest.generated_at || "—"}
          </span>
        </div>
        <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
          <p>
            上证 {sh?.close ?? "—"}（{fmtPct(sh?.change_pct)}）· 深证 {sz?.close ?? "—"}（
            {fmtPct(sz?.change_pct)}）
          </p>
          <p>
            涨跌 {sent?.up_count ?? "—"} / {sent?.down_count ?? "—"} · 涨停{" "}
            {sent?.limit_up ?? "—"} / 跌停 {sent?.limit_down ?? "—"}
          </p>
          <p>
            自选 {wl?.total ?? 0} · 上涨 {wl?.up ?? 0} / 下跌 {wl?.down ?? 0}
            {wl?.unconfigured ? "（未配置）" : ""}
          </p>
        </div>
        {digest.errors && digest.errors.length > 0 && (
          <p className="mt-2 text-[11px] text-amber-500/80">
            部分数据源失败：{digest.errors.map((e) => e.section).join("、")}
          </p>
        )}
        <p className="mt-3 text-[11px] text-muted-foreground/50">
          纯数据摘要，不构成投资建议。下方为实时盘面。
        </p>
      </GlassCard>
    );
  }

  if (done && !error) {
    return (
      <GlassCard className="mb-6 border-dashed">
        <div className="flex items-start gap-3">
          <FileText className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
          <div className="text-sm text-muted-foreground/80">
            <p className="font-medium text-muted-foreground">尚无今日数据摘要</p>
            <p className="mt-1">
              调度器或 GitHub Actions 生成后会出现在此；也可通过{" "}
              <code className="rounded bg-muted/40 px-1 text-xs">python -m jobs.daily_digest</code>{" "}
              手动跑一次。
            </p>
          </div>
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard className="mb-6 border-dashed">
        <p className="text-sm text-destructive/80">今日摘要加载失败：{error}</p>
      </GlassCard>
    );
  }

  return null;
}
