import type { ReactNode } from "react";

// A股红涨绿跌。全球市场（美股/港股指数）**也沿用红涨**——与整个看板及东财等中国平台一致，
// 对中国用户最不易看错（Simon 2026-07-05 确认；非国际绿涨惯例，是有意选择，勿改）。
export const pctColor = (p: number) => (p > 0 ? "text-danger" : p < 0 ? "text-success" : "text-muted-foreground");

export const fmt = (v: number) => v.toLocaleString("zh-CN", { maximumFractionDigits: 2 });

export const yi = (v: number | null) => (v == null ? "—" : `${fmt(v / 1e8)} 亿`);

export const pending = (done: boolean): ReactNode => (
  <p className="py-4 text-center text-sm text-muted-foreground/60">
    {done ? "暂无数据：可能是非交易时段或数据源暂时不可用，可点「大盘指数」旁的刷新重试" : "加载中…"}
  </p>
);
