"""notify render + compliance。"""

from __future__ import annotations

from digest import DailyDigest
from compliance import assert_compliant
from notify.render import render_digest_brief, render_review_brief, FOOTER


def _sample() -> DailyDigest:
    return DailyDigest(
        date="2026-07-12",
        market={
            "sh_index": {"close": 3200.5, "change_pct": -0.3},
            "sz_index": {"close": 10500.0, "change_pct": 0.5},
            "global": {"dji": {"change_pct": 0.1}},
            "sentiment": {"up_count": 100, "down_count": 200, "limit_up": 10, "limit_down": 5},
        },
        watchlist_summary={"total": 2, "up": 1, "down": 1, "unconfigured": False, "items": []},
        portfolio_summary=None,
        intel_summary={"new_items": 3, "tracks": []},
        generated_at="2026-07-12T18:00:00+08:00",
    )


def test_render_digest_brief_compliant():
    msg = render_digest_brief(_sample(), "https://example.com/daily-review")
    assert "3200" in msg.body_markdown or "3,200" in msg.body_markdown
    assert msg.link.endswith("daily-review")
    assert_compliant(msg.body_markdown + "\n" + msg.footer, context="notify")
    assert "不构成投资建议" in FOOTER


def test_render_review_brief():
    msg = render_review_brief(_sample(), "今日盘面中性震荡，量能平平。", "http://127.0.0.1:5899/daily-review")
    assert "定时复盘" in msg.title
    assert "中性震荡" in msg.body_markdown
    assert_compliant(msg.body_markdown + "\n" + msg.footer, context="notify")
