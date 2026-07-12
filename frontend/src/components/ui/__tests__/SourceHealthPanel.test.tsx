import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SourceHealthPanel } from "../SourceHealthPanel";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    healthSources: vi.fn(),
  },
}));

describe("SourceHealthPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders degraded chain and source details", async () => {
    vi.mocked(api.healthSources).mockResolvedValue({
      sources: {
        tencent: { status: "down", last_ok: null, last_fail: "2026-07-12T10:00:00+08:00", last_error: "timeout" },
        stale_cache: { status: "idle", last_ok: "2026-07-12T09:55:00+08:00", last_fail: null, last_error: null },
        eastmoney: { status: "degraded", last_ok: "2026-07-12T09:00:00+08:00", last_fail: "2026-07-12T10:00:00+08:00", last_error: "403 rate limit" },
        mootdx: { status: "ok", last_ok: "2026-07-12T10:00:00+08:00", last_fail: null, last_error: null },
        akshare: { status: "missing", last_ok: null, last_fail: null, last_error: "not installed" },
      },
      chains: { quote: "degraded", kline: "ok", news: "down" },
      updated_at: "2026-07-12T10:00:01+08:00",
    });

    render(
      <MemoryRouter>
        <SourceHealthPanel />
      </MemoryRouter>,
    );

    expect(await screen.findByText("数据源状态")).toBeInTheDocument();
    expect(screen.getByText("实时行情")).toBeInTheDocument();
    expect(screen.getAllByText("降级").length).toBeGreaterThan(0);
    expect(screen.getByText("腾讯财经")).toBeInTheDocument();
    expect(screen.getByText("timeout")).toBeInTheDocument();
    expect(screen.getByText(/部分链路已降级或不可用/)).toBeInTheDocument();
  });

  it("shows error when health request fails", async () => {
    vi.mocked(api.healthSources).mockRejectedValue(new Error("network"));

    render(
      <MemoryRouter>
        <SourceHealthPanel />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/无法读取数据源状态/)).toBeInTheDocument();
  });
});
