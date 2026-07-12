"""行情 fallback 链：tencent → stale_cache。"""
from __future__ import annotations

import quote_cache
from data_fetcher.base import DataSourceError, FetcherChain, _StaleCacheResult


def _wrap_tencent(codes: list[str]) -> dict[str, dict]:
    import astock

    try:
        result = astock._fetch_quote_tencent(codes)
    except Exception as e:  # noqa: BLE001 — 统一转为 DataSourceError
        raise DataSourceError("tencent", str(e)) from e
    if not result:
        raise DataSourceError("tencent", "empty response")
    quote_cache.set_all(result)
    return result


def _quote_from_cache(codes: list[str]) -> _StaleCacheResult:
    out, cached_at, partial = quote_cache.get(codes)
    if not out:
        raise DataSourceError("stale_cache", "no cache")
    return _StaleCacheResult(data=out, _cached_at=cached_at, _partial=partial)


QUOTE_CHAIN = FetcherChain("quote", [
    ("tencent", _wrap_tencent),
    ("stale_cache", _quote_from_cache),
])
