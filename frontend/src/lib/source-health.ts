import type { HealthSource } from "@/lib/api";

export const CHAIN_LABELS: Record<string, string> = {
  quote: "实时行情",
  kline: "K 线",
  news: "新闻",
};

export const SOURCE_LABELS: Record<string, string> = {
  tencent: "腾讯财经",
  stale_cache: "内存缓存",
  eastmoney: "东方财富",
  mootdx: "mootdx",
  akshare: "akshare",
  baidu: "百度股市通",
};

export const CHAIN_STATUS_LABELS: Record<string, string> = {
  ok: "正常",
  degraded: "降级",
  down: "不可用",
  idle: "待探测",
};

export const SOURCE_STATUS_LABELS: Record<HealthSource["status"], string> = {
  ok: "正常",
  degraded: "降级",
  down: "不可用",
  missing: "未安装",
  idle: "待探测",
};

export function formatBadChains(
  chains: Record<string, "ok" | "degraded" | "down" | "idle">,
): string {
  return Object.entries(chains)
    .filter(([, status]) => status === "degraded" || status === "down")
    .map(([name]) => CHAIN_LABELS[name] ?? name)
    .join("、");
}
