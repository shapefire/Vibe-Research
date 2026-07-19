"""NotifyService 集成测试。"""

from __future__ import annotations

from digest import DailyDigest
from notify.base import NotifyMessage, NotifyResult
from notify.registry import ProviderRegistry
from notify.service import NotifyService
import notify.config as cfg_mod


class FakeProvider:
    provider_id = "fake"
    display_name = "Fake"
    calls = 0

    def validate_config(self, config: dict) -> list[str]:
        return []

    def send(self, message: NotifyMessage, config: dict) -> NotifyResult:
        FakeProvider.calls += 1
        return NotifyResult(self.provider_id, ok=True, latency_ms=2)


def _digest() -> DailyDigest:
    return DailyDigest(
        date="2026-07-12",
        market={"sh_index": {"close": 1, "change_pct": 0}, "sz_index": {}, "global": {}, "sentiment": {}},
        watchlist_summary={"total": 0, "up": 0, "down": 0, "unconfigured": True, "items": []},
        portfolio_summary=None,
        intel_summary={"new_items": 0, "tracks": []},
        generated_at="2026-07-12T18:00:00+08:00",
    )


def test_send_digest_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("VR_NOTIFY_ENABLED", raising=False)
    svc = NotifyService(config_loader=lambda: {"enabled": False, "channels": [], "dashboard_url": "", "status": {}})
    assert svc.send_digest(_digest()) == []


def test_send_digest_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    ProviderRegistry.clear()
    FakeProvider.calls = 0
    ProviderRegistry.register(FakeProvider())

    def loader():
        return {
            "enabled": True,
            "dashboard_url": "http://127.0.0.1:5899/daily-review",
            "channels": [{"provider": "fake", "enabled": True, "webhook_url": "https://qyapi.weixin.qq.com/x"}],
            "status": {},
        }

    # 避免 status 写入搅乱
    monkeypatch.setattr(cfg_mod, "update_channel_status", lambda *a, **k: None)
    monkeypatch.setattr(cfg_mod, "config_path", lambda: tmp_path / "notify.json")
    monkeypatch.setattr(cfg_mod, "sent_dir", lambda: tmp_path / "notify_sent")
    monkeypatch.setattr(cfg_mod, "save_config", lambda c: None)

    svc = NotifyService(config_loader=loader)
    r1 = svc.send_digest(_digest())
    assert any(x.ok and not x.skipped for x in r1)
    assert FakeProvider.calls == 1

    # 写入 lock（真实实现）
    (tmp_path / "notify_sent").mkdir(parents=True, exist_ok=True)
    (tmp_path / "notify_sent" / "2026-07-12_fake.lock").write_text("{}", encoding="utf-8")
    r2 = svc.send_digest(_digest())
    assert any(x.skipped for x in r2)
    assert FakeProvider.calls == 1

    import notify.providers as _p

    ProviderRegistry.clear()
    _p.register_builtin_providers()
