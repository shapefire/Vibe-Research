"""数据源 fallback 链模块。"""
from data_fetcher.base import AllSourcesFailed, DataSourceError, FetchResult, FetcherChain
from data_fetcher.registry import registry

__all__ = [
    "AllSourcesFailed",
    "DataSourceError",
    "FetchResult",
    "FetcherChain",
    "registry",
]
