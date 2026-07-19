from __future__ import annotations

import json

import tools  # noqa: F401 — register all domains
from tools import trim
from tools.params import clamp_limit, validate_a_code, validate_codes
from tools.registry import execute, openai_tools

CHAT_NAMES = {
    "query_quote", "query_valuation", "query_reports", "query_news", "query_global_stock",
    "query_kline", "query_market_overview", "query_radar", "query_fund_flow",
    "query_margin", "query_dragon_tiger", "query_block_trade",
}


def test_validate_a_code_ok():
    assert validate_a_code("600519") == "600519"


def test_validate_a_code_bad():
    assert validate_a_code("1") is None
    assert validate_a_code("abcdef") is None


def test_validate_codes_max_20():
    codes = [f"{i:06d}" for i in range(21)]
    assert validate_codes(codes) is None  # signals error to caller


def test_page_from_end_no_overlap():
    rows = [{"i": i} for i in range(120)]
    p0, meta0 = trim.page_from_end(rows, limit=20, offset=0)
    assert [r["i"] for r in p0] == list(range(100, 120))
    assert meta0["truncated"] is True
    assert meta0["total"] == 120
    assert meta0["returned"] == 20
    assert meta0["offset"] == 0
    assert meta0["next_offset"] == 20

    p1, meta1 = trim.page_from_end(rows, limit=20, offset=20)
    assert [r["i"] for r in p1] == list(range(80, 100))
    assert meta1["next_offset"] == 40
    assert {r["i"] for r in p0} & {r["i"] for r in p1} == set()


def test_page_from_end_covers_all():
    rows = [{"i": i} for i in range(45)]
    seen = []
    offset = 0
    while True:
        page, meta = trim.page_from_end(rows, limit=20, offset=offset)
        seen.extend(r["i"] for r in page)
        if not meta.get("truncated"):
            break
        offset = meta["next_offset"]
    assert sorted(seen) == list(range(45))


def test_fit_json_budget_keeps_valid_json():
    payload = {
        "data": [{"x": "y" * 200} for _ in range(50)],
        "meta": {"truncated": False, "total": 50, "returned": 50, "offset": 0},
    }
    out = trim.fit_json_budget(payload, budget=3000)
    s = json.dumps(out, ensure_ascii=False)
    assert len(s) <= 3000
    json.loads(s)
    assert out["meta"]["truncated"] is True
    assert out["meta"]["returned"] == len(out["data"])


def test_clamp_limit_chat_fund_flow():
    assert clamp_limit("chat", "query_fund_flow", None) == 20
    assert clamp_limit("chat", "query_fund_flow", 999) == 60
    assert clamp_limit("mcp", "query_fund_flow", None) == 60
    assert clamp_limit("mcp", "query_fund_flow", 999) == 120


def test_chat_surface_twelve():
    names = {t["function"]["name"] for t in openai_tools("chat")}
    assert names == CHAT_NAMES
    assert len(names) == 12


def test_fund_flow_pagination(monkeypatch):
    import astock

    rows = [{"date": str(i), "main_net": float(i)} for i in range(120)]
    monkeypatch.setattr(astock, "stock_fund_flow_120d", lambda code: rows)
    p0 = execute("query_fund_flow", {"code": "600519"}, surface="chat")
    assert p0["meta"]["returned"] == 20
    assert p0["meta"]["next_offset"] == 20
    p1 = execute("query_fund_flow", {"code": "600519", "offset": 20}, surface="chat")
    assert set(x["date"] for x in p0["data"]) & set(x["date"] for x in p1["data"]) == set()
