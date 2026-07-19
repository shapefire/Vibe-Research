"""scheduler 单元测试。"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scheduler import JobSpec, Scheduler


def test_register_and_run_once():
    ran: list[int] = []
    sched = Scheduler()
    sched.register(JobSpec(name="test", fn=lambda: ran.append(1)))
    sched.run_once("test")
    assert ran == [1]
    status = sched.get_status()[0]
    assert status["last_status"] == "success"


def test_unknown_job_raises():
    sched = Scheduler()
    with pytest.raises(KeyError):
        sched.run_once("nope")


def test_cron_matches_time(monkeypatch):
    ran: list[int] = []
    sched = Scheduler(timezone="Asia/Shanghai")
    spec = JobSpec(name="cron_test", cron_time="18:00", fn=lambda: ran.append(1))
    sched.register(spec)

    tz = ZoneInfo("Asia/Shanghai")
    at_1805 = datetime(2026, 7, 12, 18, 5, 0, tzinfo=tz)
    import scheduler as sched_mod

    assert sched_mod._should_run_cron(spec, at_1805)
    sched._execute(spec)
    assert ran == [1]
    spec._last_cron_date = at_1805.date().isoformat()
    assert not sched_mod._should_run_cron(spec, at_1805)


def test_interval_not_immediate_on_first_tick():
    sched = Scheduler()
    spec = JobSpec(name="interval", interval_sec=1800, fn=lambda: None)
    sched.register(spec)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    import scheduler as sched_mod

    assert sched_mod._should_run_interval(spec, now) is False
    assert spec.last_run is not None


def test_interval_job_runs_after_elapsed():
    ran: list[int] = []
    sched = Scheduler()
    spec = JobSpec(name="interval", interval_sec=1, fn=lambda: ran.append(1))
    sched.register(spec)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    spec.last_run = now
    import scheduler as sched_mod
    from datetime import timedelta

    later = now + timedelta(seconds=2)
    assert sched_mod._should_run_interval(spec, later)


def test_job_error_recorded():
    sched = Scheduler()

    def boom():
        raise RuntimeError("fail")

    sched.register(JobSpec(name="bad", fn=boom))
    sched.run_once("bad")
    status = sched.get_status()[0]
    assert status["last_status"] == "error"
    assert "fail" in (status["last_error"] or "")
