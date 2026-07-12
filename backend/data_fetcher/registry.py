"""数据源健康状态注册表（进程内单例）。"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

TZ8 = timezone(timedelta(hours=8))

KNOWN_SOURCES = ("tencent", "stale_cache", "eastmoney", "mootdx", "akshare")
CHAIN_SOURCES: dict[str, list[str]] = {
    "quote": ["tencent", "stale_cache"],
    "kline": ["mootdx"],
    "news": ["akshare"],
}


def _iso_now() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


@dataclass
class SourceState:
    status: str = "idle"
    last_ok: str | None = None
    last_fail: str | None = None
    last_error: str | None = None
    success_count: int = 0
    fail_count: int = 0


@dataclass
class SourceRegistry:
    _states: dict[str, SourceState] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _state(self, source_id: str) -> SourceState:
        if source_id not in self._states:
            self._states[source_id] = SourceState()
        return self._states[source_id]

    def mark_ok(self, source_id: str) -> None:
        with self._lock:
            s = self._state(source_id)
            s.status = "ok"
            s.last_ok = _iso_now()
            s.last_error = None
            s.success_count += 1

    def mark_fail(self, source_id: str, reason: str) -> None:
        with self._lock:
            s = self._state(source_id)
            s.status = "down"
            s.last_fail = _iso_now()
            s.last_error = reason[:200]
            s.fail_count += 1

    def mark_missing(self, source_id: str, reason: str) -> None:
        with self._lock:
            s = self._state(source_id)
            s.status = "missing"
            s.last_error = reason[:200]
            s.last_fail = _iso_now()

    def chain_status(self, chain: str) -> str:
        with self._lock:
            return self._chain_status_unlocked(chain)

    def _chain_status_unlocked(self, chain: str) -> str:
        sources = CHAIN_SOURCES.get(chain, [])
        if not sources:
            return "down"
        primary = self._state(sources[0])
        if primary.status == "ok":
            return "ok"
        for source_id in sources[1:]:
            if self._state(source_id).last_ok:
                return "degraded"
        if primary.status == "missing":
            return "down"
        if primary.last_ok:
            return "degraded"
        return "down"

    def to_dict(self) -> dict:
        with self._lock:
            sources = {}
            for sid in KNOWN_SOURCES:
                s = self._state(sid)
                sources[sid] = {
                    "status": s.status,
                    "last_ok": s.last_ok,
                    "last_fail": s.last_fail,
                    "last_error": s.last_error,
                }
            for sid, s in self._states.items():
                if sid not in sources:
                    sources[sid] = {
                        "status": s.status,
                        "last_ok": s.last_ok,
                        "last_fail": s.last_fail,
                        "last_error": s.last_error,
                    }
            chains = {name: self._chain_status_unlocked(name) for name in CHAIN_SOURCES}
            return {
                "sources": sources,
                "chains": chains,
                "updated_at": _iso_now(),
            }


registry = SourceRegistry()
