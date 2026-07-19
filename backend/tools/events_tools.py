from __future__ import annotations

import astock

from tools.params import LIMITS, clamp_limit, validate_a_code
from tools.registry import ToolSpec, register
from tools import trim

_MCP = frozenset({"mcp"})
_QA_TEXT_CAP = 500


def _hard_max(surface: str, tool: str) -> int:
    return LIMITS.get((surface, tool), (15, 50))[1]


def _fetch_then_page(rows: list, *, surface: str, tool: str, args: dict) -> dict:
    limit = clamp_limit(surface, tool, args.get("limit"))
    try:
        offset = int(args.get("offset") or 0)
    except (TypeError, ValueError):
        offset = 0
    if not isinstance(rows, list):
        rows = list(rows or [])
    page, meta = trim.page_from_start(rows, limit=limit, offset=offset)
    return trim.attach_page_meta(page, meta)


def _clip_text(s: object, cap: int = _QA_TEXT_CAP) -> tuple[str, bool]:
    text = "" if s is None else str(s)
    if len(text) <= cap:
        return text, False
    return text[:cap], True


def _query_announcements(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.announcements(code, limit=_hard_max(surface, "query_announcements"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_announcements 执行失败：{e}"}
    return _fetch_then_page(rows, surface=surface, tool="query_announcements", args=args)


def _query_disclosure(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.disclosure(code)
    except astock.DependencyMissing as e:
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_disclosure 执行失败：{e}"}
    return _fetch_then_page(rows, surface=surface, tool="query_disclosure", args=args)


def _query_lockup(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        return astock.lockup_expiry(code)
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_lockup 执行失败：{e}"}


def _query_investor_qa(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.investor_qa(code, page_size=_hard_max(surface, "query_investor_qa"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_investor_qa 执行失败：{e}"}
    out = _fetch_then_page(rows, surface=surface, tool="query_investor_qa", args=args)
    any_field_trunc = False
    page = []
    for row in out["data"]:
        q, tq = _clip_text(row.get("question"))
        a, ta = _clip_text(row.get("answer"))
        any_field_trunc = any_field_trunc or tq or ta
        page.append({**row, "question": q, "answer": a})
    out["data"] = page
    if any_field_trunc:
        meta = dict(out.get("meta") or {})
        meta["field_truncated"] = True
        base_hint = meta.get("hint") or ""
        extra = "问答文本单字段已截断至 500 字"
        meta["hint"] = f"{base_hint}；{extra}" if base_hint else extra
        meta["truncated"] = True
        out["meta"] = meta
    return out


def _register() -> None:
    code_req = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "limit": {"type": "integer"},
            "offset": {"type": "integer"},
        },
        "required": ["code"],
    }
    for name, desc, handler, params in (
        ("query_announcements", "查个股近期公告列表（客观标题与时间；可用 limit/offset）。", _query_announcements, code_req),
        ("query_disclosure", "查个股信息披露列表（客观数据；可用 limit/offset）。", _query_disclosure, code_req),
        (
            "query_lockup",
            "查限售解禁日历（历史与未来待解禁客观数据）。",
            _query_lockup,
            {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        ),
        ("query_investor_qa", "查互动易问答（提问与回复客观文本；可用 limit/offset）。", _query_investor_qa, code_req),
    ):
        register(ToolSpec(name=name, description=desc, parameters=params, handler=handler, surfaces=_MCP))


_register()
