import { useCallback } from "react";
import { api } from "@/lib/api";
import { useApiQuery } from "@/hooks/useApiQuery";

export function useDailyReview() {
  const overview = useApiQuery(useCallback(() => api.marketOverview(), []), []);
  const emotion = useApiQuery(useCallback(() => api.emotion(), []), []);
  const turnover = useApiQuery(useCallback(() => api.turnoverTop(), []), []);
  const indices = useApiQuery(useCallback(() => api.indices(), []), []);
  const globalIdx = useApiQuery(useCallback(() => api.globalIndices(), []), []);
  const scheduledReview = useApiQuery(useCallback(() => api.reviewLatest(), []), []);
  const digest = useApiQuery(useCallback(() => api.digestLatest(), []), []);

  const refreshAll = useCallback(() => {
    overview.refetch();
    emotion.refetch();
    turnover.refetch();
    indices.refetch();
    globalIdx.refetch();
    scheduledReview.refetch();
    digest.refetch();
  }, [overview, emotion, turnover, indices, globalIdx, scheduledReview, digest]);

  return { overview, emotion, turnover, indices, globalIdx, scheduledReview, digest, refreshAll };
}
