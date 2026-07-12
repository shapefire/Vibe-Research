"""compare.py 单元测试。"""

from __future__ import annotations

import pytest

from compare import diff_snapshots, flatten_diff, swap_before_after


def test_diff_numeric_fields():
    a = {"quote": {"price": 1700.0, "pe": 28.0}}
    b = {"quote": {"price": 1680.0, "pe": 28.5}}
    flat = flatten_diff(diff_snapshots(a, b))
    assert flat["quote.price"]["delta"] == -20.0
    assert flat["quote.price"]["delta_pct"] == pytest.approx(-1.18, abs=0.01)
    assert flat["quote.pe"]["delta"] == pytest.approx(0.5)


def test_diff_missing_key():
    a = {"quote": {"price": 100}}
    b = {"quote": {"price": 110}, "extra": 1}
    flat = flatten_diff(diff_snapshots(a, b))
    assert flat["extra"]["missing_in"] == "a"


def test_diff_zero_before_no_pct():
    a = {"x": 0}
    b = {"x": 10}
    flat = flatten_diff(diff_snapshots(a, b))
    assert flat["x"]["delta"] == 10
    assert flat["x"]["delta_pct"] is None


def test_diff_string_scalar():
    a = {"meta": {"name": "600519"}}
    b = {"meta": {"name": "600519"}}
    flat = flatten_diff(diff_snapshots(a, b))
    assert flat["meta.name"]["type"] == "scalar"
    assert "delta" not in flat["meta.name"]


def test_diff_nested_market():
    a = {"market": {"up_count": 2000, "limit_up": 40}}
    b = {"market": {"up_count": 2100, "limit_up": 45}}
    flat = flatten_diff(diff_snapshots(a, b))
    assert flat["market.up_count"]["delta"] == 100


def test_diff_max_depth():
    deep: dict = {}
    cur = deep
    for _ in range(15):
        cur["n"] = {}
        cur = cur["n"]
    cur["v"] = 1
    result = diff_snapshots(deep, deep)
    assert result is not None


def test_skip_captured_at():
    a = {"price": 1, "captured_at": "2026-01-01", "code": "600519"}
    b = {"price": 2, "captured_at": "2026-02-01", "code": "600519"}
    flat = flatten_diff(diff_snapshots(a, b))
    assert "captured_at" not in flat
    assert "code" not in flat
    assert "price" in flat


def test_swap_before_after():
    flat = {
        "quote.price": {"before": 100.0, "after": 110.0, "delta": 10.0, "delta_pct": 10.0, "type": "numeric"},
    }
    swapped = swap_before_after(flat)
    assert swapped["quote.price"]["before"] == 110.0
    assert swapped["quote.price"]["after"] == 100.0
    assert swapped["quote.price"]["delta"] == -10.0
    assert swapped["quote.price"]["delta_pct"] == -10.0


def test_flatten_diff_missing_in():
    a = {"x": 1}
    b = {"x": 2, "y": 3}
    flat = flatten_diff(diff_snapshots(a, b))
    assert flat["y"]["missing_in"] == "a"
