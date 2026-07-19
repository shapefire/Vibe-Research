"""notify registry / mock provider 测试。"""

from __future__ import annotations

from notify.base import NotifyMessage, NotifyResult
from notify.registry import ProviderRegistry


class MockProvider:
    provider_id = "mock"
    display_name = "Mock"

    def validate_config(self, config: dict) -> list[str]:
        return []

    def send(self, message: NotifyMessage, config: dict) -> NotifyResult:
        return NotifyResult(self.provider_id, ok=True, latency_ms=1)


def test_register_and_list():
    ProviderRegistry.clear()
    ProviderRegistry.register(MockProvider())
    ids = {p["id"] for p in ProviderRegistry.list_providers()}
    assert "mock" in ids
    # 恢复内置
    import notify.providers as _p

    _p.register_builtin_providers()
