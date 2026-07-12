import { api, type NoteSnapshot } from "./api";

/** 采集问 AI 场景下的客观行情/估值快照；失败不阻断保存。 */
export async function fetchNoteSnapshot(code: string): Promise<NoteSnapshot | undefined> {
  try {
    const [quoteMap, valuation, percentile] = await Promise.all([
      api.quote(code),
      api.valuation(code),
      api.percentile(code),
    ]);
    const quote = quoteMap[code];
    if (!quote) return undefined;
    const captured_at = new Date().toLocaleString("sv-SE", { timeZone: "Asia/Shanghai" }).replace(" ", "T") + "+08:00";
    return {
      code,
      quote: {
        price: quote.price,
        pe_ttm: quote.pe_ttm,
        change_pct: quote.change_pct,
      },
      valuation: valuation ? {
        pe_ttm: valuation.pe_ttm,
        pb: valuation.pb,
        mcap_yi: valuation.mcap_yi,
      } : undefined,
      valuation_pctile: percentile?.metrics?.pe_ttm
        ? { pe_5y: percentile.metrics.pe_ttm.percentile }
        : undefined,
      captured_at,
    };
  } catch {
    return undefined;
  }
}
