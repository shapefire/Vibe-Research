"""radar_cache_warm job 测试。"""
from __future__ import annotations

from unittest.mock import MagicMock

from jobs import radar_cache_warm


def test_radar_cache_warm_run(monkeypatch):
    called = {"n": 0}

    def fake_fetch():
        called["n"] += 1
        return {"industries": [], "stats": {"failed_sources": 0}}

    monkeypatch.setattr(radar_cache_warm.newsradar, "fetch_radar", fake_fetch)
    radar_cache_warm.run()
    assert called["n"] == 1


def test_radar_cache_warm_spec():
    spec = radar_cache_warm.spec()
    assert spec.name == "radar_cache_warm"
    assert spec.interval_sec == 3600
    assert spec.fn is not None
