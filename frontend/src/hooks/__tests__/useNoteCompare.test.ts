import { describe, expect, it } from "vitest";
import { formatDelta, exportCompareMarkdown } from "@/hooks/useNoteCompare";
import type { CompareResult } from "@/lib/api";

describe("formatDelta", () => {
  it("formats positive delta with plus sign", () => {
    expect(formatDelta({ delta: 4, delta_pct: 5.88, type: "numeric" })).toBe("+4 (+5.88%)");
  });

  it("formats negative delta", () => {
    expect(formatDelta({ delta: -20, delta_pct: -1.18, type: "numeric" })).toBe("-20 (-1.18%)");
  });
});

describe("exportCompareMarkdown", () => {
  it("includes disclaimer and diff table", () => {
    const result: CompareResult = {
      note_a: { id: "1", kind: "问AI", title: "A", ts: 1000 },
      note_b: { id: "2", kind: "问AI", title: "B", ts: 2000 },
      comparable: true,
      reason: null,
      diff: {
        "quote.price": { before: 100, after: 110, delta: 10, delta_pct: 10, type: "numeric" },
      },
    };
    const md = exportCompareMarkdown(result);
    expect(md).toContain("现价");
    expect(md).toContain("不构成投资建议");
    expect(md).not.toContain("改善");
  });
});
