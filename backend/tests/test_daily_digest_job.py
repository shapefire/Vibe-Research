"""daily_digest CLI 集成测试。"""
from __future__ import annotations

import sys

import pytest


def test_daily_digest_cli(tmp_path, monkeypatch):
    import digest
    import market
    import newsradar
    import portfolio as pf
    import watchlist

    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    dig_dir = tmp_path / "digests"
    monkeypatch.setattr(digest, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(digest, "DIGESTS_DIR", dig_dir)

    monkeypatch.setattr(digest.astock, "index_quote", lambda: [])
    monkeypatch.setattr(market, "get_overview", lambda: {"sentiment": {}})
    monkeypatch.setattr(market, "get_global_indices", lambda: [])
    monkeypatch.setattr(watchlist, "is_configured", lambda: False)
    monkeypatch.setattr(pf, "get_portfolio", lambda: {"holdings": [], "totals": {}})
    monkeypatch.setattr(newsradar, "get_cache_stats", lambda _d: {"new_items": 0, "tracks": []})
    import scheduled_review

    monkeypatch.setattr(scheduled_review, "run_for_digest", lambda _d: None)
    import notes as notes_mod

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(notes_mod, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(notes_mod, "NOTES_DIR", str(notes_dir))
    monkeypatch.setattr(notes_mod, "INDEX_FILE", str(notes_dir / "index.json"))

    from jobs import daily_digest as daily_digest_job

    monkeypatch.setattr(sys, "argv", ["daily_digest.py", "--date", "2026-07-12"])
    assert daily_digest_job.main() == 0
    assert (tmp_path / "digests" / "2026-07-12.json").exists()
    assert (tmp_path / "notes" / "index.json").exists()


def test_portfolio_no_embedded_scheduler():
    import portfolio as pf

    assert not hasattr(pf, "start_scheduler")
