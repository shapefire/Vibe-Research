import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2, ChevronDown, ChevronRight, NotebookPen, Loader2, GitCompare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { api, ApiError } from "@/lib/api";
import { loadNotes, deleteNote, clearNotes, migrateIfNeeded, type Note } from "@/lib/notes";

const KIND_COLOR: Record<string, string> = {
  复盘: "bg-primary/15 text-primary",
  今日要点: "bg-warning/15 text-warning",
  问AI: "bg-success/15 text-success",
};

export function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState<string | null>(null);

  const fmt = (ts: number) => new Date(ts).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });

  const refresh = useCallback(async () => {
    setError(null);
    const list = await loadNotes();
    setNotes(list);
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const imported = await migrateIfNeeded();
        if (imported > 0) {
          toast.success(`已迁移 ${imported} 条研究记录到本地服务`);
        }
        await refresh();
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : "加载研究记录失败";
        setError(msg);
      } finally {
        setLoading(false);
      }
    })();
  }, [refresh]);

  const handleToggle = async (n: Note) => {
    if (openId === n.id) {
      setOpenId(null);
      return;
    }
    setOpenId(n.id);
    if (!n.content) {
      setLoadingContent(n.id);
      try {
        const detail = await api.note(n.id);
        setNotes((prev) => prev.map((item) =>
          item.id === n.id ? { ...item, content: detail.content, snapshot: detail.snapshot } : item,
        ));
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : "加载正文失败";
        toast.error(msg);
        setOpenId(null);
      } finally {
        setLoadingContent(null);
      }
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const next = await deleteNote(id);
      setNotes(next);
      if (openId === id) setOpenId(null);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "删除失败");
    }
  };

  const handleClear = async () => {
    if (!confirm("清空所有研究记录？")) return;
    try {
      await clearNotes();
      setNotes([]);
      setOpenId(null);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "清空失败");
    }
  };

  return (
    <div>
      <PageHeader
        title="研究记录"
        subtitle="把 AI 复盘 / 要点 / 问答沉淀在本地，随时回看。数据存本地服务 ~/.vibe-research/notes/。"
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/notes/compare"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm text-muted-foreground hover:border-primary/40 hover:text-primary"
            >
              <GitCompare className="h-4 w-4" /> 对比
            </Link>
            {notes.length > 0 && (
              <button onClick={handleClear}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive">
                <Trash2 className="h-4 w-4" /> 清空
              </button>
            )}
          </div>
        }
      />

      {loading ? (
        <GlassCard>
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> 加载中…
          </div>
        </GlassCard>
      ) : error ? (
        <GlassCard>
          <div className="py-10 text-center text-sm text-destructive">{error}</div>
        </GlassCard>
      ) : notes.length === 0 ? (
        <GlassCard>
          <div className="flex flex-col items-center gap-2 py-10 text-center text-sm text-muted-foreground">
            <NotebookPen className="h-8 w-8 text-muted-foreground/40" />
            还没有记录。在「每日复盘」「资讯雷达」或「问 AI」里点 <b className="text-foreground">「存入沉淀」</b> 保存分析结果。
          </div>
        </GlassCard>
      ) : (
        <div className="space-y-2">
          {notes.map((n) => {
            const open = openId === n.id;
            return (
              <GlassCard key={n.id} className="!p-0 overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-3">
                  <button onClick={() => handleToggle(n)} className="flex flex-1 items-center gap-2 text-left">
                    {open ? <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] ${KIND_COLOR[n.kind] || "bg-muted/50 text-muted-foreground"}`}>{n.kind}</span>
                    <span className="flex-1 truncate text-sm font-medium">{n.title}</span>
                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground/60">{fmt(n.ts)}</span>
                  </button>
                  <button onClick={() => handleDelete(n.id)} className="shrink-0 text-muted-foreground/60 hover:text-destructive" title="删除">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                {open && (
                  <div className="border-t border-border/40 px-4 py-3">
                    {loadingContent === n.id ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> 加载正文…
                      </div>
                    ) : (
                      <div className="prose prose-sm prose-invert max-w-none text-foreground">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{n.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}
              </GlassCard>
            );
          })}
        </div>
      )}

      <Disclaimer />
    </div>
  );
}
