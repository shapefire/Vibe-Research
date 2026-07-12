import type { DiffEntry } from "@/lib/api";
import { diffLabel, formatDelta, formatValue } from "@/hooks/useNoteCompare";

interface Props {
  diff: Record<string, DiffEntry>;
  noteATs: number;
  noteBTs: number;
}

export function DiffTable({ diff, noteATs, noteBTs }: Props) {
  const fmtTs = (ts: number) =>
    new Date(ts).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });

  const rows = Object.entries(diff).filter(([, e]) => !e.missing_in);

  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">无共有可对比指标</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border/60 text-left text-xs text-muted-foreground">
            <th className="pb-2 pr-4 font-medium">指标</th>
            <th className="pb-2 pr-4 font-medium">{fmtTs(noteATs)}（较早）</th>
            <th className="pb-2 pr-4 font-medium">{fmtTs(noteBTs)}（较晚）</th>
            <th className="pb-2 font-medium">变化</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([path, entry]) => (
            <tr key={path} className="border-b border-border/30">
              <td className="py-2.5 pr-4 text-foreground">{diffLabel(path)}</td>
              <td className="py-2.5 pr-4 font-mono text-muted-foreground">{formatValue(entry.before)}</td>
              <td className="py-2.5 pr-4 font-mono text-muted-foreground">{formatValue(entry.after)}</td>
              <td className="py-2.5 font-mono text-foreground">{formatDelta(entry)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
