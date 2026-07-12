"""A 股行情内存缓存 — 供 quote stale fallback 使用。"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

TZ8 = timezone(timedelta(hours=8))

_QUOTE_CACHE: dict[str, tuple[float, dict]] = {}
TTL = int(os.environ.get("VR_QUOTE_CACHE_TTL", "300"))


def set_all(quotes: dict[str, dict]) -> None:
    now = time.time()
    for code, q in quotes.items():
        _QUOTE_CACHE[code] = (now, q)


def get(codes: list[str]) -> tuple[dict[str, dict], str | None, bool]:
    """返回 (命中缓存的行情, 最早命中项 ISO 时间戳, 是否部分命中)。"""
    now = time.time()
    out: dict[str, dict] = {}
    oldest_ts: float | None = None
    for code in codes:
        hit = _QUOTE_CACHE.get(code)
        if hit and now - hit[0] < TTL:
            out[code] = hit[1]
            if oldest_ts is None or hit[0] < oldest_ts:
                oldest_ts = hit[0]
    cached_at = None
    if oldest_ts is not None:
        cached_at = datetime.fromtimestamp(oldest_ts, TZ8).isoformat(timespec="seconds")
    partial = 0 < len(out) < len(codes)
    return out, cached_at, partial


def clear() -> None:
    """测试用：清空缓存。"""
    _QUOTE_CACHE.clear()
