import { describe, it, expect, beforeEach, vi } from "vitest";
import { parseCodes, addCodes, loadLocalWatch, saveWatch, migrateIfNeeded } from "../watchlist";

vi.mock("../api", () => ({
  api: {
    watchlist: vi.fn(),
    watchlistAdd: vi.fn(),
    watchlistRemove: vi.fn(),
    watchlistReplace: vi.fn(),
    watchlistMigrate: vi.fn(),
  },
}));

import { api } from "../api";

describe("parseCodes", () => {
  it("parses comma-separated A-share codes", () => {
    expect(parseCodes("600519, 000858")).toEqual(["600519", "000858"]);
  });

  it("parses multi-market tokens", () => {
    expect(parseCodes("600519 AAPL 700")).toEqual(["600519", "AAPL", "00700"]);
  });

  it("deduplicates codes", () => {
    expect(parseCodes("600519,600519,000858")).toEqual(["600519", "000858"]);
  });

  it("returns empty for blank input", () => {
    expect(parseCodes("")).toEqual([]);
    expect(parseCodes("  , \n ")).toEqual([]);
  });
});

describe("addCodes", () => {
  const existing = ["600519"];

  it("merges new codes and reports added count", () => {
    const { next, added } = addCodes(existing, "000858, 300750");
    expect(next).toEqual(["600519", "000858", "300750"]);
    expect(added).toBe(2);
  });
});

describe("loadLocalWatch / saveWatch", () => {
  beforeEach(() => {
    localStorage.removeItem("vr-watchlist");
    localStorage.removeItem("vr-watchlist-migrated");
  });

  it("loadLocalWatch returns empty by default", () => {
    expect(loadLocalWatch()).toEqual([]);
  });

  it("saveWatch and loadLocalWatch round-trip", () => {
    saveWatch(["600519", "000858"]);
    expect(loadLocalWatch()).toEqual(["600519", "000858"]);
  });

  it("loadLocalWatch filters invalid codes", () => {
    localStorage.setItem("vr-watchlist", JSON.stringify(["600519", "12345", "abc"]));
    expect(loadLocalWatch()).toEqual(["600519"]);
  });
});

describe("migrateIfNeeded", () => {
  beforeEach(() => {
    localStorage.removeItem("vr-watchlist");
    localStorage.removeItem("vr-watchlist-migrated");
    vi.mocked(api.watchlistMigrate).mockReset();
  });

  it("skips when already migrated", async () => {
    localStorage.setItem("vr-watchlist-migrated", "1");
    localStorage.setItem("vr-watchlist", JSON.stringify(["600519"]));
    expect(await migrateIfNeeded()).toBe(0);
    expect(api.watchlistMigrate).not.toHaveBeenCalled();
  });

  it("migrates local codes and sets flag only after success", async () => {
    localStorage.setItem("vr-watchlist", JSON.stringify(["600519", "000001"]));
    vi.mocked(api.watchlistMigrate).mockResolvedValue({
      items: [],
      total: 2,
      migrated: 2,
    });
    expect(await migrateIfNeeded()).toBe(2);
    expect(api.watchlistMigrate).toHaveBeenCalledWith(["600519", "000001"]);
    expect(localStorage.getItem("vr-watchlist-migrated")).toBe("1");
    // backup kept (Q-08-09)
    expect(JSON.parse(localStorage.getItem("vr-watchlist") || "[]")).toEqual(["600519", "000001"]);
  });

  it("does not set migrated flag when API fails", async () => {
    localStorage.setItem("vr-watchlist", JSON.stringify(["600519"]));
    vi.mocked(api.watchlistMigrate).mockRejectedValue(new Error("down"));
    await expect(migrateIfNeeded()).rejects.toThrow("down");
    expect(localStorage.getItem("vr-watchlist-migrated")).toBeNull();
  });
});
