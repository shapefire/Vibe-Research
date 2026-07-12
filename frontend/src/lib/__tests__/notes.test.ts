import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { addNote, deleteNote, loadNotes, clearNotes, type Note } from "../notes";

describe("notes", () => {
  beforeEach(() => {
    clearNotes();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with empty list", () => {
    expect(loadNotes()).toEqual([]);
  });

  it("addNote prepends new note with kind/title/content", () => {
    vi.setSystemTime(new Date("2026-07-12T10:00:00Z"));
    const list = addNote("复盘", "每日复盘 2026-07-12", "# 内容");
    expect(list).toHaveLength(1);
    expect(list[0].kind).toBe("复盘");
    expect(list[0].title).toBe("每日复盘 2026-07-12");
    expect(list[0].content).toBe("# 内容");
    expect(list[0].ts).toBe(Date.now());
    expect(list[0].id).toMatch(/^\d+-/);
  });

  it("addNote keeps newest first", () => {
    addNote("复盘", "第一条", "a");
    addNote("问AI", "第二条", "b");
    const notes = loadNotes();
    expect(notes[0].title).toBe("第二条");
    expect(notes[1].title).toBe("第一条");
  });

  it("deleteNote removes by id", () => {
    const list = addNote("复盘", "待删", "x");
    const id = list[0].id;
    addNote("复盘", "保留", "y");
    const after = deleteNote(id);
    expect(after).toHaveLength(1);
    expect(after[0].title).toBe("保留");
  });

  it("deleteNote returns unchanged list when id not found", () => {
    addNote("复盘", "唯一", "x");
    const after = deleteNote("nonexistent");
    expect(after).toHaveLength(1);
  });

  it("truncates to MAX 200 notes", () => {
    for (let i = 0; i < 210; i++) {
      addNote("复盘", `note-${i}`, `body-${i}`);
    }
    const notes = loadNotes();
    expect(notes).toHaveLength(200);
    expect(notes[0].title).toBe("note-209");
    expect(notes[199].title).toBe("note-10");
  });

  it("returns invalid JSON as empty array", () => {
    localStorage.setItem("vr-notes", "not-json");
    expect(loadNotes()).toEqual([]);
  });

  it("returns non-array JSON as empty array", () => {
    localStorage.setItem("vr-notes", JSON.stringify({ foo: 1 }));
    expect(loadNotes()).toEqual([]);
  });

  it("clearNotes removes all", () => {
    addNote("复盘", "a", "1");
    clearNotes();
    expect(loadNotes()).toEqual([]);
  });
});

describe("Note shape", () => {
  it("generates unique ids", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-12T10:00:00Z"));
    const a = addNote("k", "t1", "c1")[0] as Note;
    vi.setSystemTime(new Date("2026-07-12T10:00:01Z"));
    const b = addNote("k", "t2", "c2")[0] as Note;
    expect(a.id).not.toBe(b.id);
    vi.useRealTimers();
  });
});
