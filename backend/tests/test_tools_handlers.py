from __future__ import annotations

import importlib

from data_fetcher.base import AllSourcesFailed, FetchResult
import tools.events_tools as _events_tools
import tools.funds_tools as _funds_tools
import tools.fundamentals_tools as _fundamentals_tools
import tools.market_tools as _market_tools
import tools.personal_tools as _personal_tools
import tools.quote_tools as _quote_tools
from tools.registry import _REGISTRY, execute, mcp_tools, openai_tools

_NEWS_TITLE = "新闻标题"
_NEWS_TIME = "发布时间"
_NEWS_SRC = "文章来源"


def setup_function():
    _REGISTRY.clear()
    importlib.reload(_quote_tools)
    importlib.reload(_market_tools)
    importlib.reload(_funds_tools)
    importlib.reload(_fundamentals_tools)
    importlib.reload(_events_tools)
    importlib.reload(_personal_tools)


def test_query_quote_unwrap(monkeypatch):
    import astock

    monkeypatch.setattr(
        astock,
        "fetch_quote",
        lambda codes: FetchResult(data={"600519": {"price": 1}}, source="tencent", chain="quote"),
    )
    out = execute("query_quote", {"codes": ["600519"]}, surface="chat")
    assert out["data"]["600519"]["price"] == 1
    assert out["_meta"]["source"] == "tencent"


def test_query_quote_bad_code():
    out = execute("query_quote", {"codes": ["1"]}, surface="chat")
    assert "error" in out


def test_query_kline_clamps_offset(monkeypatch):
    import astock

    seen: dict = {}

    def fake_fetch(code, category=4, offset=60):
        seen["offset"] = offset
        return FetchResult(data=[{"date": "2026-01-01"}], source="mootdx", chain="kline")

    monkeypatch.setattr(astock, "fetch_kline", fake_fetch)
    execute("query_kline", {"code": "600519", "offset": 999}, surface="chat")
    assert seen["offset"] == 120


def test_query_news_unwrap(monkeypatch):
    import astock

    monkeypatch.setattr(
        astock,
        "fetch_news",
        lambda code, limit=20: FetchResult(
            data=[{_NEWS_TITLE: "t", _NEWS_TIME: "2026-01-01", _NEWS_SRC: "x", "extra": "drop"}],
            source="akshare",
            chain="news",
        ),
    )
    out = execute("query_news", {"code": "600519"}, surface="mcp")
    assert out["data"][0][_NEWS_TITLE] == "t"
    assert "extra" not in out["data"][0]
    assert out["_meta"]["source"] == "akshare"


def test_query_global_stock_not_found(monkeypatch):
    import gstock

    monkeypatch.setattr(gstock, "us_hk_stock", lambda symbol: {})
    out = execute("query_global_stock", {"symbol": "NOPE"}, surface="chat")
    assert "error" in out


def test_query_quote_all_sources_failed(monkeypatch):
    import astock

    def fail(codes):
        raise AllSourcesFailed("quote", [{"source": "tencent", "error": "down"}])

    monkeypatch.setattr(astock, "fetch_quote", fail)
    out = execute("query_quote", {"codes": ["600519"]}, surface="mcp")
    assert "error" in out


def test_query_fund_flow_empty(monkeypatch):
    import astock

    monkeypatch.setattr(astock, "stock_fund_flow_120d", lambda code: [])
    out = execute("query_fund_flow", {"code": "600519"}, surface="chat")
    assert out["data"] == []
    assert "hint" in out["meta"]
    assert out["meta"]["hint"]


def test_query_radar_per_track(monkeypatch):
    import newsradar

    monkeypatch.setattr(
        newsradar,
        "get_radar",
        lambda force=False: {
            "industries": [{
                "key": "ai",
                "name": "AI",
                "accent": "#f00",
                "total": 8,
                "items": [
                    {"title": f"t{i}", "url": f"u{i}", "time": "2026-01-01", "source": "x", "extra": "drop"}
                    for i in range(8)
                ],
            }],
            "stats": {"industries": 1},
        },
    )
    out = execute("query_radar", {}, surface="chat")
    assert len(out["industries"][0]["items"]) == 5
    assert "extra" not in out["industries"][0]["items"][0]
    assert out["meta"]["truncated"] is True


def test_query_market_overview_truncates_sectors(monkeypatch):
    import market

    sectors = [{"name": f"s{i}"} for i in range(40)]
    monkeypatch.setattr(
        market,
        "get_overview",
        lambda: {"sentiment": {"up": 1}, "sectors": sectors, "updated": "2026-01-01"},
    )
    out = execute("query_market_overview", {}, surface="chat")
    assert len(out["sectors"]) == 30
    assert out["meta"]["truncated"] is True


def test_mcp_only_rejected_on_chat():
    out = execute("query_market_emotion", {}, surface="chat")
    assert "error" in out


def test_chat_surface_twelve():
    names = {t["function"]["name"] for t in openai_tools("chat")}
    assert len(names) == 12
    assert names == {
        "query_quote", "query_valuation", "query_reports", "query_news", "query_global_stock",
        "query_kline", "query_market_overview", "query_radar", "query_fund_flow",
        "query_margin", "query_dragon_tiger", "query_block_trade",
    }


def test_mcp_surface_twenty_nine():
    names = {t["name"] for t in mcp_tools("mcp")}
    assert len(names) == 29
    assert {"list_notes", "get_note", "get_latest_digest", "list_watchlist"} <= names


def test_fundamentals_financials(monkeypatch):
    import astock

    monkeypatch.setattr(astock, "financials", lambda code: {"roe": 0.2})
    out = execute("query_financials", {"code": "600519"}, surface="mcp")
    assert out["roe"] == 0.2
    assert "error" in execute("query_financials", {"code": "600519"}, surface="chat")


def test_events_announcements(monkeypatch):
    import astock

    monkeypatch.setattr(astock, "announcements", lambda code, limit=15: [{"title": "a"}] * 3)
    out = execute("query_announcements", {"code": "600519"}, surface="mcp")
    assert out["data"][0]["title"] == "a"


def test_personal_mcp_only():
    assert "error" in execute("list_notes", {}, surface="chat")
    assert "error" in execute("get_note", {"note_id": "x"}, surface="chat")


def test_list_watchlist(monkeypatch):
    import watchlist

    monkeypatch.setattr(watchlist, "get_state", lambda: {"items": [], "total": 0, "updated_at": None})
    assert execute("list_watchlist", {}, surface="mcp")["total"] == 0


def test_get_note_content_window(monkeypatch):
    import notes

    monkeypatch.setattr(
        notes,
        "get_note",
        lambda nid: {"id": nid, "title": "t", "content": "a" * 25000, "kind": "ask-ai"},
    )
    out = execute("get_note", {"note_id": "n1"}, surface="mcp")
    assert out["meta"]["truncated"] is True
    assert len(out["content"]) == 20000


def test_get_latest_digest_missing(monkeypatch):
    import digest as digest_mod

    monkeypatch.setattr(digest_mod, "load_latest", lambda: None)
    out = execute("get_latest_digest", {}, surface="mcp")
    assert "error" in out
