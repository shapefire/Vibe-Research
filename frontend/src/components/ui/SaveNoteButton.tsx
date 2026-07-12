import { Check, BookmarkPlus, Loader2 } from "lucide-react";
import { useSaveNote } from "@/hooks/useSaveNote";

interface Props {
  kind: string;
  title: string;
  content: string;
  contextCode?: string;
}

// 把一段 AI 结果存入「研究记录」（沉淀）。存本地服务，不上传。
export function SaveNoteButton({ kind, title, content, contextCode }: Props) {
  const { save, saving, saved } = useSaveNote();

  if (!content.trim()) return null;

  return (
    <button
      onClick={() => save(kind, title, content, contextCode)}
      disabled={saved || saving}
      className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-60"
    >
      {saving ? (
        <><Loader2 className="h-3.5 w-3.5 animate-spin" /> 保存中…</>
      ) : saved ? (
        <><Check className="h-3.5 w-3.5" /> 已存入沉淀</>
      ) : (
        <><BookmarkPlus className="h-3.5 w-3.5" /> 存入沉淀</>
      )}
    </button>
  );
}
