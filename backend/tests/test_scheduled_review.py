"""scheduled_review 单元测试。"""
from __future__ import annotations

from digest import DailyDigest
import scheduled_review


def _sample() -> DailyDigest:
    return DailyDigest(
        date="2026-07-12",
        market={"sh_index": {"close": 3200, "change_pct": -0.3}, "sz_index": {}, "global": {}, "sentiment": {}},
        watchlist_summary={"total": 0, "up": 0, "down": 0, "unconfigured": True, "items": []},
        portfolio_summary=None,
        intel_summary={"new_items": 0, "tracks": []},
        generated_at="2026-07-12T18:00:00+08:00",
    )


def test_llm_disabled_by_default(monkeypatch):
    monkeypatch.delenv("VR_DIGEST_INCLUDE_LLM", raising=False)
    assert scheduled_review.llm_config_from_env() is None


def test_build_review_context_contains_disclaimer_block():
    ctx = scheduled_review.build_review_context(_sample())
    assert "每日数据摘要" in ctx
    assert "不构成投资建议" in ctx


def test_run_for_digest_skips_without_llm(monkeypatch):
    monkeypatch.delenv("VR_DIGEST_INCLUDE_LLM", raising=False)
    assert scheduled_review.run_for_digest(_sample()) is None


def test_run_for_digest_with_mock_llm(monkeypatch):
    monkeypatch.setenv("VR_DIGEST_INCLUDE_LLM", "true")
    monkeypatch.setenv("VR_DIGEST_LLM_MODE", "api")
    monkeypatch.setenv("VR_DIGEST_LLM_API_KEY", "test-key")
    monkeypatch.setattr(scheduled_review, "generate_review", lambda _d: "今日盘面中性，涨跌互现。")
    import notes as notes_mod

    called: list[str] = []
    monkeypatch.setattr(notes_mod, "create_from_scheduled_review", lambda d, c: called.append(c) or {"id": f"review-{d.date}"})
    out = scheduled_review.run_for_digest(_sample())
    assert out == "今日盘面中性，涨跌互现。"
    assert called
