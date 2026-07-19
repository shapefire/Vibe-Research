"""digest 单元测试。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import digest
from compliance import assert_compliant


def _sample_digest() -> digest.DailyDigest:
    return digest.DailyDigest(
        date="2026-07-12",
        market={
            "sh_index": {"close": 3200.5, "change_pct": -0.3},
            "sz_index": {"close": 10500.2, "change_pct": -0.5},
            "global": {"dji": {"change_pct": 0.2}},
            "sentiment": {"up_count": 2100, "down_count": 2800, "limit_up": 45, "limit_down": 12},
        },
        watchlist_summary={"total": 1, "up": 1, "down": 0, "flat": 0, "unconfigured": False, "items": []},
        portfolio_summary=None,
        intel_summary={"new_items": 42, "tracks": [{"name": "AI算力", "count": 8}]},
        generated_at="2026-07-12T18:00:05+08:00",
    )


def test_generate_market_section(monkeypatch):
    monkeypatch.setattr(
        digest.astock,
        "index_quote",
        lambda: [
            {"name": "上证指数", "price": 3200, "change_pct": -0.3},
            {"name": "深证成指", "price": 10500, "change_pct": -0.5},
        ],
    )
    monkeypatch.setattr(
        digest.market,
        "get_overview",
        lambda: {"sentiment": {"up": 100, "down": 200, "zt_real": 10, "dt_real": 5}},
    )
    monkeypatch.setattr(
        digest.market,
        "get_global_indices",
        lambda: [{"key": "dji", "price": 1, "change_pct": 0.2}],
    )
    monkeypatch.setattr(digest.watchlist, "is_configured", lambda: False)
    monkeypatch.setattr(digest.pf, "get_portfolio", lambda: {"holdings": [], "totals": {}})
    monkeypatch.setattr(digest.newsradar, "get_cache_stats", lambda _d: {"new_items": 0, "tracks": []})

    d = digest.generate("2026-07-12")
    assert d.market["sh_index"]["close"] == 3200
    assert d.market["sentiment"]["up_count"] == 100


def test_watchlist_missing(monkeypatch):
    monkeypatch.setattr(digest.astock, "index_quote", lambda: [])
    monkeypatch.setattr(digest.market, "get_overview", lambda: {"sentiment": {}})
    monkeypatch.setattr(digest.market, "get_global_indices", lambda: [])
    monkeypatch.setattr(digest.watchlist, "is_configured", lambda: False)
    monkeypatch.setattr(digest.pf, "get_portfolio", lambda: {"holdings": [], "totals": {}})
    monkeypatch.setattr(digest.newsradar, "get_cache_stats", lambda _d: {"new_items": 0, "tracks": []})

    d = digest.generate("2026-07-12")
    assert d.watchlist_summary["total"] == 0
    assert d.watchlist_summary["unconfigured"] is True


def test_save_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(digest, "DIGESTS_DIR", tmp_path / "digests")
    d = _sample_digest()
    path = digest.save(d)
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["date"] == d.date


def test_to_markdown_contains_disclaimer():
    md = digest.to_markdown(_sample_digest())
    assert "不构成投资建议" in md
    assert "建议买入" not in md


def test_partial_failure_still_generates(monkeypatch):
    monkeypatch.setattr(digest.astock, "index_quote", lambda: [])
    monkeypatch.setattr(digest.market, "get_overview", lambda: {"sentiment": {}})
    monkeypatch.setattr(digest.market, "get_global_indices", MagicMock(side_effect=TimeoutError("timeout")))
    monkeypatch.setattr(digest.watchlist, "is_configured", lambda: False)
    monkeypatch.setattr(digest.pf, "get_portfolio", lambda: {"holdings": [], "totals": {}})
    monkeypatch.setattr(digest.newsradar, "get_cache_stats", lambda _d: {"new_items": 0, "tracks": []})

    d = digest.generate("2026-07-12")
    assert d.date == "2026-07-12"
    assert any(e["section"] == "market.global" for e in d.errors)


def test_digest_markdown_compliant():
    md = digest.to_markdown(_sample_digest())
    assert_compliant(md, context="daily_digest")


def test_load_latest(tmp_path, monkeypatch):
    dig_dir = tmp_path / "digests"
    monkeypatch.setattr(digest, "DIGESTS_DIR", dig_dir)
    digest.save(_sample_digest())
    loaded = digest.load_latest()
    assert loaded is not None
    assert loaded.date == "2026-07-12"
