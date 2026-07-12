import type { IndexQuote, MarketOverview, NoteSnapshot, ShortTermEmotion } from "./api";

/** 采集每日复盘场景下的客观市场快照。 */
export function buildReviewSnapshot(
  indices: IndexQuote[],
  overview: MarketOverview | null,
  emotion: ShortTermEmotion | null,
): NoteSnapshot {
  const captured_at = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Shanghai" }).replace(" ", "T") + "+08:00";
  return {
    market: {
      indices: indices.map((i) => ({ name: i.name, price: i.price, change_pct: i.change_pct })),
      sentiment: overview?.sentiment
        ? {
            up: overview.sentiment.up,
            down: overview.sentiment.down,
            flat: overview.sentiment.flat,
            zt: overview.sentiment.zt,
            dt: overview.sentiment.dt,
            breadth: overview.sentiment.breadth,
            speculation: overview.sentiment.speculation,
          }
        : undefined,
      emotion: emotion
        ? {
            zt_count: emotion.zt_count,
            dt_count: emotion.dt_count,
            max_boards: emotion.max_boards,
            lianban_count: emotion.lianban_count,
            seal_rate: emotion.seal_rate,
            break_rate: emotion.break_rate,
            promotion_rate: emotion.promotion_rate,
          }
        : undefined,
    },
    captured_at,
  };
}
