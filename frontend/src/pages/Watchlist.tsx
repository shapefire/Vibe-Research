import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, X, RefreshCw, Star } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { AskAiButton } from "@/components/ui/AskAiButton";
import { api, type Quote, type FetchMeta, type GlobalStock } from "@/lib/api";
import { loadWatch, addWatchRaw, removeWatch, migrateIfNeeded, type WatchItem } from "@/lib/watchlist";
import { cn } from "@/lib/utils";
import { StaleBadge } from "@/components/ui/StaleBadge";

const color = (v: number | undefined | null) =>
  v == null ? "text-muted-foreground" : v > 0 ? "text-danger" : v < 0 ? "text-success" : "text-muted-foreground";
const pct = (v: number | undefined | null) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`);

const MARKET_LABEL: Record<string, string> = {
  "a-share": "A股",
  us: "美股",
  hk: "港股",
  kr: "韩股",
};

type RowQuote = {
  name?: string;
  price?: number | null;
  change_pct?: number | null;
  pe_ttm?: number | null;
  pb?: number | null;
  turnover_pct?: number | null;
  unsupported?: boolean;
};

export function Watchlist() {
  const [items, setItems] = useState<WatchItem[]>([]);
  const [quotes, setQuotes] = useState<Record<string, RowQuote>>({});
  const [quoteMeta, setQuoteMeta] = useState<FetchMeta | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);

  const refreshQuotes = useCallback(async (list: WatchItem[]) => {
    if (!list.length) {
      setQuotes({});
      setQuoteMeta(null);
      return;
    }
    setLoading(true);
    const next: Record<string, RowQuote> = {};
    try {
      const aShare = list.filter((i) => i.market === "a-share").map((i) => i.symbol);
      if (aShare.length) {
        const { data, meta } = await api.quoteWithMeta(aShare.join(","));
        setQuoteMeta(meta ?? null);
        for (const c of aShare) {
          const q = data[c] as Quote | undefined;
          if (q) {
            next[c] = {
              name: q.name,
              price: q.price,
              change_pct: q.change_pct,
              pe_ttm: q.pe_ttm,
              pb: q.pb,
              turnover_pct: q.turnover_pct,
            };
          }
        }
      } else {
        setQuoteMeta(null);
      }

      const overseas = list.filter((i) => i.market === "us" || i.market === "hk");
      await Promise.all(
        overseas.map(async (i) => {
          try {
            const g: GlobalStock = await api.globalStock(i.symbol);
            next[i.symbol] = {
              name: g.name || g.quote?.name,
              price: g.quote?.price,
              change_pct: g.quote?.change_pct,
            };
          } catch {
            next[i.symbol] = { unsupported: false };
          }
        }),
      );

      for (const i of list.filter((x) => x.market === "kr")) {
        next[i.symbol] = { unsupported: true, name: i.symbol };
      }
      setQuotes(next);
    } catch {
      /* keep previous quotes */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const migrated = await migrateIfNeeded();
        const list = await loadWatch();
        if (cancelled) return;
        setItems(list);
        if (migrated > 0) setHint(`已迁移 ${migrated} 只自选股到服务端`);
        await refreshQuotes(list);
      } catch (e) {
        if (!cancelled) setBootError(e instanceof Error ? e.message : "加载自选失败");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshQuotes]);

  const add = async () => {
    if (!input.trim()) {
      setHint(null);
      return;
    }
    try {
      const { items: next, added } = await addWatchRaw(input);
      setItems(next);
      setInput("");
      setHint(added ? `已添加 ${added} 只` : "没识别到新的有效代码（可能已在自选里）");
      await refreshQuotes(next);
    } catch (e) {
      setHint(e instanceof Error ? e.message : "添加失败");
    }
  };

  const remove = async (symbol: string) => {
    try {
      const next = await removeWatch(symbol);
      setItems(next);
      await refreshQuotes(next);
    } catch (e) {
      setHint(e instanceof Error ? e.message : "删除失败");
    }
  };

  const aiContext = useMemo(
    () =>
      items.length
        ? "我的自选股（服务端本地）：\n" +
          items
            .map((i) => {
              const q = quotes[i.symbol];
              if (q?.unsupported) return `${i.symbol}（${MARKET_LABEL[i.market] || i.market}·行情暂不支持）`;
              return q?.price != null
                ? `${q.name || i.symbol}(${i.symbol}) 现价${q.price} ${pct(q.change_pct)}`
                : `${i.symbol}（行情未取到）`;
            })
            .join("\n")
        : "还没有自选股。",
    [items, quotes],
  );

  return (
    <div>
      <PageHeader
        title="自选股"
        subtitle="批量添加、一屏总览。数据存本地服务端 ~/.vibe-research，不上传。"
        actions={
          items.length > 0 && (
            <AskAiButton
              context={aiContext}
              label="让 AI 读自选"
              suggestions={["这几只里哪些估值偏高", "帮我按赛道分组看看", "各自最大的风险点是什么"]}
            />
          )
        }
      />

      {bootError && (
        <p className="mb-3 text-sm text-destructive">{bootError}</p>
      )}

      <GlassCard className="mb-4">
        <label className="mb-1.5 block text-xs text-muted-foreground">
          批量添加 —— 支持 A 股 / 美股 / 港股 / 韩股（如 600519、AAPL、00700、005930.KS）
        </label>
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void add();
            }}
            rows={2}
            placeholder={"如：600519, AAPL, 00700\n005930.KS"}
            className="flex-1 resize-y rounded-lg border border-border bg-black/20 px-3 py-2 text-sm outline-none focus:border-primary/50"
          />
          <button
            onClick={() => void add()}
            className="inline-flex h-9 shrink-0 items-center gap-1.5 self-start rounded-lg bg-primary/15 px-4 text-sm font-medium text-primary shadow-glow hover:bg-primary/25"
          >
            <Plus className="h-4 w-4" /> 添加
          </button>
        </div>
        {hint && <p className="mt-2 text-xs text-muted-foreground/70">{hint}</p>}
      </GlassCard>

      <GlassCard glow>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="flex items-center gap-1.5 font-semibold">
            <Star className="h-4 w-4 text-primary" /> 自选总览
            <span className="text-xs font-normal text-muted-foreground">（{items.length}）</span>
            {quoteMeta?.stale && <StaleBadge partial={quoteMeta.partial} />}
          </h3>
          <button
            onClick={() => void refreshQuotes(items)}
            disabled={loading}
            className="text-muted-foreground hover:text-primary"
            title="刷新价格"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          </button>
        </div>
        {items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground/60">
            还没有自选股，用上面的框粘贴代码批量添加。
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 text-left text-xs text-muted-foreground">
                  {["名称", "代码", "市场", "现价", "涨跌%", "PE(TTM)", "PB", "换手%", ""].map((h) => (
                    <th key={h} className="whitespace-nowrap px-2 py-2 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((i) => {
                  const q = quotes[i.symbol];
                  return (
                    <tr key={i.symbol} className="border-b border-border/30">
                      <td className="px-2 py-2.5 font-medium">
                        {q?.unsupported ? "—" : q?.name || "—"}
                        {quoteMeta?.stale && !q && <StaleBadge partial />}
                      </td>
                      <td className="px-2 py-2.5 font-mono text-xs text-muted-foreground">{i.symbol}</td>
                      <td className="px-2 py-2.5 text-xs text-muted-foreground">
                        {MARKET_LABEL[i.market] || i.market}
                      </td>
                      <td className={cn("px-2 py-2.5 font-mono", color(q?.change_pct))}>
                        {q?.unsupported ? "暂不支持" : q?.price != null ? q.price : "—"}
                      </td>
                      <td className={cn("px-2 py-2.5 font-mono", color(q?.change_pct))}>
                        {q?.unsupported ? "—" : pct(q?.change_pct)}
                      </td>
                      <td className="px-2 py-2.5 font-mono text-muted-foreground">{q?.pe_ttm ?? "—"}</td>
                      <td className="px-2 py-2.5 font-mono text-muted-foreground">{q?.pb ?? "—"}</td>
                      <td className="px-2 py-2.5 font-mono text-muted-foreground">{q?.turnover_pct ?? "—"}</td>
                      <td className="px-2 py-2.5">
                        <button
                          onClick={() => void remove(i.symbol)}
                          className="text-muted-foreground/50 hover:text-destructive"
                          title="移除"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <Disclaimer />
    </div>
  );
}
