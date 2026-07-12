"""新闻 fallback 链：akshare → 东财直连。"""
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


def _wrap_eastmoney(code: str, limit: int = 20) -> list[dict]:
    import astock

    try:
        return astock._fetch_news_eastmoney(code, limit=limit)
    except DataSourceError:
        raise
    except Exception as e:  # noqa: BLE001
        raise DataSourceError("eastmoney", str(e)) from e


NEWS_CHAIN = FetcherChain("news", [
    ("akshare", _wrap_akshare),
    ("eastmoney", _wrap_eastmoney),
])
