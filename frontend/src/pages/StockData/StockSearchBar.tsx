import { Search, Loader2 } from "lucide-react";

interface Props {
  code: string;
  loading: boolean;
  onChange: (code: string) => void;
  onSearch: () => void;
}

export function StockSearchBar({ code, loading, onChange, onSearch }: Props) {
  return (
    <div className="mb-5 flex gap-2">
      <input
        value={code}
        onChange={(e) => onChange(e.target.value.replace(/[^a-zA-Z0-9.]/g, "").toUpperCase().slice(0, 12))}
        onKeyDown={(e) => e.key === "Enter" && onSearch()}
        placeholder="A 股 6 位代码，或美股/港股/韩股（AAPL / 00700 / 005930.KS）"
        className="w-80 rounded-lg border border-border bg-black/20 px-3 py-2 text-sm outline-none focus:border-primary/50"
      />
      <button
        onClick={onSearch}
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-lg bg-primary/15 px-4 py-2 text-sm font-medium text-primary shadow-glow hover:bg-primary/25 disabled:opacity-50"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        查询
      </button>
    </div>
  );
}
