import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ScheduledReviewCard } from "../ScheduledReviewCard";
import type { NoteDetail } from "@/lib/api";

const sample: NoteDetail = {
  id: "review-2026-07-12",
  kind: "复盘",
  title: "定时复盘 2026-07-12",
  ts: 1,
  tags: ["scheduled"],
  content: "## 大盘\n今日指数小幅震荡。\n\n*不构成投资建议*",
};

describe("ScheduledReviewCard", () => {
  it("renders scheduled review preview", () => {
    render(
      <MemoryRouter>
        <ScheduledReviewCard review={sample} loading={false} done={true} error={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText("定时复盘 2026-07-12")).toBeInTheDocument();
    expect(screen.getByText(/大盘/)).toBeInTheDocument();
  });

  it("shows hint when no review", () => {
    render(
      <MemoryRouter>
        <ScheduledReviewCard review={null} loading={false} done={true} error={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/今日尚无定时复盘/)).toBeInTheDocument();
  });
});
