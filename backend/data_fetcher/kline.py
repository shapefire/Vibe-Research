"""K 线 fallback 链：mootdx → 东财 push2his → 百度日 K。"""
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


def _wrap_eastmoney(code: str, category: int = 4, offset: int = 60) -> list[dict]:
    import astock

    try:
        return astock._fetch_kline_eastmoney(code, category=category, offset=offset)
    except DataSourceError:
        raise
    except Exception as e:  # noqa: BLE001
        raise DataSourceError("eastmoney", str(e)) from e


def _wrap_baidu(code: str, category: int = 4, offset: int = 60) -> list[dict]:
    import astock

    try:
        return astock._fetch_kline_baidu(code, category=category, offset=offset)
    except DataSourceError:
        raise
    except Exception as e:  # noqa: BLE001
        raise DataSourceError("baidu", str(e)) from e


KLINE_CHAIN = FetcherChain("kline", [
    ("mootdx", _wrap_mootdx),
    ("eastmoney", _wrap_eastmoney),
    ("baidu", _wrap_baidu),
])
