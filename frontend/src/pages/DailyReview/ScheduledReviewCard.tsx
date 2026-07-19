import { Link } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GlassCard } from "@/components/ui/GlassCard";
import type { NoteDetail } from "@/lib/api";

interface Props {
  review: NoteDetail | null;
  loading: boolean;
  done: boolean;
  error: string | null;
}

export function ScheduledReviewCard({ review, loading, done, error }: Props) {
  if (loading && !review) {
    return (
      <GlassCard className="mb-6">
        <p className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground/60">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载定时复盘…
        </p>
      </GlassCard>
    );
  }

  if (review) {
    const preview = review.content.length > 600 ? `${review.content.slice(0, 600)}…` : review.content;
    return (
      <GlassCard glow className="mb-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
            <Sparkles className="h-4 w-4 text-primary" /> {review.title}
          </h3>
          <Link to="/notes" className="text-[11px] text-primary hover:underline">
            研究记录 · 完整版
          </Link>
        </div>
        <div className="prose prose-sm prose-invert max-h-64 max-w-none overflow-y-auto text-foreground">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{preview}</ReactMarkdown>
        </div>
        <p className="mt-3 text-[11px] text-muted-foreground/50">
          收盘定时生成 · 下方为实时盘面，可手动「让 AI 复盘今天」覆盖或补充
        </p>
      </GlassCard>
    );
  }

  if (done && !error) {
    return (
      <GlassCard className="mb-6 border-dashed">
        <div className="flex items-start gap-3">
          <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
          <div className="text-sm text-muted-foreground/80">
            <p className="font-medium text-muted-foreground">今日尚无定时复盘</p>
            <p className="mt-1">
              到点后会自动生成数据快照；若已设 <code className="rounded bg-muted/40 px-1 text-xs">VR_DIGEST_INCLUDE_LLM=true</code>{" "}
              并配置 API Key 或本机 CLI，会一并写入 AI 复盘到研究记录。
            </p>
            <p className="mt-2">
              也可直接用下方 <b className="text-foreground">「让 AI 复盘今天」</b> 基于实时数据手动生成。
            </p>
          </div>
        </div>
      </GlassCard>
    );
  }

  return null;
}
