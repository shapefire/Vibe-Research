from __future__ import annotations

import watchlist
import notes
import digest as digest_mod
from notes import NoteError

from tools.params import clamp_limit
from tools.registry import ToolSpec, register

_MCP = frozenset({"mcp"})
_CONTENT_DEFAULT = 20000


def _list_watchlist(args: dict, surface: str):
    return watchlist.get_state()


def _list_notes(args: dict, surface: str):
    limit = clamp_limit(surface, "list_notes", args.get("limit"))
    try:
        offset = int(args.get("offset") or 0)
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)
    kind = args.get("kind")
    q = args.get("q")
    result = notes.list_notes(
        kind=str(kind) if kind else None,
        q=str(q) if q else None,
        limit=limit,
        offset=offset,
    )
    items = result.get("items") or []
    total = int(result.get("total") or 0)
    truncated = offset + len(items) < total
    meta = {
        "truncated": truncated,
        "total": total,
        "returned": len(items),
        "offset": offset,
        "next_offset": offset + len(items) if truncated else offset,
    }
    if truncated:
        meta["hint"] = f"还有剩余笔记；使用 offset={meta['next_offset']} 继续取"
    return {"items": items, "total": total, "meta": meta}


def _get_note(args: dict, surface: str):
    note_id = str(args.get("note_id") or "").strip()
    if not note_id:
        return {"error": "缺少 note_id"}
    try:
        content_offset = int(args.get("content_offset") or 0)
    except (TypeError, ValueError):
        content_offset = 0
    try:
        content_limit = int(args.get("content_limit") or _CONTENT_DEFAULT)
    except (TypeError, ValueError):
        content_limit = _CONTENT_DEFAULT
    content_offset = max(0, content_offset)
    content_limit = max(1, min(content_limit, _CONTENT_DEFAULT))
    try:
        note = notes.get_note(note_id)
    except NoteError as e:
        return {"error": str(e)}
    content = note.get("content") or ""
    total = len(content)
    end = min(total, content_offset + content_limit)
    window = content[content_offset:end]
    truncated = end < total
    out = {**note, "content": window}
    meta = {
        "truncated": truncated,
        "total": total,
        "returned": len(window),
        "content_offset": content_offset,
        "next_content_offset": end if truncated else content_offset,
    }
    if truncated:
        meta["hint"] = f"正文未完；使用 content_offset={end} 继续取"
    out["meta"] = meta
    return out


def _get_latest_digest(args: dict, surface: str):
    d = digest_mod.load_latest()
    if d is None:
        return {"error": "暂无每日摘要"}
    return {"date": d.date, "markdown": digest_mod.to_markdown(d)}


def _register() -> None:
    register(ToolSpec(
        name="list_watchlist",
        description="列出当前自选股（只读：代码/市场/备注等客观字段）。",
        parameters={"type": "object", "properties": {}},
        handler=_list_watchlist,
        surfaces=_MCP,
    ))
    register(ToolSpec(
        name="list_notes",
        description="列出研究笔记元数据（不含正文；可用 kind/q/limit/offset 分页）。",
        parameters={
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "q": {"type": "string"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
            },
        },
        handler=_list_notes,
        surfaces=_MCP,
    ))
    register(ToolSpec(
        name="get_note",
        description="按 id 读取单条研究笔记（含正文；超长用 content_offset/content_limit 分页）。",
        parameters={
            "type": "object",
            "properties": {
                "note_id": {"type": "string"},
                "content_offset": {"type": "integer"},
                "content_limit": {"type": "integer"},
            },
            "required": ["note_id"],
        },
        handler=_get_note,
        surfaces=_MCP,
    ))
    register(ToolSpec(
        name="get_latest_digest",
        description="获取最新每日数据摘要（日期 + markdown 客观汇总）。",
        parameters={"type": "object", "properties": {}},
        handler=_get_latest_digest,
        surfaces=_MCP,
    ))


_register()
