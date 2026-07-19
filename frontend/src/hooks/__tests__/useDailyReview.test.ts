import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDailyReview } from "@/pages/DailyReview/useDailyReview";

vi.mock("@/lib/api", () => ({
  api: {
    marketOverview: vi.fn().mockResolvedValue({ sentiment: null, sectors: [] }),
    emotion: vi.fn().mockResolvedValue({ zt_count: 0 }),
    turnoverTop: vi.fn().mockResolvedValue({ stocks: [] }),
    indices: vi.fn().mockResolvedValue([]),
    globalIndices: vi.fn().mockResolvedValue([]),
    digestLatest: vi.fn().mockResolvedValue(null),
    reviewLatest: vi.fn().mockResolvedValue(null),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

describe("useDailyReview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers 7 API calls on mount", async () => {
    renderHook(() => useDailyReview());
    await waitFor(() => {
      expect(mockedApi.marketOverview).toHaveBeenCalled();
      expect(mockedApi.emotion).toHaveBeenCalled();
      expect(mockedApi.turnoverTop).toHaveBeenCalled();
      expect(mockedApi.indices).toHaveBeenCalled();
      expect(mockedApi.globalIndices).toHaveBeenCalled();
      expect(mockedApi.digestLatest).toHaveBeenCalled();
      expect(mockedApi.reviewLatest).toHaveBeenCalled();
    });
  });

  it("refreshAll refetches all queries", async () => {
    const { result } = renderHook(() => useDailyReview());
    await waitFor(() => expect(result.current.overview.done).toBe(true));
    vi.clearAllMocks();
    result.current.refreshAll();
    await waitFor(() => {
      expect(mockedApi.marketOverview).toHaveBeenCalled();
      expect(mockedApi.emotion).toHaveBeenCalled();
      expect(mockedApi.turnoverTop).toHaveBeenCalled();
      expect(mockedApi.indices).toHaveBeenCalled();
      expect(mockedApi.globalIndices).toHaveBeenCalled();
      expect(mockedApi.digestLatest).toHaveBeenCalled();
      expect(mockedApi.reviewLatest).toHaveBeenCalled();
    });
  });
});
