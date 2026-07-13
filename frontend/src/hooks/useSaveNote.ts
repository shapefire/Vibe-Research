import { useState, useCallback } from "react";
import { toast } from "sonner";
import { ApiError, type NoteSnapshot } from "@/lib/api";
import { addNote } from "@/lib/notes";
import { fetchNoteSnapshot } from "@/lib/noteSnapshot";

export function useSaveNote() {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useCallback(async (
    kind: string, title: string, content: string, contextCode?: string,
    options?: { snapshot?: NoteSnapshot },
  ) => {
    setSaving(true);
    setError(null);
    try {
      let snapshot: NoteSnapshot | undefined = options?.snapshot;
      if (!snapshot && contextCode) {
        snapshot = await fetchNoteSnapshot(contextCode);
      }
      await addNote(kind, title, content, snapshot, contextCode);
      setSaved(true);
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 0) toast.error("请先启动后端（uvicorn app:app --port 8900）");
        else if (e.status === 401) toast.error("请填写后端访问密钥");
        else if (e.status === 409) toast.error("已达笔记上限，请删除旧记录后再保存");
        else toast.error(e.message);
        setError(e.message);
      } else {
        toast.error("保存失败");
        setError("保存失败");
      }
    } finally {
      setSaving(false);
    }
  }, []);

  const reset = useCallback(() => setSaved(false), []);

  return { save, saving, saved, error, reset };
}
