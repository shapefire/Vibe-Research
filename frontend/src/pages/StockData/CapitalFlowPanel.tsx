import {
  Wallet, Trophy, CalendarClock, Boxes, MessageSquare,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import type {
  MarginRow, BlockTradeRow, HolderRow, DividendRow, FundFlowRow,
  DragonTiger, Lockup, Blocks, HotConcept, QaRow,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { yi, pct } from "./stockFormatters";
import { Metric } from "./ValuationPanel";

interface Props {
  margin: MarginRow[];
  blockT: BlockTradeRow[];
  holders: HolderRow[];
  dividend: DividendRow[];
  fundFlow: FundFlowRow[];
  dt: DragonTiger | null;
  lockup: Lockup | null;
  blocks: Blocks | null;
  hotCon: HotConcept[];
  qa: QaRow[];
}

export function CapitalFlowPanel({
  margin, blockT, holders, dividend, fundFlow, dt, lockup, blocks, hotCon, qa,
}: Props) {
  const hasCapital = margin.length > 0 || holders.length > 0 || fundFlow.length > 0 || dividend.length > 0;

  return (
    <>
      {hasCapital && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><Wallet className="h-4 w-4 text-primary" /> 资金面 · 筹码</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {margin[0] && <Metric k="融资余额" v={yi(margin[0].rzye)} sub={margin[0].date} />}
            {margin[0] && <Metric k="融券余额" v={yi(margin[0].rqye)} />}
            {holders[0] && <Metric k="股东户数" v={Number(holders[0].holder_num).toLocaleString()} sub={`环比 ${pct(holders[0].change_ratio)}`} />}
            {fundFlow.length > 0 && <Metric k="近20日主力净流入" v={yi(fundFlow.slice(-20).reduce((s, r) => s + r.main_net, 0))} />}
            {dividend[0] && <Metric k="最近派息(每10股)" v={`${dividend[0].bonus_rmb} 元`} sub={dividend[0].date} />}
          </div>
          {blockT.length > 0 && (
            <div className="mt-3 border-t border-border/40 pt-3">
              <p className="mb-2 text-xs text-muted-foreground">近期大宗交易（{blockT.length}）</p>
              <div className="space-y-1.5">
                {blockT.slice(0, 5).map((b, i) => (
                  <div key={i} className="flex items-center gap-3 text-xs">
                    <span className="w-20 shrink-0 font-mono text-muted-foreground">{b.date}</span>
                    <span className="w-14 shrink-0">{b.price} 元</span>
                    <span className={cn("w-20 shrink-0", b.premium_pct >= 0 ? "text-danger" : "text-success")}>折溢 {b.premium_pct}%</span>
                    <span className="flex-1 truncate text-muted-foreground">买 {b.buyer} · 卖 {b.seller}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <p className="mt-3 text-[11px] text-muted-foreground/60">资金/筹码为公开客观数据，仅供了解该股当前状态，不构成任何买卖建议。</p>
        </GlassCard>
      )}

      {dt && dt.records.length > 0 && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><Trophy className="h-4 w-4 text-primary" /> 龙虎榜（近30日 {dt.records.length} 次）</h3>
          <div className="space-y-2">
            {dt.records.slice(0, 6).map((r, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-border/40 pb-2 text-sm last:border-0">
                <span className="w-20 shrink-0 font-mono text-xs text-muted-foreground">{r.date}</span>
                <span className="flex-1 truncate">{r.reason}</span>
                <span className={cn("shrink-0 font-mono text-xs", r.net_buy >= 0 ? "text-danger" : "text-success")}>净买 {r.net_buy} 万</span>
              </div>
            ))}
          </div>
          {(dt.seats.buy.length > 0 || dt.seats.sell.length > 0) && (
            <div className="mt-3 grid gap-4 border-t border-border/40 pt-3 sm:grid-cols-2">
              <div>
                <p className="mb-1.5 text-xs font-medium text-danger">买入席位 TOP</p>
                {dt.seats.buy.map((s, i) => (
                  <div key={i} className="flex justify-between gap-2 text-xs text-muted-foreground"><span className="truncate">{s.name}</span><span className="shrink-0 font-mono">净{s.net}万</span></div>
                ))}
              </div>
              <div>
                <p className="mb-1.5 text-xs font-medium text-success">卖出席位 TOP</p>
                {dt.seats.sell.map((s, i) => (
                  <div key={i} className="flex justify-between gap-2 text-xs text-muted-foreground"><span className="truncate">{s.name}</span><span className="shrink-0 font-mono">净{s.net}万</span></div>
                ))}
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {lockup && (lockup.upcoming.length > 0 || lockup.history.length > 0) && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><CalendarClock className="h-4 w-4 text-primary" /> 限售解禁</h3>
          {lockup.upcoming.length > 0 ? (
            <div className="mb-3 rounded-lg border border-warning/30 bg-warning/5 p-3">
              <p className="mb-1.5 text-xs font-medium text-warning">未来 90 天待解禁（{lockup.upcoming.length}）</p>
              {lockup.upcoming.slice(0, 4).map((h, i) => (
                <div key={i} className="flex items-center gap-3 text-xs"><span className="w-20 shrink-0 font-mono text-muted-foreground">{h.date}</span><span className="flex-1 truncate">{h.type}</span><span className="shrink-0 text-muted-foreground">占比 {pct(h.ratio)}</span></div>
              ))}
            </div>
          ) : (
            <p className="mb-2 text-xs text-muted-foreground/70">未来 90 天无待解禁。</p>
          )}
          {lockup.history.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">历史解禁（近 {Math.min(lockup.history.length, 5)}）</p>
              {lockup.history.slice(0, 5).map((h, i) => (
                <div key={i} className="flex items-center gap-3 text-xs"><span className="w-20 shrink-0 font-mono text-muted-foreground">{h.date}</span><span className="flex-1 truncate text-muted-foreground">{h.type}</span></div>
              ))}
            </div>
          )}
        </GlassCard>
      )}

      {((blocks && blocks.concept_tags.length > 0) || hotCon.length > 0) && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><Boxes className="h-4 w-4 text-primary" /> 板块归属 · 概念</h3>
          {blocks && blocks.concept_tags.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-1.5">
              {blocks.concept_tags.slice(0, 24).map((t, i) => (
                <span key={i} className="rounded-full border border-border/70 px-2 py-0.5 text-xs text-muted-foreground">{t}</span>
              ))}
            </div>
          )}
          {hotCon.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">当下热门概念命中</p>
              <div className="flex flex-wrap gap-1.5">
                {hotCon.slice(0, 12).map((h, i) => (
                  <span key={i} className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">{h.concept}</span>
                ))}
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {qa.filter((q) => q.answer).length > 0 && (
        <GlassCard className="mb-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold"><MessageSquare className="h-4 w-4 text-primary" /> 投资者互动（互动易）</h3>
          <div className="space-y-3">
            {qa.filter((q) => q.answer).slice(0, 5).map((q, i) => (
              <div key={i} className="border-b border-border/40 pb-3 text-sm last:border-0">
                <p className="text-muted-foreground"><span className="mr-1.5 rounded bg-muted/50 px-1.5 py-0.5 text-[10px]">问</span>{q.question}</p>
                <p className="mt-1"><span className="mr-1.5 rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary">答</span>{q.answer}</p>
                <p className="mt-1 text-[11px] text-muted-foreground/60">{q.ask_time}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </>
  );
}
