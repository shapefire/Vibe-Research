"""新闻 fallback 链：仅 akshare。"""
from __future__ import annotations

from data_fetcher.base import DataSourceError, FetcherChain


def _wrap_akshare(code: str, limit: int = 20) -> list[dict]:
    import astock

    try:
        return astock._fetch_news(code, limit=limit)
    except astock.DependencyMissing:
        raise
    except DataSourceError:
        raise
    except Exception as e:  # noqa: BLE001
        raise DataSourceError("akshare", str(e)) from e


NEWS_CHAIN = FetcherChain("news", [
    ("akshare", _wrap_akshare),
])
