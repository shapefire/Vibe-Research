import { Check } from "lucide-react";
import type { NoteMeta } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  notes: NoteMeta[];
  selected: [string | null, string | null];
  onSelect: (id: string) => void;
}

function hasSnapshot(n: NoteMeta): boolean {
  return n.has_snapshot === true || (n.snapshot != null && typeof n.snapshot === "object" && Object.keys(n.snapshot).length > 0);
}

export function NotePicker({ notes, selected, onSelect }: Props) {
  const fmt = (ts: number) =>
    new Date(ts).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });

  if (notes.length === 0) {
    return <p className="py-4 text-center text-sm text-muted-foreground">暂无笔记</p>;
  }

  return (
    <ul className="space-y-1">
      {notes.map((n) => {
        const ok = hasSnapshot(n);
        const selIdx = selected.indexOf(n.id);
        const isSelected = selIdx >= 0;
        return (
          <li key={n.id}>
            <button
              type="button"
              disabled={!ok}
              onClick={() => ok && onSelect(n.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
                ok ? "border-border hover:border-primary/40 hover:bg-muted/20" : "cursor-not-allowed border-border/40 opacity-50",
                isSelected && "border-primary/50 bg-primary/5",
              )}
            >
              <span className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center rounded border text-[10px]",
                isSelected ? "border-primary bg-primary text-primary-foreground" : "border-border",
              )}>
                {isSelected ? <Check className="h-3 w-3" /> : selIdx === -1 ? "" : null}
              </span>
              <span className="shrink-0 rounded-full bg-muted/50 px-2 py-0.5 text-[10px] text-muted-foreground">{n.kind}</span>
              <span className="flex-1 truncate font-medium">{n.title}</span>
              <span className="shrink-0 font-mono text-[11px] text-muted-foreground/70">{fmt(n.ts)}</span>
              {!ok && (
                <span className="shrink-0 text-[10px] text-muted-foreground">缺少数据快照</span>
              )}
              {isSelected && (
                <span className="shrink-0 text-[10px] text-primary">{selIdx === 0 ? "较早" : "较晚"}</span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
