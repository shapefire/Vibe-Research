from __future__ import annotations

import json
import math
from typing import Any


def json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else str(obj)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(x) for x in obj]
    return str(obj)


def page_from_end(rows: list, *, limit: int, offset: int) -> tuple[list, dict]:
    """Paginate from the end (newest-last lists like fund flow). offset skips already-returned newest items."""
    total = len(rows)
    offset = max(0, int(offset))
    limit = max(1, int(limit))
    end = total - offset
    if end <= 0:
        meta = {
            "truncated": False,
            "total": total,
            "returned": 0,
            "offset": offset,
            "next_offset": offset,
            "hint": "没有更多数据",
        }
        return [], meta
    start = max(0, end - limit)
    page = rows[start:end]
    truncated = start > 0
    next_offset = offset + len(page) if truncated else offset
    meta = {
        "truncated": truncated,
        "total": total,
        "returned": len(page),
        "offset": offset,
        "next_offset": next_offset if truncated else offset,
        "hint": (
            f"还有 {start} 条；使用 offset={next_offset} 或增大 limit 继续取"
            if truncated
            else ""
        ),
    }
    if not truncated:
        meta.pop("hint", None)
    return page, meta


def page_from_start(rows: list, *, limit: int, offset: int = 0) -> tuple[list, dict]:
    """Paginate from the start (newest-first / API list order)."""
    total = len(rows)
    offset = max(0, int(offset))
    limit = max(1, int(limit))
    if offset >= total:
        meta = {
            "truncated": False,
            "total": total,
            "returned": 0,
            "offset": offset,
            "next_offset": offset,
            "hint": "没有更多数据",
        }
        return [], meta
    page = rows[offset : offset + limit]
    truncated = offset + len(page) < total
    next_offset = offset + len(page)
    meta = {
        "truncated": truncated,
        "total": total,
        "returned": len(page),
        "offset": offset,
        "next_offset": next_offset if truncated else offset,
    }
    if truncated:
        meta["hint"] = f"还有 {total - next_offset} 条；使用 offset={next_offset} 或增大 limit 继续取"
    return page, meta


def attach_page_meta(data: Any, meta: dict) -> dict:
    return {"data": data, "meta": meta}


def fit_json_budget(payload: Any, budget: int) -> Any:
    """Shrink list payload['data'] from the front (older) until JSON fits; never slice the JSON string."""
    payload = json_safe(payload)

    def _len(p: Any) -> int:
        return len(json.dumps(p, ensure_ascii=False))

    if _len(payload) <= budget:
        return payload
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return {
            "data": None,
            "meta": {
                "truncated": True,
                "hint": "结果过大，请缩小 limit 或改用 MCP 面",
            },
        }
    data = list(payload["data"])
    meta = dict(payload.get("meta") or {})
    total = meta.get("total", len(data))
    while data and _len({"data": data, "meta": meta}) > budget:
        data = data[1:]  # drop older end of current page window
        meta["truncated"] = True
        meta["returned"] = len(data)
        meta["hint"] = "受 Chat token 预算裁剪；增大分页次数或改用 MCP"
    out = {"data": data, "meta": meta}
    if "total" not in meta:
        meta["total"] = total
    return out
