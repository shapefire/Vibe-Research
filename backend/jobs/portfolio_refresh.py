"""持仓定时刷新 job。"""

from __future__ import annotations

import portfolio as pf
from scheduler import JobSpec


def run() -> None:
    pf._refresh_snapshot()  # noqa: SLF001


def spec() -> JobSpec:
    return JobSpec(name="portfolio_refresh", interval_sec=1800, fn=run)
