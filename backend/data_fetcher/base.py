"""数据源 fallback 链核心抽象。"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from data_fetcher.registry import registry

log = logging.getLogger("vibe.data_fetcher")


@dataclass(frozen=True)
class DataSourceError(Exception):
    """单源失败，chain 可继续尝试下一源。"""

    source: str
    reason: str

    def __str__(self) -> str:
        return f"{self.source}: {self.reason}"


@dataclass(frozen=True)
class AllSourcesFailed(Exception):
    """所有源均失败。"""

    endpoint: str
    attempts: list[dict[str, str]]

    def __str__(self) -> str:
        return f"{self.endpoint}: all sources failed ({len(self.attempts)} attempts)"


@dataclass(frozen=True)
class FetchResult:
    data: Any
    source: str
    chain: str
    stale: bool = False
    cached_at: str | None = None
    partial: bool = False


class FetcherChain:
    """按优先级依次尝试 provider，记录每源结果。"""

    def __init__(self, name: str, providers: list[tuple[str, Callable[..., Any]]]):
        self.name = name
        self.providers = providers

    def fetch(self, *args: Any, **kwargs: Any) -> FetchResult:
        attempts: list[dict[str, str]] = []
        for source_id, fn in self.providers:
            try:
                result = fn(*args, **kwargs)
                registry.mark_ok(source_id)
                stale = source_id == "stale_cache"
                cached_at = getattr(result, "_cached_at", None) if stale else None
                partial = getattr(result, "_partial", False) if stale else False
                data = result.data if isinstance(result, _StaleCacheResult) else result
                return FetchResult(
                    data=data,
                    source=source_id,
                    chain=self.name,
                    stale=stale,
                    cached_at=cached_at,
                    partial=partial,
                )
            except DataSourceError as e:
                attempts.append({"source": source_id, "error": str(e.reason)})
                registry.mark_fail(source_id, str(e.reason))
                log.warning("source %s failed: %s", source_id, e.reason)
                continue
        raise AllSourcesFailed(self.name, attempts)


@dataclass
class _StaleCacheResult:
    """stale_cache provider 返回值，携带 cached_at / partial 元数据。"""

    data: Any
    _cached_at: str | None = None
    _partial: bool = False
