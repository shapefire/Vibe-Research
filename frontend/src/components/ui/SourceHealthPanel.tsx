import { useCallback, useEffect, useState } from "react";
import { Activity, AlertCircle, CheckCircle2, RefreshCw, XCircle } from "lucide-react";
import { api, type HealthSources } from "@/lib/api";
import {
  CHAIN_LABELS,
  CHAIN_STATUS_LABELS,
  SOURCE_LABELS,
  SOURCE_STATUS_LABELS,
} from "@/lib/source-health";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";

function StatusIcon({ status }: { status: string }) {
  if (status === "ok") return <CheckCircle2 className="h-4 w-4 text-success" />;
  if (status === "degraded" || status === "idle") return <AlertCircle className="h-4 w-4 text-warning" />;
  return <XCircle className="h-4 w-4 text-destructive" />;
}

function statusClass(status: string) {
  if (status === "ok") return "text-success";
  if (status === "degraded" || status === "idle") return "text-warning";
  if (status === "missing") return "text-muted-foreground";
  return "text-destructive";
}

function formatTime(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

/** 展示各数据源与 fallback chain 的健康状态，供设置页排障。 */
export function SourceHealthPanel() {
  const [status, setStatus] = useState<HealthSources | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.healthSources()
      .then(setStatus)
      .catch(() => setError("无法读取数据源状态，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (window.location.hash === "#data-sources") {
      document.getElementById("data-sources")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  return (
    <div id="data-sources" className="mb-4 scroll-mt-4">
      <GlassCard>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <div>
              <h3 className="text-sm font-semibold">数据源状态</h3>
              <p className="text-xs text-muted-foreground">查看行情、K 线、新闻各链路与上游依赖是否正常</p>
            </div>
          </div>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/40 disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            刷新
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading && !status && !error && (
          <p className="text-sm text-muted-foreground">正在读取数据源状态…</p>
        )}

        {status && (
          <div className="space-y-4">
            <div>
              <h4 className="mb-2 text-xs font-medium text-muted-foreground">数据链路</h4>
              <div className="grid gap-2 sm:grid-cols-3">
                {Object.entries(status.chains).map(([name, chainStatus]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between rounded-lg border border-border/70 bg-black/10 px-3 py-2 text-sm"
                  >
                    <span>{CHAIN_LABELS[name] ?? name}</span>
                    <span className={cn("inline-flex items-center gap-1 font-medium", statusClass(chainStatus))}>
                      <StatusIcon status={chainStatus} />
                      {CHAIN_STATUS_LABELS[chainStatus] ?? chainStatus}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="mb-2 text-xs font-medium text-muted-foreground">上游依赖</h4>
              <div className="overflow-x-auto rounded-lg border border-border/70">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead className="bg-black/20 text-xs text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-medium">依赖</th>
                      <th className="px-3 py-2 font-medium">状态</th>
                      <th className="px-3 py-2 font-medium">最近成功</th>
                      <th className="px-3 py-2 font-medium">最近失败</th>
                      <th className="px-3 py-2 font-medium">错误信息</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(status.sources).map(([name, source]) => (
                      <tr key={name} className="border-t border-border/50">
                        <td className="px-3 py-2 font-medium">{SOURCE_LABELS[name] ?? name}</td>
                        <td className={cn("px-3 py-2", statusClass(source.status))}>
                          {SOURCE_STATUS_LABELS[source.status] ?? source.status}
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{formatTime(source.last_ok)}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{formatTime(source.last_fail)}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{source.last_error ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              更新时间：{formatTime(status.updated_at)}
              {Object.values(status.chains).some((chainStatus) => chainStatus === "degraded" || chainStatus === "down") && (
                <span className="ml-2 text-warning">
                  部分链路已降级或不可用，页面可能展示缓存数据。
                </span>
              )}
              {Object.values(status.chains).some((chainStatus) => chainStatus === "idle") && (
                <span className="ml-2 text-warning">
                  部分链路尚未探测，刷新后会自动检测；新闻/K 线 fallback：akshare/mootdx → 东财 → 百度日 K。
                </span>
              )}
            </p>
            <p className="text-xs text-muted-foreground/80">
              若上游依赖显示「未安装」，请在后端执行 <code className="rounded bg-muted/50 px-1">pip install mootdx akshare</code>（Docker 镜像已预装）。
            </p>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
