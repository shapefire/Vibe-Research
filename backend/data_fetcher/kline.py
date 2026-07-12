"""K 线 fallback 链：仅 mootdx（Phase 1 无假 akshare fallback）。"""
from __future__ import annotations

from data_fetcher.base import DataSourceError, FetcherChain


def _wrap_mootdx(code: str, category: int = 4, offset: int = 60) -> list[dict]:
    import astock

    try:
        return astock._fetch_kline(code, category=category, offset=offset)
    except astock.DependencyMissing:
        raise
    except DataSourceError:
        raise
    except Exception as e:  # noqa: BLE001
        raise DataSourceError("mootdx", str(e)) from e


KLINE_CHAIN = FetcherChain("kline", [
    ("mootdx", _wrap_mootdx),
])
