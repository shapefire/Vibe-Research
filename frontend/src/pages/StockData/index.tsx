import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { AskAiButton } from "@/components/ui/AskAiButton";
import { EarningsSnapshot } from "@/components/ui/EarningsSnapshot";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { api } from "@/lib/api";
import { useStockData } from "./useStockData";
import { buildStockContext } from "./buildStockContext";
import { StockSearchBar } from "./StockSearchBar";
import { QuoteOverview } from "./QuoteOverview";
import { ValuationPanel } from "./ValuationPanel";
import { FinancialPanel } from "./FinancialPanel";
import { ReportsNewsPanel } from "./ReportsNewsPanel";
import { CapitalFlowPanel } from "./CapitalFlowPanel";
import { GlobalStockPanel } from "./GlobalStockPanel";

export function StockData() {
  const [code, setCode] = useState("");
  const [compareNoteCount, setCompareNoteCount] = useState(0);
  const data = useStockData();
  const {
    val, reports, news, pctl, fin, anns, depNote,
    margin, blockT, holders, dividend, fundFlow, dt, lockup, blocks, hotCon, qa,
    gstock, quoteMeta, loading, error, search,
  } = data;

  const handleSearch = () => search(code);
  const aiContext = buildStockContext({ val, reports, anns, pctl, fin, gstock });

  useEffect(() => {
    if (!val || !/^\d{6}$/.test(code)) {
      setCompareNoteCount(0);
      return;
    }
    let cancelled = false;
    api.notesByTag(code, true)
      .then((data) => { if (!cancelled) setCompareNoteCount(data.total); })
      .catch(() => { if (!cancelled) setCompareNoteCount(0); });
    return () => { cancelled = true; };
  }, [val, code]);

  return (
    <div>
      <PageHeader
        title="个股数据"
        subtitle="行情 · 估值 · 研报 · 新闻 —— 客观数据配齐，判断交给你的 AI"
        actions={(val || gstock) && (
          <AskAiButton
            context={aiContext}
            label="让 AI 读这些数据"
            contextCode={!gstock && /^\d{6}$/.test(code) ? code : undefined}
            suggestions={gstock
              ? ["这家公司基本面怎么样", "盈利能力如何", "有什么风险"]
              : ["这个估值贵不贵", "机构一致预期怎么看", "近期研报的分歧点", "有什么风险"]}
          />
        )}
      />

      <StockSearchBar code={code} loading={loading} onChange={setCode} onSearch={handleSearch} />

      {compareNoteCount >= 2 && /^\d{6}$/.test(code) && (
        <div className="mb-4 rounded-lg border border-primary/20 bg-primary/5 px-4 py-2.5 text-sm text-muted-foreground">
          你有 {compareNoteCount} 条 {code} 的研究记录，{" "}
          <Link to={`/notes/compare?tag=${code}`} className="text-primary hover:underline">
            查看变化 →
          </Link>
        </div>
      )}

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      {gstock && <GlobalStockPanel gstock={gstock} />}

      {val && (
        <>
          <QuoteOverview val={val} quoteMeta={quoteMeta} />
          <EarningsSnapshot val={val} fin={fin} pctl={pctl} />
          {pctl && <ValuationPanel pctl={pctl} />}
          {fin && <FinancialPanel fin={fin} />}
          <ReportsNewsPanel reports={reports} anns={anns} news={news} depNote={depNote} />
          <CapitalFlowPanel
            margin={margin} blockT={blockT} holders={holders} dividend={dividend}
            fundFlow={fundFlow} dt={dt} lockup={lockup} blocks={blocks} hotCon={hotCon} qa={qa}
          />
        </>
      )}

      {!val && !error && !loading && !gstock && (
        <GlassCard>
          <div className="py-10 text-center text-sm text-muted-foreground">
            输入一个 6 位股票代码，拉取它的行情、估值、研报与新闻。<br />
            <span className="text-xs text-muted-foreground/60">数据来自公开源（腾讯行情 / 东财研报 / akshare）；Vibe-Research 不预置任何标的、不做推荐。</span>
          </div>
        </GlassCard>
      )}

      <Disclaimer />
    </div>
  );
}
