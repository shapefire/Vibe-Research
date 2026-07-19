"""资讯雷达缓存预热 job —— 定时 force 刷新 radar 缓存（Phase 2 stub）。"""

from __future__ import annotations

import logging

import newsradar
from scheduler import JobSpec

_log = logging.getLogger("vibe.jobs.radar_cache_warm")

DEFAULT_INTERVAL_SEC = 3600


def run() -> None:
    """拉取全部 RSS 源并更新本地缓存；失败时抛出让 scheduler 记录 error。"""
    data = newsradar.fetch_radar()
    failed = (data.get("stats") or {}).get("failed_sources", 0)
    _log.info("radar cache warmed industries=%s failed_sources=%s", len(data.get("industries") or []), failed)


def spec() -> JobSpec:
    return JobSpec(name="radar_cache_warm", interval_sec=DEFAULT_INTERVAL_SEC, fn=run)
