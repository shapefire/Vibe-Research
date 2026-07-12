// 金额格式化（后端资金单位：元 / 万元）

export const yi = (v: number) => `${(v / 1e8).toFixed(2)} 亿`;

export const fmt = (v: number | null | undefined, suffix = "") =>
  v === null || v === undefined ? "—" : `${v}${suffix}`;

// A股红涨绿跌（中国平台看美港股也用此惯例）
export const pctColor = (p: number | null | undefined) =>
  p != null && p > 0 ? "text-danger" : p != null && p < 0 ? "text-success" : "text-muted-foreground";

export const pctStr = (p: number | null | undefined) => (p == null ? "—" : `${p > 0 ? "+" : ""}${p}%`);

export const curOf = (market: string) => (market === "HK" ? "港元" : market === "KR" ? "韩元" : "美元");
export const mktName = (m: string) => (m === "HK" ? "港股" : m === "KR" ? "韩股" : "美股");

export const bigMoney = (v: number | null, market: string) =>
  v == null ? "—" : v >= 1e12 ? `${(v / 1e12).toFixed(2)} 万亿${curOf(market)}` : `${(v / 1e8).toFixed(0)} 亿${curOf(market)}`;

export const round2 = (v: number | null | undefined, suffix = "") =>
  v == null ? "—" : `${Math.round(v * 100) / 100}${suffix}`;

export const pct = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(Number(v)) ? "—" : `${Number(v).toFixed(2)}%`;
