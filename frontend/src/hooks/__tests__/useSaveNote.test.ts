import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSaveNote } from "../useSaveNote";
import { ApiError } from "@/lib/api";

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

vi.mock("@/lib/notes", () => ({
  addNote: vi.fn().mockResolvedValue([]),
}));

vi.mock("@/lib/noteSnapshot", () => ({
  fetchNoteSnapshot: vi.fn().mockResolvedValue({ code: "600519" }),
}));

import { addNote } from "@/lib/notes";

const mockedAddNote = vi.mocked(addNote);

describe("useSaveNote", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets saved=true on success", async () => {
    const { result } = renderHook(() => useSaveNote());
    await act(async () => {
      await result.current.save("复盘", "标题", "内容");
    });
    expect(result.current.saved).toBe(true);
    expect(mockedAddNote).toHaveBeenCalledWith("复盘", "标题", "内容", undefined);
  });

  it("sets error on failure", async () => {
    mockedAddNote.mockRejectedValueOnce(new ApiError("保存失败", 500));
    const { result } = renderHook(() => useSaveNote());
    await act(async () => {
      await result.current.save("复盘", "标题", "内容");
    });
    expect(result.current.saved).toBe(false);
    expect(result.current.error).toBe("保存失败");
  });
});
