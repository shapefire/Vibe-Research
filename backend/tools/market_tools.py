from __future__ import annotations

import astock
import market
import newsradar

from tools.params import clamp_limit, validate_a_code
from tools.registry import ToolSpec, register
from tools import trim

_SURFACES = frozenset({"chat", "mcp"})
_MCP_ONLY = frozenset({"mcp"})
_RADAR_ITEM_FIELDS = ("title", "url", "time", "source")


def _trim_radar_item(item: dict) -> dict:
    return {k: item.get(k, "") for k in _RADAR_ITEM_FIELDS}


def _query_market_overview(args: dict, surface: str):
    limit = clamp_limit(surface, "query_market_overview", None)
    data = market.get_overview()
    sectors = data.get("sectors") or []
    out = {
        "sentiment": data.get("sentiment"),
        "sectors": sectors[:limit],
        "updated": data.get("updated"),
    }
    if len(sectors) <= limit:
        return out
    return {
        **out,
        "meta": {
            "truncated": True,
            "total": len(sectors),
            "returned": limit,
            "offset": 0,
            "hint": f"板块共 {len(sectors)} 个，本次返回前 {limit} 个",
        },
    }


def _query_radar(args: dict, surface: str):
    force = bool(args.get("force"))
    per_track = clamp_limit(surface, "query_radar", args.get("per_track"))
    raw = newsradar.get_radar(force=force)
    industries = []
    any_truncated = False
    track_totals: dict[str, int] = {}
    for ind in raw.get("industries") or []:
        items = ind.get("items") or []
        total = len(items)
        key = ind.get("key") or ind.get("name") or ""
        track_totals[key] = total
        if total > per_track:
            any_truncated = True
        industries.append({
            "key": ind.get("key"),
            "name": ind.get("name"),
            "accent": ind.get("accent"),
            "total": ind.get("total", total),
            "items": [_trim_radar_item(it) for it in items[:per_track]],
        })
    out: dict = {
        "generated_at": raw.get("generated_at"),
        "recent_days": raw.get("recent_days"),
        "industries": industries,
        "stats": raw.get("stats"),
    }
    if any_truncated:
        out["meta"] = {
            "truncated": True,
            "per_track": per_track,
            "track_totals": track_totals,
            "hint": f"每赛道仅返回 {per_track} 条；增大 per_track 获取更多",
        }
    return out


def _query_market_emotion(args: dict, surface: str):
    data = market.get_short_term_emotion()
    if not data:
        return {"data": {}, "hint": "暂无短线情绪数据，可能非交易日或数据源暂不可用"}
    return {"data": data}


def _query_turnover_top(args: dict, surface: str):
    data = market.get_turnover_top()
    if not data or not data.get("stocks"):
        return {"data": {}, "hint": "暂无成交额榜数据"}
    return {"data": data}


def _query_global_indices(args: dict, surface: str):
    rows = market.get_global_indices()
    if not rows:
        return {"data": [], "hint": "暂无全球指数数据"}
    return {"data": rows}


def _query_hot_concepts(args: dict, surface: str):
    code = validate_a_code(args.get("code"))
    if code is None:
        return {"error": "代码必须是 6 位数字"}
    rows = astock.hot_concepts(code)
    if not rows:
        return {"data": [], "hint": "暂无热门概念命中，可能非交易时段或数据源暂不可用"}
    return {"data": rows}


register(
    ToolSpec(
        name="query_market_overview",
        description="查 A 股市场总览：涨跌家数/涨跌停/活跃度 + 行业板块资金流（按净额降序）。",
        parameters={"type": "object", "properties": {}},
        handler=_query_market_overview,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_radar",
        description=(
            "查行业资讯雷达：各赛道最新资讯摘要（标题/链接/时间）。"
            "可分页：增大 per_track 获取更多；force=true 强制刷新缓存。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "force": {"type": "boolean", "description": "是否强制刷新缓存，默认 false"},
                "per_track": {"type": "integer", "description": "每赛道返回条数上限"},
            },
        },
        handler=_query_radar,
        surfaces=_SURFACES,
    )
)
register(
    ToolSpec(
        name="query_market_emotion",
        description="查 A 股短线情绪：连板梯队/封板率/炸板率/晋级率/涨跌停家数（客观公开榜单）。",
        parameters={"type": "object", "properties": {}},
        handler=_query_market_emotion,
        surfaces=_MCP_ONLY,
    )
)
register(
    ToolSpec(
        name="query_turnover_top",
        description="查全市场成交额榜 Top20（客观公开榜单，非推荐/非预测）。",
        parameters={"type": "object", "properties": {}},
        handler=_query_turnover_top,
        surfaces=_MCP_ONLY,
    )
)
register(
    ToolSpec(
        name="query_hot_concepts",
        description="查个股当下被市场归到哪些热门概念（东财概念命中，按热度降序）。",
        parameters={
            "type": "object",
            "properties": {"code": {"type": "string", "description": "6 位股票代码"}},
            "required": ["code"],
        },
        handler=_query_hot_concepts,
        surfaces=_MCP_ONLY,
    )
)
register(
    ToolSpec(
        name="query_global_indices",
        description="查全球主要指数快照（道指/标普/纳指/恒生/恒生科技等）。",
        parameters={"type": "object", "properties": {}},
        handler=_query_global_indices,
        surfaces=_MCP_ONLY,
    )
)
