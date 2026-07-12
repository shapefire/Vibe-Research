"""data_fetcher 单元测试（mock，不联网）。"""
from __future__ import annotations

import time

import pytest

import astock
import quote_cache
from data_fetcher.base import AllSourcesFailed, DataSourceError, FetcherChain
from data_fetcher.quote import QUOTE_CHAIN
from data_fetcher.kline import KLINE_CHAIN
from data_fetcher.news import NEWS_CHAIN
from data_fetcher.registry import registry


@pytest.fixture(autouse=True)
def _reset_registry():
    registry._states.clear()
    quote_cache.clear()
    yield
    registry._states.clear()
    quote_cache.clear()


def test_chain_first_provider_success():
    calls: list[str] = []

    def first():
        calls.append("first")
        return {"ok": True}

    def second():
        calls.append("second")
        return {"ok": False}

    chain = FetcherChain("test", [("a", first), ("b", second)])
    result = chain.fetch()
    assert result.data == {"ok": True}
    assert result.source == "a"
    assert calls == ["first"]


def test_chain_fallback_to_second():
    def first():
        raise DataSourceError("a", "timeout")

    def second():
        return {"cached": True}

    chain = FetcherChain("test", [("a", first), ("b", second)])
    result = chain.fetch()
    assert result.data == {"cached": True}
    assert result.source == "b"


def test_chain_all_failed():
    def fail_a():
        raise DataSourceError("a", "err-a")

    def fail_b():
        raise DataSourceError("b", "err-b")

    chain = FetcherChain("test", [("a", fail_a), ("b", fail_b)])
    with pytest.raises(AllSourcesFailed) as exc:
        chain.fetch()
    assert len(exc.value.attempts) == 2


def test_chain_dependency_missing_not_continue(monkeypatch):
    def missing():
        raise astock.DependencyMissing("mootdx 未安装")

    def second():
        return []

    chain = FetcherChain("kline", [("mootdx", missing), ("skip", second)])
    with pytest.raises(astock.DependencyMissing):
        chain.fetch()


def test_quote_chain_tencent_writes_cache(monkeypatch):
    monkeypatch.setattr(
        astock,
        "_fetch_quote_tencent",
        lambda codes: {codes[0]: {"name": "茅台", "price": 100.0}},
    )
    result = QUOTE_CHAIN.fetch(["600519"])
    assert result.source == "tencent"
    cached, _, _ = quote_cache.get(["600519"])
    assert "600519" in cached


def test_stale_cache_returns_with_ttl(monkeypatch):
    quote_cache.set_all({"600519": {"name": "茅台", "price": 99.0}})
    monkeypatch.setattr(astock, "_fetch_quote_tencent", lambda codes: (_ for _ in ()).throw(DataSourceError("tencent", "down")))
    result = QUOTE_CHAIN.fetch(["600519"])
    assert result.source == "stale_cache"
    assert result.stale is True
    assert result.data["600519"]["price"] == 99.0


def test_stale_cache_expired_raises(monkeypatch):
    quote_cache._QUOTE_CACHE["600519"] = (time.time() - 9999, {"name": "茅台", "price": 1.0})
    monkeypatch.setattr(astock, "_fetch_quote_tencent", lambda codes: (_ for _ in ()).throw(DataSourceError("tencent", "down")))
    with pytest.raises(AllSourcesFailed):
        QUOTE_CHAIN.fetch(["600519"])


def test_fetch_quote_integration(monkeypatch):
    monkeypatch.setattr(
        astock,
        "_fetch_quote_tencent",
        lambda codes: {codes[0]: {"name": "测试", "price": 10.0}},
    )
    result = astock.fetch_quote(["600519"])
    assert result.stale is False
    assert result.chain == "quote"


def test_kline_mootdx_only_success(monkeypatch):
    monkeypatch.setattr(astock, "_fetch_kline", lambda code, **kw: [{"date": "2026-01-01"}])
    result = KLINE_CHAIN.fetch("600519")
    assert result.source == "mootdx"


def test_kline_mootdx_fail_all_sources(monkeypatch):
    monkeypatch.setattr(
        astock,
        "_fetch_kline",
        lambda code, **kw: (_ for _ in ()).throw(RuntimeError("connection refused")),
    )
    with pytest.raises(AllSourcesFailed):
        KLINE_CHAIN.fetch("600519")


def test_kline_dependency_missing(monkeypatch):
    monkeypatch.setattr(
        astock,
        "_fetch_kline",
        lambda code, **kw: (_ for _ in ()).throw(astock.DependencyMissing("mootdx 未安装")),
    )
    with pytest.raises(astock.DependencyMissing):
        KLINE_CHAIN.fetch("600519")


def test_news_akshare_success(monkeypatch):
    monkeypatch.setattr(astock, "_fetch_news", lambda code, limit=20: [{"title": "新闻"}])
    result = NEWS_CHAIN.fetch("600519")
    assert result.source == "akshare"


def test_news_akshare_missing(monkeypatch):
    monkeypatch.setattr(
        astock,
        "_fetch_news",
        lambda code, limit=20: (_ for _ in ()).throw(astock.DependencyMissing("akshare 未安装")),
    )
    with pytest.raises(astock.DependencyMissing):
        NEWS_CHAIN.fetch("600519")


def test_registry_mark_ok_updates_status():
    registry.mark_ok("tencent")
    d = registry.to_dict()
    assert d["sources"]["tencent"]["status"] == "ok"
    assert d["sources"]["tencent"]["last_ok"]


def test_registry_mark_fail():
    registry.mark_fail("tencent", "timeout")
    d = registry.to_dict()
    assert d["sources"]["tencent"]["status"] == "down"
    assert d["sources"]["tencent"]["last_error"] == "timeout"


def test_stale_cache_partial_hit(monkeypatch):
    quote_cache.set_all({"600519": {"name": "茅台", "price": 99.0}})
    monkeypatch.setattr(astock, "_fetch_quote_tencent", lambda codes: (_ for _ in ()).throw(DataSourceError("tencent", "down")))
    result = QUOTE_CHAIN.fetch(["600519", "000001"])
    assert result.partial is True
    assert "600519" in result.data
    assert "000001" not in result.data


def test_chain_status_degraded():
    registry.mark_fail("tencent", "down")
    registry.mark_ok("stale_cache")
    assert registry.chain_status("quote") == "degraded"
