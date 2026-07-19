"""统一后台任务调度 —— portfolio 刷新、每日摘要等。

单线程轮询：interval job 按间隔触发；cron job 按 HH:MM（上海时区）每日一次。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

_log = logging.getLogger("vibe.scheduler")

DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_DIGEST_TIME = "18:00"
_CHECK_INTERVAL_SEC = 60


@dataclass
class JobSpec:
    name: str
    interval_sec: int | None = None
    cron_time: str | None = None
    fn: Callable[[], None] | None = None
    enabled: bool = True
    last_run: datetime | None = None
    last_status: str = "idle"
    last_error: str | None = None
    _last_cron_date: str | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)


class Scheduler:
    def __init__(self, timezone: str = DEFAULT_TIMEZONE) -> None:
        self.timezone = timezone
        self._tz = ZoneInfo(timezone)
        self._jobs: dict[str, JobSpec] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def register(self, spec: JobSpec) -> None:
        enabled_names = _enabled_job_names()
        if enabled_names and spec.name not in enabled_names:
            spec.enabled = False
        with self._lock:
            self._jobs[spec.name] = spec

    def run_once(self, name: str) -> None:
        spec = self._get_job(name)
        if spec._running:
            raise RuntimeError(f"job {name} is already running")
        self._execute(spec)

    def get_status(self) -> list[dict]:
        now = datetime.now(self._tz)
        out: list[dict] = []
        with self._lock:
            for spec in self._jobs.values():
                out.append(
                    {
                        "name": spec.name,
                        "enabled": spec.enabled,
                        "interval_sec": spec.interval_sec,
                        "cron_time": spec.cron_time,
                        "last_run": spec.last_run.isoformat() if spec.last_run else None,
                        "last_status": spec.last_status,
                        "last_error": spec.last_error,
                        "next_run_estimate": _next_run_estimate(spec, now, self._tz),
                    }
                )
        return out

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="vibe-scheduler")
        self._thread.start()
        _log.info("scheduler started timezone=%s jobs=%s", self.timezone, list(self._jobs))

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            now = datetime.now(self._tz)
            with self._lock:
                specs = [s for s in self._jobs.values() if s.enabled and s.fn]
            for spec in specs:
                try:
                    if _should_run_interval(spec, now):
                        self._execute(spec)
                    elif _should_run_cron(spec, now):
                        self._execute(spec)
                except Exception as e:  # noqa: BLE001
                    _log.exception("scheduler loop error job=%s: %s", spec.name, e)
            time.sleep(_CHECK_INTERVAL_SEC)

    def _execute(self, spec: JobSpec) -> None:
        if not spec.fn:
            return
        started = time.perf_counter()
        spec._running = True
        spec.last_status = "running"
        spec.last_error = None
        try:
            spec.fn()
            spec.last_status = "success"
        except Exception as e:  # noqa: BLE001
            spec.last_status = "error"
            spec.last_error = str(e)
            _log.exception("job %s failed: %s", spec.name, e)
        finally:
            spec._running = False
            spec.last_run = datetime.now(self._tz)
            if spec.cron_time:
                spec._last_cron_date = spec.last_run.date().isoformat()
            duration_ms = int((time.perf_counter() - started) * 1000)
            _log.info(
                "job %s status=%s duration=%dms",
                spec.name,
                spec.last_status,
                duration_ms,
            )

    def _get_job(self, name: str) -> JobSpec:
        with self._lock:
            if name not in self._jobs:
                raise KeyError(name)
            return self._jobs[name]

    def get_job(self, name: str) -> JobSpec | None:
        with self._lock:
            return self._jobs.get(name)

    def is_job_running(self, name: str) -> bool:
        spec = self.get_job(name)
        return bool(spec and spec._running)


def _enabled_job_names() -> set[str]:
    raw = os.environ.get("VR_JOBS", "portfolio_refresh,daily_digest").strip()
    if not raw:
        return set()
    return {p.strip() for p in raw.split(",") if p.strip()}


def _should_run_interval(spec: JobSpec, now: datetime) -> bool:
    if not spec.interval_sec or spec._running:
        return False
    if spec.last_run is None:
        # 启动时不立即跑 interval job，避免阻塞 cron 检查（radar 预热耗时长）
        spec.last_run = now
        return False
    elapsed = (now - spec.last_run).total_seconds()
    return elapsed >= spec.interval_sec


def _should_run_cron(spec: JobSpec, now: datetime) -> bool:
    if not spec.cron_time or spec._running:
        return False
    today = now.date().isoformat()
    if spec._last_cron_date == today:
        return False
    try:
        parts = spec.cron_time.strip().split(":", 1)
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, TypeError, IndexError):
        return False
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # 到达计划时刻后、当日未跑过即触发（避免 60s 轮询错过精确分钟）
    return now >= scheduled


def _next_run_estimate(spec: JobSpec, now: datetime, tz: ZoneInfo) -> str | None:
    if not spec.enabled:
        return None
    if spec.interval_sec:
        base = spec.last_run or now
        nxt = base + timedelta(seconds=spec.interval_sec)
        return nxt.astimezone(tz).isoformat()
    if spec.cron_time:
        try:
            hour, minute = (int(p) for p in spec.cron_time.split(":", 1))
        except (ValueError, TypeError):
            return None
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.isoformat()
    return None
