"""digest / jobs API 测试。"""
from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

import app as app_module
import digest

client = TestClient(app_module.app)


@pytest.fixture
def sample_digest_file(tmp_path, monkeypatch):
    dig_dir = tmp_path / "digests"
    monkeypatch.setattr(digest, "DIGESTS_DIR", dig_dir)
    d = digest.DailyDigest(
        date="2026-07-12",
        market={"sh_index": {"close": 1, "change_pct": 0}, "sz_index": {"close": 1, "change_pct": 0}, "global": {}, "sentiment": {}},
        watchlist_summary={"total": 0, "up": 0, "down": 0, "flat": 0, "unconfigured": True, "items": []},
        portfolio_summary=None,
        intel_summary={"new_items": 0, "tracks": []},
        generated_at="2026-07-12T18:00:00+08:00",
    )
    dig_dir.mkdir(parents=True)
    (dig_dir / "2026-07-12.json").write_text(json.dumps(asdict(d), ensure_ascii=False), encoding="utf-8")
    return d


def test_digest_latest_404(monkeypatch, tmp_path):
    monkeypatch.setattr(digest, "DIGESTS_DIR", tmp_path / "empty")
    resp = client.get("/api/digest/latest")
    assert resp.status_code == 404


def test_digest_latest_ok(sample_digest_file):
    resp = client.get("/api/digest/latest")
    assert resp.status_code == 200
    assert resp.json()["date"] == "2026-07-12"


def test_digest_by_date_ok(sample_digest_file):
    resp = client.get("/api/digest/2026-07-12")
    assert resp.status_code == 200
    assert resp.json()["date"] == "2026-07-12"


def test_jobs_status():
    resp = client.get("/api/jobs/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body
    assert body["scheduler_enabled"] is True


def test_jobs_run_daily_digest(monkeypatch, tmp_path):
    monkeypatch.setattr(digest, "DIGESTS_DIR", tmp_path / "digests")
    import notes as notes_mod

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(notes_mod, "NOTES_DIR", str(notes_dir))
    monkeypatch.setattr(notes_mod, "INDEX_FILE", str(notes_dir / "index.json"))

    monkeypatch.setattr(digest.astock, "index_quote", lambda: [])
    monkeypatch.setattr(digest.market, "get_overview", lambda: {"sentiment": {}})
    monkeypatch.setattr(digest.market, "get_global_indices", lambda: [])
    monkeypatch.setattr(digest.watchlist, "is_configured", lambda: False)
    monkeypatch.setattr(digest.pf, "get_portfolio", lambda: {"holdings": [], "totals": {}})
    monkeypatch.setattr(digest.newsradar, "get_cache_stats", lambda _d: {"new_items": 0, "tracks": []})
    import scheduled_review

    monkeypatch.setattr(scheduled_review, "run_for_digest", lambda _d: None)
    if app_module._scheduler:
        monkeypatch.setattr(app_module._scheduler, "is_job_running", lambda _n: False)

    resp = client.post("/api/jobs/daily-digest/run", json={"date": "2026-07-12"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert (tmp_path / "digests" / "2026-07-12.json").exists()


def test_jobs_run_unknown():
    resp = client.post("/api/jobs/unknown/run")
    assert resp.status_code == 404


def test_jobs_run_radar_cache_warm(monkeypatch):
    called = {"n": 0}

    def fake_run():
        called["n"] += 1

    import jobs.radar_cache_warm as rcw

    monkeypatch.setattr(rcw, "run", fake_run)
    resp = client.post("/api/jobs/radar-cache-warm/run")
    assert resp.status_code == 200
    assert called["n"] == 1


def test_jobs_run_requires_auth(monkeypatch):
    monkeypatch.setattr(app_module, "_API_KEY", "secret")
    resp = client.post("/api/jobs/daily-digest/run")
    assert resp.status_code == 401
    monkeypatch.setattr(app_module, "_API_KEY", "")


def test_review_latest_404():
    resp = client.get("/api/review/latest")
    assert resp.status_code == 404
