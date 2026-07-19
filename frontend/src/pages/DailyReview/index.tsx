import { PageHeader } from "@/components/ui/PageHeader";
import { AskAiButton } from "@/components/ui/AskAiButton";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { useDailyReview } from "./useDailyReview";
import { MarketIndices } from "./MarketIndices";
import { WatchlistPanel } from "./WatchlistPanel";
import { ReviewAiSection } from "./ReviewAiSection";
import { ScheduledReviewCard } from "./ScheduledReviewCard";
import { MarketOverviewCards } from "./MarketOverviewCards";
import { SentimentPanel } from "./SentimentPanel";
import { TopVolumeTable } from "./TopVolumeTable";
import { SectorFlowPanel } from "./SectorFlowPanel";

export function DailyReview() {
  const { overview, emotion, turnover, indices, globalIdx, scheduledReview, refreshAll } = useDailyReview();

  const today = new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
  const idxList = indices.data ?? [];
  const dataSummary = idxList.length
    ? idxList.map((i) => `${i.name} ${i.price}（${i.change_pct > 0 ? "+" : ""}${i.change_pct}%）`).join("；")
    : "（指数数据未取到）";
  const sectors = overview.data?.sectors ?? [];

  return (
    <div>
      <PageHeader
        title="每日复盘"
        subtitle={`${today} · 大盘 / 情绪 / 板块资金一屏看全，交给你的 AI 做复盘`}
        actions={
          <AskAiButton
            context={`今日大盘数据：${dataSummary}`}
            label="问 AI"
            suggestions={["今天大盘怎么走", "哪些指数领涨领跌", "盘面有什么值得注意"]}
          />
        }
      />

      <ScheduledReviewCard
        review={scheduledReview.data}
        loading={scheduledReview.loading}
        done={scheduledReview.done}
        error={scheduledReview.error}
      />

      <MarketIndices
        indices={idxList}
        globalIdx={globalIdx.data ?? []}
        idxErr={!!indices.error}
        loading={indices.loading}
        onRefresh={refreshAll}
      />

      <WatchlistPanel />
      <ReviewAiSection
        dataSummary={dataSummary}
        today={today}
        indices={idxList}
        overview={overview.data}
        emotion={emotion.data}
      />
      <MarketOverviewCards overview={overview.data} done={overview.done} />
      <SentimentPanel emotion={emotion.data} done={emotion.done} />
      <TopVolumeTable turnover={turnover.data} done={turnover.done} />
      <SectorFlowPanel sectors={sectors} ovDone={overview.done} />

      <Disclaimer />
    </div>
  );
}
