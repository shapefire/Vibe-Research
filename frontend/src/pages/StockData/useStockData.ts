import { useRef, useState, useCallback } from "react";
import {
  api, ApiError,
  type Valuation, type Report, type NewsItem, type ValPercentile,
  type Financials, type Announcement, type MarginRow, type BlockTradeRow, type HolderRow,
  type DividendRow, type FundFlowRow, type DragonTiger, type Lockup, type Blocks, type HotConcept, type QaRow,
  type GlobalStock, type FetchMeta,
} from "@/lib/api";

const emptyState = () => ({
  val: null as Valuation | null,
  reports: [] as Report[],
  news: [] as NewsItem[],
  pctl: null as ValPercentile | null,
  fin: null as Financials | null,
  anns: [] as Announcement[],
  depNote: null as string | null,
  margin: [] as MarginRow[],
  blockT: [] as BlockTradeRow[],
  holders: [] as HolderRow[],
  dividend: [] as DividendRow[],
  fundFlow: [] as FundFlowRow[],
  dt: null as DragonTiger | null,
  lockup: null as Lockup | null,
  blocks: null as Blocks | null,
  hotCon: [] as HotConcept[],
  qa: [] as QaRow[],
  gstock: null as GlobalStock | null,
  quoteMeta: null as FetchMeta | null,
});

export function useStockData() {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [state, setState] = useState(emptyState);
  const runIdRef = useRef(0);

  const search = useCallback(async (rawCode: string) => {
    const c = rawCode.trim().toUpperCase();
    if (!c) { setErr("请输入代码"); return; }
    const rid = ++runIdRef.current;
    setLoading(true);
    setErr(null);
    setState(emptyState());

    if (!/^\d{6}$/.test(c)) {
      try {
        const g = await api.globalStock(c);
        if (rid === runIdRef.current) setState((s) => ({ ...s, gstock: g }));
      } catch (e) {
        if (rid === runIdRef.current) setErr(e instanceof ApiError ? e.message : "查询失败");
      } finally {
        if (rid === runIdRef.current) setLoading(false);
      }
      return;
    }

    const patch = <K extends keyof ReturnType<typeof emptyState>>(key: K) =>
      (v: ReturnType<typeof emptyState>[K]) => {
        if (rid === runIdRef.current) setState((s) => ({ ...s, [key]: v }));
      };

    api.margin(c).then(patch("margin")).catch(() => {});
    api.blockTrade(c).then(patch("blockT")).catch(() => {});
    api.holders(c).then(patch("holders")).catch(() => {});
    api.dividend(c).then(patch("dividend")).catch(() => {});
    api.fundFlow(c).then(patch("fundFlow")).catch(() => {});
    api.dragonTiger(c).then(patch("dt")).catch(() => {});
    api.lockup(c).then(patch("lockup")).catch(() => {});
    api.blocks(c).then(patch("blocks")).catch(() => {});
    api.hotConcepts(c).then(patch("hotCon")).catch(() => {});
    api.investorQa(c).then(patch("qa")).catch(() => {});
    api.quoteWithMeta(c).then((r) => {
      if (rid === runIdRef.current) setState((s) => ({ ...s, quoteMeta: r.meta ?? null }));
    }).catch(() => {});

    try {
      const [v, r, p, f, a] = await Promise.all([
        api.valuation(c),
        api.reports(c).catch(() => []),
        api.percentile(c).catch(() => null),
        api.financials(c).catch(() => null),
        api.announcements(c).catch(() => []),
      ]);
      if (rid !== runIdRef.current) return;
      setState((s) => ({ ...s, val: v, reports: r, pctl: p, fin: f, anns: a }));
      try {
        const n = await api.news(c);
        if (rid === runIdRef.current) setState((s) => ({ ...s, news: n }));
      } catch (e) {
        if (rid === runIdRef.current && e instanceof ApiError && e.status === 501) {
          setState((s) => ({ ...s, depNote: e.message }));
        }
      }
    } catch (e) {
      if (rid !== runIdRef.current) return;
      setErr(e instanceof ApiError ? e.message : "查询失败");
    } finally {
      if (rid === runIdRef.current) setLoading(false);
    }
  }, []);

  return { ...state, loading, error: err, search };
}
