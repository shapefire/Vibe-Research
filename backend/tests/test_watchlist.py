"""watchlist 数据层单测（无外网）。"""

from __future__ import annotations

import json

import pytest

import watchlist


@pytest.fixture
def wl_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(watchlist, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(watchlist, "WL_FILE", str(tmp_path / "watchlist.json"))
    monkeypatch.setattr(watchlist, "WATCHLIST_FILE", str(tmp_path / "watchlist.json"))
    return tmp_path


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("600519", ("600519", "a-share")),
        ("600519.SH", ("600519", "a-share")),
        ("000001.SZ", ("000001", "a-share")),
        ("aapl", ("AAPL", "us")),
        ("AAPL", ("AAPL", "us")),
        ("700", ("00700", "hk")),
        ("00700", ("00700", "hk")),
        ("00700.HK", ("00700", "hk")),
        ("005930.KS", ("005930.KS", "kr")),
        ("XYZ!!!", None),
        ("", None),
    ],
)
def test_normalize_symbol(raw, expected):
    assert watchlist.normalize_symbol(raw) == expected


def test_parse_symbols_skips_invalid():
    got = watchlist.parse_symbols("600519, AAPL, XYZ!!!, 700")
    assert [x["symbol"] for x in got] == ["600519", "AAPL", "00700"]


def test_crud_and_cap(wl_dir, monkeypatch):
    monkeypatch.setenv("VR_WATCHLIST_MAX", "2")
    items, added = watchlist.add_raw("600519, AAPL")
    assert added == 2
    assert len(items) == 2
    with pytest.raises(watchlist.CapacityExceeded):
        watchlist.add_symbols(["00700"])
    items2, removed = watchlist.remove("AAPL")
    assert removed is True
    assert len(items2) == 1
    items3, removed2 = watchlist.remove("NOPE")
    assert removed2 is False
    assert len(items3) == 1


def test_put_rejects_invalid(wl_dir):
    with pytest.raises(watchlist.WatchlistError):
        watchlist.replace_all([{"symbol": "NOT_A_CODE", "market": "us"}])


def test_put_allows_empty(wl_dir):
    watchlist.add_symbols(["600519"])
    items = watchlist.replace_all([])
    assert items == []


def test_corrupt_quarantine(wl_dir):
    path = wl_dir / "watchlist.json"
    path.write_text("{bad", encoding="utf-8")
    items = watchlist.list_items()
    assert items == []
    assert (wl_dir / "watchlist.json.corrupt").exists() or list(wl_dir.glob("watchlist.json.corrupt*"))


def test_conflict_on_market_mismatch(wl_dir):
    watchlist.add_symbols(["600519"])
    # Force a weird conflict: same symbol stored, try different market via replace duplicate
    with pytest.raises(watchlist.WatchlistConflict):
        watchlist.replace_all(
            [
                {"symbol": "600519", "market": "a-share"},
                {"symbol": "600519", "market": "a-share"},
            ]
        )


def test_migrate_and_load_all(wl_dir):
    items, n = watchlist.migrate(["600519", "000001", "!!!"])
    assert n == 2
    assert watchlist.is_configured()
    rows = watchlist.load_all()
    assert {r["code"] for r in rows} == {"600519", "000001"}


def test_post_skips_invalid_in_symbols(wl_dir):
    items, added = watchlist.add_symbols(["600519", "!!!", "AAPL"])
    assert added == 2
    assert {i["symbol"] for i in items} == {"600519", "AAPL"}


def test_get_state(wl_dir):
    watchlist.add_raw("600519")
    st = watchlist.get_state()
    assert st["total"] == 1
    assert "updated_at" in st
