import { FileText, Megaphone, Newspaper } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type { Report, Announcement, NewsItem } from "@/lib/api";

interface Props {
  reports: Report[];
  anns: Announcement[];
  news: NewsItem[];
  depNote: string | null;
}

export function ReportsNewsPanel({ reports, anns, news, depNote }: Props) {
  return (
    <>
      {reports.length > 0 && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><FileText className="h-4 w-4 text-primary" /> 近期研报（{reports.length}）</h3>
          <div className="space-y-2">
            {reports.slice(0, 12).map((r, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-border/40 pb-2 text-sm last:border-0">
                <span className="w-20 shrink-0 font-mono text-xs text-muted-foreground">{(r.publishDate || "").slice(0, 10)}</span>
                <span className="w-24 shrink-0 truncate text-xs text-muted-foreground">{r.orgSName}</span>
                {r.pdfUrl ? (
                  <a href={r.pdfUrl} target="_blank" rel="noreferrer" className="flex-1 truncate hover:text-primary">{r.title}</a>
                ) : (
                  <span className="flex-1 truncate">{r.title}</span>
                )}
                {r.emRatingName && <span className="shrink-0 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary">{r.emRatingName}</span>}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {anns.length > 0 && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><Megaphone className="h-4 w-4 text-primary" /> 近期公告（{anns.length}）</h3>
          <div className="space-y-2">
            {anns.slice(0, 12).map((a, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-border/40 pb-2 text-sm last:border-0">
                <span className="w-20 shrink-0 font-mono text-xs text-muted-foreground">{a.date}</span>
                {a.type && <span className="w-24 shrink-0 truncate text-xs text-muted-foreground">{a.type}</span>}
                {a.url ? (
                  <a href={a.url} target="_blank" rel="noreferrer" className="flex-1 truncate hover:text-primary">{a.title.replace(/^[^:：]*[:：]/, "")}</a>
                ) : (
                  <span className="flex-1 truncate">{a.title}</span>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      <GlassCard>
        <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><Newspaper className="h-4 w-4 text-primary" /> 个股新闻</h3>
        {depNote ? (
          <p className="text-xs text-warning">{depNote}（安装后新闻/公告即可用）</p>
        ) : news.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">暂无新闻</p>
        ) : (
          <div className="space-y-2">
            {news.slice(0, 10).map((n, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-border/40 pb-2 text-sm last:border-0">
                <span className="w-28 shrink-0 font-mono text-xs text-muted-foreground">{(n.发布时间 || "").slice(0, 16)}</span>
                {n.新闻链接 ? (
                  <a href={n.新闻链接} target="_blank" rel="noreferrer" className="flex-1 truncate hover:text-primary">{n.新闻标题}</a>
                ) : (
                  <span className="flex-1 truncate">{n.新闻标题}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </>
  );
}
