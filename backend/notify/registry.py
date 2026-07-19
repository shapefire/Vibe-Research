"""Provider 注册表 —— 新增渠道只需 register，不改 Service。"""

from __future__ import annotations

from notify.base import NotifyProvider


class ProviderRegistry:
    _providers: dict[str, NotifyProvider] = {}

    @classmethod
    def register(cls, provider: NotifyProvider) -> None:
        cls._providers[provider.provider_id] = provider

    @classmethod
    def get(cls, provider_id: str) -> NotifyProvider | None:
        return cls._providers.get(provider_id)

    @classmethod
    def list_providers(cls) -> list[dict]:
        return [
            {"id": p.provider_id, "name": p.display_name}
            for p in cls._providers.values()
        ]

    @classmethod
    def clear(cls) -> None:
        """测试用。"""
        cls._providers = {}
