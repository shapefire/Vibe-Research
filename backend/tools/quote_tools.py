from __future__ import annotations

import astock
import gstock
from data_fetcher.base import AllSourcesFailed, FetchResult

from tools.params import clamp_limit, validate_a_code, validate_codes
from tools.registry import ToolSpec, register
from tools import trim

_SURFACES = frozenset({"chat", "mcp"})
_REPORT_FIELDS = ("title", "publishDate", "orgSName", "emRatingName")
_NEWS_FIELDS = ("新闻标题", "发布时间", "文章来源")


def _meta_from(result: FetchResult) -> dict:
    m = {"source": result.source, "stale": result.stale, "chain": result.chain}
    if result.cached_at:
        m["cached_at"] = result.cached_at
    if result.partial:
        m["partial"] = True
    return m


def _unwrap(result: FetchResult) -> dict:
    return {"data": result.data, "_meta": _meta_from(result)}


def _error(exc: Exception) -> dict:
    return {"error": str(exc)}


def _query_quote(args: dict, surface: str):
    codes = validate_codes(args.get("codes"))
    if codes is None:
        return {"error": "codes 必须是最多 20 个 6 位数字"}
    try:
        return _unwrap(astock.fetch_quote(codes))
    except astock.DependencyMissing as e:
        return _error(e)
    except AllSourcesFailed as e:
        return _error(e)


def _query_valuation(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        return astock.full_valuation(code)
    except astock.DependencyMissing as e:
        return _error(e)
    except AllSourcesFailed as e:
        return _error(e)
    except Exception as e:  # noqa: BLE001
        return _error(e)


def _query_reports(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    limit = clamp_limit(surface, "query_reports", args.get("limit"))
    try:
        rows = astock.eastmoney_reports(code, max_pages=1)
    except astock.DependencyMissing as e:
        return _error(e)
    except AllSourcesFailed as e:
        return _error(e)
    except Exception as e:  # noqa: BLE001
        return _error(e)
    trimmed = [{k: r.get(k) for k in _REPORT_FIELDS} for r in rows]
    try:
        offset = int(args.get("offset") or 0)
    except (TypeError, ValueError):
        offset = 0
    page, meta = trim.page_from_start(trimmed, limit=limit, offset=offset)
    return trim.attach_page_meta(page, meta)


def _query_news(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    limit = clamp_limit(surface, "query_news", args.get("limit"))
    try:
        result = astock.fetch_news(code, limit=limit)
    except astock.DependencyMissing as e:
        return _error(e)
    except AllSourcesFailed as e:
        return _error(e)
    data = [{k: r.get(k) for k in _NEWS_FIELDS} for r in (result.data or [])]
    return {"data": data, "_meta": _meta_from(result)}


def _query_global_stock(args: dict, surface: str):
    symbol = str(args.get("symbol") or "").strip()
    if not symbol:
        return {"error": "symbol 不能为空"}
    try:
        data = gstock.us_hk_stock(symbol)
    except Exception as e:  # noqa: BLE001
        return _error(e)
    if not data:
        return {"error": "未找到该美股/港股/韩股代码"}
    return data


def _query_kline(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    try:
        category = int(args.get("category", 4))
    except (TypeError, ValueError):
        category = 4
    offset = clamp_limit(surface, "query_kline", args.get("offset"))
    try:
        return _unwrap(astock.fetch_kline(code, category=category, offset=offset))
    except astock.DependencyMissing as e:
        return _error(e)
    except AllSourcesFailed as e:
        return _error(e)


register(
    ToolSpec(
        name="query_quote",
        description="查 A 股实时行情：现价/涨跌/PE/PB/市值/换手/涨跌停。可批量。",
        parameters={
            "type": "object",
            "properties": {
                "codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "6 位股票代码列表，如 ['600519','000858']",
                },
            },
            "required": ["codes"],
        },
        handler=_query_quote,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_valuation",
        description="查单只个股的完整估值：行情 + 机构一致预期 EPS + 前向PE/PEG/PE消化年数。",
        parameters={
            "type": "object",
            "properties": {"code": {"type": "string", "description": "6 位股票代码"}},
            "required": ["code"],
        },
        handler=_query_valuation,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_reports",
        description="查个股近期研报列表（标题/机构/评级/日期）。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6 位股票代码"},
                "limit": {"type": "integer", "description": "返回条数上限"},
                "offset": {"type": "integer", "description": "分页起点，0 为第一页"},
            },
            "required": ["code"],
        },
        handler=_query_reports,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_news",
        description="查个股近期新闻（标题/时间/来源）。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6 位股票代码"},
                "limit": {"type": "integer", "description": "返回条数上限"},
            },
            "required": ["code"],
        },
        handler=_query_news,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_global_stock",
        description=(
            "查美股 / 港股 / 韩股个股：行情（现价/涨跌/市值/成交额）+ 关键财务指标"
            "（韩股仅行情、无财务）。美股用字母代码(如 AAPL/NVDA)，港股用数字(如 00700)，"
            "韩股用 6 位数字加 .KS 后缀(如三星 005930.KS、SK海力士 000660.KS)。"
        ),
        parameters={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "美股字母代码 / 港股代码 / 韩股 XXXXXX.KS"}},
            "required": ["symbol"],
        },
        handler=_query_global_stock,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_kline",
        description="查 A 股 K 线（日/周/月/60 分钟）。category 4=日 5=周 6=月 11=60分钟。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6 位股票代码"},
                "category": {"type": "integer", "description": "K 线周期，默认 4（日）"},
                "offset": {"type": "integer", "description": "返回 K 线根数，默认 60，硬顶 120"},
            },
            "required": ["code"],
        },
        handler=_query_kline,
        surfaces=_SURFACES,
    )
)
