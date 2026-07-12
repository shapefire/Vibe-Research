import { useCallback, useState } from "react";
import { api, ApiError, type CompareResult, type DiffEntry, type NoteMeta } from "@/lib/api";

export function formatValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "number") {
    if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(2);
  }
  return String(value);
}

export function formatDelta(entry: DiffEntry): string {
  if (entry.missing_in) return "—";
  if (entry.type === "scalar") {
    if (entry.before === entry.after) return "无变化";
    return `${formatValue(entry.before)} → ${formatValue(entry.after)}`;
  }
  if (entry.delta == null) return "—";
  const sign = entry.delta > 0 ? "+" : "";
  const deltaStr = `${sign}${formatValue(entry.delta)}`;
  if (entry.delta_pct != null) {
    const pctSign = entry.delta_pct > 0 ? "+" : "";
    return `${deltaStr} (${pctSign}${entry.delta_pct.toFixed(2)}%)`;
  }
  return deltaStr;
}

const DISCLAIMER =
  "以下为客观数据变化，不构成投资建议。Vibe-Research 不预置标的、不建议买卖。";

export function exportCompareMarkdown(result: CompareResult): string {
  const fmtTs = (ts: number) =>
    new Date(ts).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });

  const lines = [
    `# 研究记录对比`,
    "",
    `- **较早**：${result.note_a.title}（${fmtTs(result.note_a.ts)}）`,
    `- **较晚**：${result.note_b.title}（${fmtTs(result.note_b.ts)}）`,
    "",
  ];

  if (!result.comparable) {
    lines.push(`> 无法对比：${result.reason === "missing_snapshot" ? "缺少数据快照" : "无共有可对比指标"}`);
  } else {
    lines.push("| 指标 | 较早 | 较晚 | 变化 |", "| --- | --- | --- | --- |");
    for (const [path, entry] of Object.entries(result.diff)) {
      if (entry.missing_in) continue;
      const label = DIFF_LABELS[path] ?? path;
      lines.push(
        `| ${label} | ${formatValue(entry.before)} | ${formatValue(entry.after)} | ${formatDelta(entry)} |`,
      );
    }
  }

  lines.push("", "---", "", DISCLAIMER);
  return lines.join("\n");
}

export const DIFF_LABELS: Record<string, string> = {
  "quote.price": "现价",
  "quote.pe_ttm": "PE(TTM)",
  "quote.change_pct": "涨跌幅",
  "valuation.pe_ttm": "估值 PE(TTM)",
  "valuation.pb": "PB",
  "valuation.mcap_yi": "市值(亿)",
  "valuation_pctile.pe_5y": "PE 5年分位",
  "valuation_pctile.pb_5y": "PB 5年分位",
  "market.sentiment.up": "上涨家数",
  "market.sentiment.down": "下跌家数",
  "market.sentiment.flat": "平盘家数",
  "market.sentiment.zt": "涨停",
  "market.sentiment.dt": "跌停",
  "market.sentiment.breadth": "大盘宽度",
  "market.sentiment.speculation": "题材投机",
  "market.emotion.zt_count": "涨停数",
  "market.emotion.dt_count": "跌停数",
  "market.emotion.max_boards": "最高连板",
  "market.emotion.lianban_count": "连板家数",
  "market.emotion.seal_rate": "封板率",
  "market.emotion.break_rate": "炸板率",
  "market.emotion.promotion_rate": "晋级率",
};

export function diffLabel(path: string): string {
  if (DIFF_LABELS[path]) return DIFF_LABELS[path];
  const idxMatch = path.match(/^market\.indices\.(\d+)\.(price|change_pct)$/);
  if (idxMatch) {
    const field = idxMatch[2] === "price" ? "点位" : "涨跌幅";
    return `指数#${Number(idxMatch[1]) + 1}${field}`;
  }
  return path;
}

export function useNoteCompare() {
  const [notes, setNotes] = useState<NoteMeta[]>([]);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadByTag = useCallback(async (tag: string) => {
    setLoadingNotes(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.notesByTag(tag, false);
      setNotes(data.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "加载笔记失败");
      setNotes([]);
    } finally {
      setLoadingNotes(false);
    }
  }, []);

  const loadReviewNotes = useCallback(async () => {
    setLoadingNotes(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.notes({ kind: "复盘", limit: 200 });
      setNotes(data.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "加载笔记失败");
      setNotes([]);
    } finally {
      setLoadingNotes(false);
    }
  }, []);

  const compare = useCallback(async (idA: string, idB: string) => {
    setLoadingCompare(true);
    setError(null);
    try {
      const data = await api.compareNotes(idA, idB);
      setResult(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "对比失败");
      setResult(null);
    } finally {
      setLoadingCompare(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    notes,
    result,
    loadingNotes,
    loadingCompare,
    error,
    loadByTag,
    loadReviewNotes,
    compare,
    reset,
  };
}
