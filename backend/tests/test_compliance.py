"""合规自动化检测单测。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compliance import (
    ComplianceViolation,
    DIGEST_FOOTER,
    PUSH_FOOTER,
    assert_compliant,
    scan_text,
    validate_system_prompt,
)
from chat import ANALYSIS_FRAMEWORK, SYSTEM_PROMPT

_FIXTURES = Path(__file__).parent / "fixtures" / "banned_outputs.json"


def _load_fixtures(key: str) -> list[str]:
    data = json.loads(_FIXTURES.read_text(encoding="utf-8"))
    return data[key]


# ---------------------------------------------------------------------------
# Prompt 完整性
# ---------------------------------------------------------------------------

def test_system_prompt_contains_required_fragments():
    missing = validate_system_prompt(SYSTEM_PROMPT)
    assert missing == [], f"SYSTEM_PROMPT 缺失合规句段: {missing}"


def test_validate_system_prompt_detects_missing():
    incomplete = "只做信息整理，不推荐任何具体买卖。"
    missing = validate_system_prompt(incomplete)
    assert "不预测" in missing
    assert "不给买卖时机" in missing
    assert "不承诺收益" in missing
    assert "不打分排名" in missing


def test_analysis_framework_compliant():
    assert_compliant(ANALYSIS_FRAMEWORK, context="ANALYSIS_FRAMEWORK")


# ---------------------------------------------------------------------------
# 扫描 API
# ---------------------------------------------------------------------------

def test_scan_text_empty():
    assert scan_text("") == []


def test_scan_text_returns_spans():
    hits = scan_text("建议买入该股票")
    assert len(hits) >= 1
    assert hits[0]["match"]
    assert hits[0]["pattern"]
    assert isinstance(hits[0]["span"], tuple)


def test_assert_compliant_passes_clean_text():
    assert_compliant("PE 28.5，处于近5年72%分位")


def test_assert_compliant_raises_with_context():
    with pytest.raises(ComplianceViolation) as exc_info:
        assert_compliant("建议买入", context="test_context")
    assert exc_info.value.context == "test_context"
    assert len(exc_info.value.matches) >= 1


# ---------------------------------------------------------------------------
# Fixtures 驱动
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", _load_fixtures("should_fail"))
def test_banned_phrases_detected(text):
    with pytest.raises(ComplianceViolation):
        assert_compliant(text)


@pytest.mark.parametrize("text", _load_fixtures("should_pass"))
def test_objective_statements_allowed(text):
    assert_compliant(text)


def test_fixtures_count():
    fail_cases = _load_fixtures("should_fail")
    pass_cases = _load_fixtures("should_pass")
    assert len(fail_cases) >= 15, f"should_fail 仅 {len(fail_cases)} 条，需 ≥15"
    assert len(pass_cases) >= 10, f"should_pass 仅 {len(pass_cases)} 条，需 ≥10"


# ---------------------------------------------------------------------------
# 06/07 预埋（模块未建时 skip）
# ---------------------------------------------------------------------------

def test_digest_template_compliant():
    assert DIGEST_FOOTER == "*纯数据摘要，不构成投资建议*"
    from digest import DISCLAIMER, DailyDigest, to_markdown

    assert DISCLAIMER == DIGEST_FOOTER
    digest = DailyDigest(
        date="2026-07-19",
        market={
            "sh_index": {"close": None, "change_pct": None},
            "sz_index": {"close": None, "change_pct": None},
            "global": {},
            "sentiment": {
                "up_count": None,
                "down_count": None,
                "limit_up": None,
                "limit_down": None,
            },
        },
        watchlist_summary={
            "total": 0,
            "up": 0,
            "down": 0,
            "unconfigured": True,
            "items": [],
        },
        portfolio_summary=None,
        intel_summary={"new_items": 0, "tracks": []},
        generated_at="2026-07-19T18:00:00+08:00",
    )
    md = to_markdown(digest)
    assert DIGEST_FOOTER in md
    assert_compliant(md, context="digest")


def test_push_template_compliant():
    from notify.render import FOOTER

    assert PUSH_FOOTER == "*纯数据摘要，不构成投资建议*"
    assert "不构成投资建议" in FOOTER
    assert_compliant(FOOTER, context="notify_footer")
