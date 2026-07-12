import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Copy, GitCompare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { useNoteCompare, exportCompareMarkdown } from "@/hooks/useNoteCompare";
import { NotePicker } from "./NotePicker";
import { DiffTable } from "./DiffTable";
import { cn } from "@/lib/utils";

type Mode = "tag" | "review";

export function CompareView() {
  const [searchParams] = useSearchParams();
  const initialTag = searchParams.get("tag") ?? "";
  const [mode, setMode] = useState<Mode>(initialTag ? "tag" : "tag");
  const [tagInput, setTagInput] = useState(initialTag);
  const [selected, setSelected] = useState<[string | null, string | null]>([null, null]);

  const {
    notes, result, loadingNotes, loadingCompare, error,
    loadByTag, loadReviewNotes, compare, reset,
  } = useNoteCompare();

  useEffect(() => {
    if (initialTag && /^\d{6}$/.test(initialTag)) {
      loadByTag(initialTag);
    }
  }, [initialTag, loadByTag]);

  const handleModeChange = (m: Mode) => {
    setMode(m);
    setSelected([null, null]);
    reset();
    if (m === "review") loadReviewNotes();
  };

  const handleTagSearch = () => {
    const tag = tagInput.trim();
    if (!/^\d{6}$/.test(tag)) {
      toast.error("请输入 6 位数字代码");
      return;
    }
    setSelected([null, null]);
    reset();
    loadByTag(tag);
  };

  const handleSelect = useCallback((id: string) => {
    setSelected(([a, b]) => {
      if (a === id) return [null, b];
      if (b === id) return [a, null];
      if (!a) return [id, b];
      if (!b) return [a, id];
      return [id, b];
    });
    reset();
  }, [reset]);

  useEffect(() => {
    const [a, b] = selected;
    if (a && b && a !== b) compare(a, b);
  }, [selected, compare]);

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(exportCompareMarkdown(result));
      toast.success("已复制为 Markdown");
    } catch {
      toast.error("复制失败");
    }
  };

  const crossKind = result?.comparable && result.note_a.kind !== result.note_b.kind;

  return (
    <div>
      <PageHeader
        title="研究记录对比"
        subtitle="对比同一研究对象在不同时间点的客观数据快照（不含 AI 结论）"
        actions={
          <Link
            to="/notes"
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> 返回列表
          </Link>
        }
      />

      <GlassCard className="mb-4">
        <div className="flex gap-2">
          {(["tag", "review"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => handleModeChange(m)}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                mode === m ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-muted/30",
              )}
            >
              {m === "tag" ? "按标的" : "按复盘"}
            </button>
          ))}
        </div>

        {mode === "tag" && (
          <div className="mt-4 flex gap-2">
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleTagSearch()}
              placeholder="6 位代码，如 600519"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
              maxLength={6}
            />
            <button
              type="button"
              onClick={handleTagSearch}
              disabled={loadingNotes}
              className="rounded-lg bg-primary/15 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/25 disabled:opacity-50"
            >
              {loadingNotes ? <Loader2 className="h-4 w-4 animate-spin" /> : "查询"}
            </button>
          </div>
        )}

        {mode === "review" && notes.length === 0 && !loadingNotes && (
          <button
            type="button"
            onClick={() => loadReviewNotes()}
            className="mt-4 text-sm text-primary hover:underline"
          >
            加载复盘笔记
          </button>
        )}
      </GlassCard>

      {error && (
        <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <GlassCard className="mb-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <GitCompare className="h-4 w-4" /> 选择两条笔记
          <span className="text-xs font-normal text-muted-foreground">（需含数据快照）</span>
        </h3>
        {loadingNotes ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> 加载中…
          </div>
        ) : (
          <NotePicker notes={notes} selected={selected} onSelect={handleSelect} />
        )}
      </GlassCard>

      {(loadingCompare || result) && (
        <GlassCard className="mb-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">对比结果</h3>
            {result?.comparable && (
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:border-primary/40 hover:text-primary"
              >
                <Copy className="h-3.5 w-3.5" /> 复制为 Markdown
              </button>
            )}
          </div>

          {loadingCompare && (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> 对比中…
            </div>
          )}

          {result && !loadingCompare && (
            <>
              {crossKind && (
                <p className="mb-3 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-muted-foreground">
                  笔记类型不同，仅展示共有指标
                </p>
              )}
              {!result.comparable ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  {result.reason === "missing_snapshot"
                    ? "无法对比，缺少数据快照"
                    : "无法对比，无共有可对比指标"}
                </p>
              ) : (
                <DiffTable
                  diff={result.diff}
                  noteATs={result.note_a.ts}
                  noteBTs={result.note_b.ts}
                />
              )}
            </>
          )}
        </GlassCard>
      )}

      <Disclaimer />
    </div>
  );
}
