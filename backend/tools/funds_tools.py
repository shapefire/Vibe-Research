from __future__ import annotations

import astock

from tools.params import LIMITS, clamp_limit, validate_a_code
from tools.registry import ToolSpec, register
from tools import trim

_SURFACES = frozenset({"chat", "mcp"})


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


def _hard_max(surface: str, tool: str) -> int:
    return LIMITS.get((surface, tool), (15, 50))[1]


def _query_fund_flow(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    limit = clamp_limit(surface, "query_fund_flow", args.get("limit"))
    try:
        offset = int(args.get("offset") or 0)
    except (TypeError, ValueError):
        offset = 0
    try:
        rows = astock.stock_fund_flow_120d(code)
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_fund_flow 执行失败：{e}"}
    if not rows:
        return trim.attach_page_meta([], {
            "truncated": False,
            "total": 0,
            "returned": 0,
            "offset": offset,
            "hint": "暂无数据，可能遭遇东财风控，请稍后重试",
        })
    page, meta = trim.page_from_end(rows, limit=limit, offset=offset)
    return trim.attach_page_meta(page, meta)


def _query_margin(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.margin_trading(code, page_size=_hard_max(surface, "query_margin"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_margin 执行失败：{e}"}
    return _fetch_then_page(rows, surface=surface, tool="query_margin", args=args)


def _query_block_trade(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        rows = astock.block_trade(code, page_size=_hard_max(surface, "query_block_trade"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_block_trade 执行失败：{e}"}
    return _fetch_then_page(rows, surface=surface, tool="query_block_trade", args=args)


def _query_dragon_tiger(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        return astock.dragon_tiger_board(code)
    except Exception as e:  # noqa: BLE001
        return {"error": f"query_dragon_tiger 执行失败：{e}"}


register(
    ToolSpec(
        name="query_fund_flow",
        description=(
            "查个股日级资金流（最近约 120 交易日）：主力/大/中/小/超大单净流入。"
            "默认返回最近一段；可用 limit/offset 分页续取。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6 位股票代码"},
                "limit": {"type": "integer", "description": "返回条数上限"},
                "offset": {"type": "integer", "description": "从最近往前的分页起点，0 为最近一页"},
            },
            "required": ["code"],
        },
        handler=_query_fund_flow,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_margin",
        description="查个股融资融券明细（日级）：融资余额/融资买入/融券余额/两融合计。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6 位股票代码"},
                "limit": {"type": "integer", "description": "返回条数上限"},
                "offset": {"type": "integer", "description": "分页起点，0 为第一页"},
            },
            "required": ["code"],
        },
        handler=_query_margin,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_dragon_tiger",
        description="查个股龙虎榜：近期上榜记录 + 最近一次买卖席位 TOP5 + 机构专用净买。",
        parameters={
            "type": "object",
            "properties": {"code": {"type": "string", "description": "6 位股票代码"}},
            "required": ["code"],
        },
        handler=_query_dragon_tiger,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_block_trade",
        description="查个股大宗交易：成交价/折溢价率/量/买卖方营业部。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6 位股票代码"},
                "limit": {"type": "integer", "description": "返回条数上限"},
                "offset": {"type": "integer", "description": "分页起点，0 为第一页"},
            },
            "required": ["code"],
        },
        handler=_query_block_trade,
        surfaces=_SURFACES,
    )
)
