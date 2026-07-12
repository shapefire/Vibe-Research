"""API 验证/契约测（FastAPI TestClient）。大多在校验层就返回，不联网、可靠。"""
import pytest
from fastapi.testclient import TestClient

import app as app_module
import astock

client = TestClient(app_module.app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_health_sources_endpoint():
    r = client.get("/api/health/sources")
    assert r.status_code == 200
    body = r.json()
    assert "sources" in body
    assert "chains" in body
    assert "quote" in body["chains"]
    assert "kline" in body["chains"]
    assert "news" in body["chains"]


def test_quote_all_fail_returns_503(monkeypatch):
    from data_fetcher.base import AllSourcesFailed

    def _fail(codes):
        raise AllSourcesFailed("quote", [{"source": "tencent", "error": "down"}])

    monkeypatch.setattr(astock, "fetch_quote", _fail)
    r = client.get("/api/quote?codes=600519")
    assert r.status_code == 503
    body = r.json()
    assert "attempts" in body["detail"]


def test_quote_stale_meta(monkeypatch):
    from data_fetcher.base import FetchResult

    monkeypatch.setattr(
        astock,
        "fetch_quote",
        lambda codes: FetchResult(
            data={"600519": {"name": "茅台", "price": 1.0}},
            source="stale_cache",
            chain="quote",
            stale=True,
            cached_at="2026-07-12T10:00:00+08:00",
        ),
    )
    r = client.get("/api/quote?codes=600519")
    assert r.status_code == 200
    body = r.json()
    assert body["_meta"]["stale"] is True
    assert body["_meta"]["source"] == "stale_cache"


def test_health_sources_no_auth_when_api_key_set(monkeypatch):
    monkeypatch.setattr(app_module, "_API_KEY", "secret-key")
    r = client.get("/api/health/sources")
    assert r.status_code == 200


def test_kline_dependency_missing_501(monkeypatch):
    def _missing(code, **kw):
        raise astock.DependencyMissing("mootdx 未安装：pip install mootdx")

    monkeypatch.setattr(astock, "fetch_kline", _missing)
    r = client.get("/api/kline?code=600519")
    assert r.status_code == 501
    assert "mootdx" in r.json()["detail"]


def test_eastmoney_cached_stale_fallback(monkeypatch):
    import time as time_mod

    app_module._DC_CACHE[("margin", "600519")] = (time_mod.time() - 9999, [{"date": "2026-01-01", "rzye": 1.0}])
    monkeypatch.setattr(astock, "margin_trading", lambda code: (_ for _ in ()).throw(RuntimeError("403 rate limit")))
    r = client.get("/api/margin?code=600519")
    assert r.status_code == 200
    body = r.json()
    assert body["_meta"]["stale"] is True
    assert body["_meta"]["source"] == "eastmoney"
    assert len(body["data"]) == 1


@pytest.mark.parametrize("path", [
    "/api/quote?codes=abc",
    "/api/valuation?code=12",
    "/api/margin?code=notcode",
    "/api/holders?code=1234567",
    "/api/announcements?code=",
])
def test_bad_code_400(path):
    assert client.get(path).status_code == 400


def test_industry_top_range():
    assert client.get("/api/industry?top=2").status_code == 422   # ge=5
    assert client.get("/api/industry?top=999").status_code == 422  # le=50


def test_chat_empty_messages_400():
    r = client.post("/api/chat", json={"messages": [], "llm": {"model": "x", "baseURL": "http://x", "apiKey": "k"}})
    assert r.status_code == 400


def test_chat_api_missing_key_400():
    # API 接入缺 baseURL/apiKey → 400（在开流前拦下）
    r = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "llm": {"provider": "deepseek", "model": "deepseek-chat", "baseURL": "", "apiKey": ""},
    })
    assert r.status_code == 400


def test_chat_cli_not_installed_400():
    # 订阅接入选一个本机没装的 CLI → 400 明确提示（不静默失败）
    r = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "llm": {"provider": "cli-qwen", "model": "qwen-code", "baseURL": "", "apiKey": ""},
    })
    # qwen 一般未装 → 400；若恰好装了 qwen 则会进流式（放宽断言）
    assert r.status_code in (400, 200)


def test_global_stock_404(monkeypatch):
    """无法解析的美股/港股代码 → 404（不 500、不崩）。"""
    import gstock
    monkeypatch.setattr(gstock, "us_hk_stock", lambda q: {})
    assert client.get("/api/global/stock?symbol=ZZZZ").status_code == 404


def test_gstock_quote_full_null_shape():
    """行情取不到时 `_quote_from({})` 仍返回完整 null 形状（契合 GlobalQuote 类型），不是空 dict。"""
    import gstock
    q = gstock._quote_from({})
    assert set(q) == {"code", "name", "price", "open", "high", "low", "prev_close", "amount", "mcap", "change_pct"}
    assert all(v is None for v in q.values())


@pytest.mark.parametrize("path", ["/daily-review", "/stock-data", "/sectors/business-space"])
def test_spa_deep_link_fallback(path):
    """Docker 部署：刷新深链路由应回退 index.html，而非 FastAPI 404 JSON。"""
    r = client.get(path)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="root"' in r.text


def test_spa_missing_asset_returns_404():
    """缺失的 .js 资源仍返回真实 404，不走 SPA fallback。"""
    r = client.get("/assets/not-exist.js")
    assert r.status_code == 404


def test_spa_fallback_does_not_override_api():
    """SPA 挂载不影响 /api/* 路由。"""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
