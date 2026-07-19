"""Contract smoke: every registered tool executes under mocks without stubs."""
from __future__ import annotations

import importlib
from dataclasses import dataclass

from data_fetcher.base import FetchResult
import tools.events_tools as _events_tools
import tools.funds_tools as _funds_tools
import tools.fundamentals_tools as _fundamentals_tools
import tools.market_tools as _market_tools
import tools.personal_tools as _personal_tools
import tools.quote_tools as _quote_tools
from tools.registry import _REGISTRY, execute, mcp_tools


@dataclass
class _Digest:
    date: str = "2026-07-19"
    market: dict | None = None
    watchlist_summary: dict | None = None
    portfolio_summary: dict | None = None
    intel_summary: dict | None = None
    generated_at: str = ""
    partial: bool = False
    errors: list | None = None

    def __post_init__(self):
        self.market = self.market or {}
        self.watchlist_summary = self.watchlist_summary or {"total": 0, "items": []}
        self.intel_summary = self.intel_summary or {}
        self.errors = self.errors or []


MIN_ARGS = {
    "query_quote": {"codes": ["600519"]},
    "query_valuation": {"code": "600519"},
    "query_reports": {"code": "600519"},
    "query_news": {"code": "600519"},
    "query_global_stock": {"symbol": "AAPL"},
    "query_kline": {"code": "600519"},
    "query_market_overview": {},
    "query_radar": {},
    "query_fund_flow": {"code": "600519"},
    "query_margin": {"code": "600519"},
    "query_dragon_tiger": {"code": "600519"},
    "query_block_trade": {"code": "600519"},
    "query_market_emotion": {},
    "query_turnover_top": {},
    "query_hot_concepts": {"code": "600519"},
    "query_global_indices": {},
    "query_financials": {"code": "600519"},
    "query_finance": {"code": "600519"},
    "query_holders": {"code": "600519"},
    "query_dividend": {"code": "600519"},
    "query_industry": {"top": 10},
    "query_announcements": {"code": "600519"},
    "query_disclosure": {"code": "600519"},
    "query_lockup": {"code": "600519"},
    "query_investor_qa": {"code": "600519"},
    "list_watchlist": {},
    "list_notes": {},
    "get_note": {"note_id": "n1"},
    "get_latest_digest": {},
}


def setup_function():
    _REGISTRY.clear()
    for mod in (
        _quote_tools,
        _market_tools,
        _funds_tools,
        _fundamentals_tools,
        _events_tools,
        _personal_tools,
    ):
        importlib.reload(mod)


def _install_mocks(monkeypatch):
    import astock
    import gstock
    import market
    import newsradar
    import watchlist
    import notes
    import digest as digest_mod

    fr = lambda data="ok": FetchResult(data=data, source="mock", chain="mock")
    monkeypatch.setattr(astock, "fetch_quote", lambda codes: fr({"600519": {"price": 1}}))
    monkeypatch.setattr(astock, "full_valuation", lambda code: {"code": code, "pe": 10})
    monkeypatch.setattr(astock, "eastmoney_reports", lambda code, max_pages=1: [{"title": "r", "publishDate": "d", "orgSName": "o", "emRatingName": "x"}])
    monkeypatch.setattr(astock, "fetch_news", lambda code, limit=20: fr([{"新闻标题": "t", "发布时间": "d", "文章来源": "s"}]))
    monkeypatch.setattr(astock, "fetch_kline", lambda code, category=4, offset=60: fr([{"c": 1}]))
    monkeypatch.setattr(astock, "stock_fund_flow_120d", lambda code: [{"date": str(i)} for i in range(40)])
    monkeypatch.setattr(astock, "margin_trading", lambda code, page_size=30: [{"d": i} for i in range(page_size)])
    monkeypatch.setattr(astock, "block_trade", lambda code, page_size=20: [{"d": i} for i in range(page_size)])
    monkeypatch.setattr(astock, "dragon_tiger_board", lambda code, trade_date=None, look_back=30: {"records": []})
    monkeypatch.setattr(astock, "financials", lambda code: {"roe": 0.1})
    monkeypatch.setattr(astock, "finance", lambda code: {"field": 1})
    monkeypatch.setattr(astock, "holder_num_change", lambda code, page_size=10: [{"h": i} for i in range(page_size)])
    monkeypatch.setattr(astock, "dividend_history", lambda code, page_size=20: [{"d": i} for i in range(page_size)])
    monkeypatch.setattr(astock, "industry_comparison", lambda top_n=20: {"top": [], "bottom": [], "total": 0})
    monkeypatch.setattr(astock, "announcements", lambda code, limit=15: [{"t": i} for i in range(limit)])
    monkeypatch.setattr(astock, "disclosure", lambda code: [{"t": i} for i in range(25)])
    monkeypatch.setattr(astock, "lockup_expiry", lambda code, trade_date=None, forward_days=90: {"past": [], "future": []})
    monkeypatch.setattr(astock, "investor_qa", lambda code, page_size=30: [{"question": "q", "answer": "a"} for _ in range(page_size)])
    monkeypatch.setattr(astock, "hot_concepts", lambda code: [{"concept": "c"}])
    monkeypatch.setattr(gstock, "us_hk_stock", lambda symbol: {"symbol": symbol, "price": 1})
    monkeypatch.setattr(market, "get_overview", lambda: {"sentiment": {}, "sectors": [{"n": i} for i in range(5)], "updated": "t"})
    monkeypatch.setattr(market, "get_short_term_emotion", lambda: {"ladder": []})
    monkeypatch.setattr(market, "get_turnover_top", lambda: {"stocks": [{"code": "1"}]})
    monkeypatch.setattr(market, "get_global_indices", lambda: [{"name": "dji"}])
    monkeypatch.setattr(newsradar, "get_radar", lambda force=False: {"industries": [], "stats": {}})
    monkeypatch.setattr(watchlist, "get_state", lambda: {"items": [], "total": 0, "updated_at": None})
    monkeypatch.setattr(notes, "list_notes", lambda kind=None, q=None, limit=50, offset=0: {"items": [], "total": 0})
    monkeypatch.setattr(notes, "get_note", lambda nid: {"id": nid, "title": "t", "content": "body", "kind": "k"})
    monkeypatch.setattr(digest_mod, "load_latest", lambda: _Digest())
    monkeypatch.setattr(digest_mod, "to_markdown", lambda d: "# ok")


def test_every_registered_tool_smoke(monkeypatch):
    _install_mocks(monkeypatch)
    names = {t["name"] for t in mcp_tools("mcp")}
    assert len(names) == 29
    assert set(MIN_ARGS) == names
    for name in sorted(names):
        out = execute(name, MIN_ARGS[name], surface="mcp")
        assert isinstance(out, (dict, list)), name
        if isinstance(out, dict):
            assert "未实现" not in str(out)
            assert "NotImplemented" not in str(out)
            # Must not be bare stub empty-error for happy path
            if "error" in out:
                raise AssertionError(f"{name} returned error under mocks: {out}")


def test_margin_supports_offset_pagination(monkeypatch):
    import astock

    monkeypatch.setattr(astock, "margin_trading", lambda code, page_size=30: [{"i": i} for i in range(40)])
    p0 = execute("query_margin", {"code": "600519", "limit": 10}, surface="chat")
    assert p0["meta"]["returned"] == 10
    assert p0["meta"]["truncated"] is True
    assert p0["meta"]["next_offset"] == 10
    p1 = execute("query_margin", {"code": "600519", "limit": 10, "offset": 10}, surface="chat")
    assert {r["i"] for r in p0["data"]} & {r["i"] for r in p1["data"]} == set()


def test_page_from_start_covers_all():
    from tools import trim

    rows = [{"i": i} for i in range(45)]
    seen = []
    offset = 0
    while True:
        page, meta = trim.page_from_start(rows, limit=20, offset=offset)
        seen.extend(r["i"] for r in page)
        if not meta.get("truncated"):
            break
        offset = meta["next_offset"]
    assert seen == list(range(45))
