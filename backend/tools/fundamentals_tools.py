from __future__ import annotations

import astock

from tools.params import LIMITS, clamp_limit, validate_a_code
from tools.registry import ToolSpec, register
from tools import trim

_MCP = frozenset({"mcp"})


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


def _query_financials(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        return astock.financials(code)
    except astock.DependencyMissing as e:
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_financials 执行失败：{e}"}


def _query_finance(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        data = astock.finance(code)
    except astock.DependencyMissing as e:
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_finance 执行失败：{e}"}
    if not data:
        return {"data": {}, "hint": "暂无季报财务快照"}
    return data


def _query_holders(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.holder_num_change(code, page_size=_hard_max(surface, "query_holders"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_holders 执行失败：{e}"}
    return _fetch_then_page(rows, surface=surface, tool="query_holders", args=args)


def _query_dividend(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.dividend_history(code, page_size=_hard_max(surface, "query_dividend"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_dividend 执行失败：{e}"}
    return _fetch_then_page(rows, surface=surface, tool="query_dividend", args=args)


def _query_industry(args: dict, surface: str):
    raw = args.get("top", 20)
    try:
        top = int(raw)
    except (TypeError, ValueError):
        top = 20
    top = max(5, min(50, top))
    try:
        return astock.industry_comparison(top_n=top)
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_industry 执行失败：{e}"}


def _register() -> None:
    common = {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}
    page_params = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "limit": {"type": "integer"},
            "offset": {"type": "integer"},
        },
        "required": ["code"],
    }
    for name, desc, handler, params in (
        ("query_financials", "查个股财务关键指标（最新报告期客观数据）。", _query_financials, common),
        ("query_finance", "查个股季报财务快照（客观字段）。", _query_finance, common),
        ("query_holders", "查股东户数变化（客观列表；可用 limit/offset 分页）。", _query_holders, page_params),
        ("query_dividend", "查分红送转历史（客观列表；可用 limit/offset 分页）。", _query_dividend, page_params),
        (
            "query_industry",
            "查全行业涨跌幅排名（板块级客观数据；参数 top 范围 5–50）。",
            _query_industry,
            {
                "type": "object",
                "properties": {"top": {"type": "integer", "description": "取前/后 N 个行业，默认 20"}},
            },
        ),
    ):
        register(ToolSpec(name=name, description=desc, parameters=params, handler=handler, surfaces=_MCP))


_register()
