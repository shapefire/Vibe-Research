import { describe, it, expect, beforeEach } from "vitest";
import { parseCodes, addCodes, loadWatch, saveWatch } from "../watchlist";

describe("parseCodes", () => {
  it("parses comma-separated codes", () => {
    expect(parseCodes("600519, 000858")).toEqual(["600519", "000858"]);
  });

  it("parses newline and space separated codes", () => {
    expect(parseCodes("600519 000858\n300750")).toEqual(["600519", "000858", "300750"]);
  });

  it("deduplicates codes", () => {
    expect(parseCodes("600519,600519,000858")).toEqual(["600519", "000858"]);
  });

  it("ignores non-6-digit tokens", () => {
    expect(parseCodes("600519,12345,ABCDEF,00700")).toEqual(["600519"]);
  });

  it("returns empty for blank input", () => {
    expect(parseCodes("")).toEqual([]);
    expect(parseCodes("  , \n ")).toEqual([]);
  });

  it("handles Chinese顿号 and mixed separators", () => {
    expect(parseCodes("600519、000858，300750")).toEqual(["600519", "000858", "300750"]);
  });
});

describe("addCodes", () => {
  const existing = ["600519"];

  it("merges new codes and reports added count", () => {
    const { next, added } = addCodes(existing, "000858, 300750");
    expect(next).toEqual(["600519", "000858", "300750"]);
    expect(added).toBe(2);
  });

  it("skips duplicates in existing list", () => {
    const { next, added } = addCodes(existing, "600519, 000858");
    expect(next).toEqual(["600519", "000858"]);
    expect(added).toBe(1);
  });

  it("returns zero added when all already exist", () => {
    const { next, added } = addCodes(existing, "600519");
    expect(next).toEqual(["600519"]);
    expect(added).toBe(0);
  });

  it("works with empty existing list", () => {
    const { next, added } = addCodes([], "600519\n000858");
    expect(next).toEqual(["600519", "000858"]);
    expect(added).toBe(2);
  });
});

describe("loadWatch / saveWatch", () => {
  beforeEach(() => {
    localStorage.removeItem("vr-watchlist");
  });

  it("loadWatch returns empty by default", () => {
    expect(loadWatch()).toEqual([]);
  });

  it("saveWatch and loadWatch round-trip", () => {
    saveWatch(["600519", "000858"]);
    expect(loadWatch()).toEqual(["600519", "000858"]);
  });

  it("loadWatch filters invalid codes", () => {
    localStorage.setItem("vr-watchlist", JSON.stringify(["600519", "12345", "abc"]));
    expect(loadWatch()).toEqual(["600519"]);
  });

  it("loadWatch returns empty on invalid JSON", () => {
    localStorage.setItem("vr-watchlist", "bad");
    expect(loadWatch()).toEqual([]);
  });
});
