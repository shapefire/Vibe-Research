import { useState } from "react";
import { Check, BookmarkPlus, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { addNote } from "@/lib/notes";
import { fetchNoteSnapshot } from "@/lib/noteSnapshot";

interface Props {
  kind: string;
  title: string;
  content: string;
  contextCode?: string;
}

// 把一段 AI 结果存入「研究记录」（沉淀）。存本地服务，不上传。
export function SaveNoteButton({ kind, title, content, contextCode }: Props) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!content.trim()) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      const snapshot = contextCode ? await fetchNoteSnapshot(contextCode) : undefined;
      await addNote(kind, title, content, snapshot);
      setSaved(true);
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 0) toast.error("请先启动后端（uvicorn app:app --port 8900）");
        else if (e.status === 401) toast.error("请填写后端访问密钥");
        else if (e.status === 409) toast.error("已达笔记上限，请删除旧记录后再保存");
        else toast.error(e.message);
      } else {
        toast.error("保存失败");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <button
      onClick={handleSave}
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
