"""注册内置 Providers。"""

from __future__ import annotations

from notify.providers.feishu import FeishuProvider
from notify.providers.wecom import WecomProvider
from notify.registry import ProviderRegistry


def register_builtin_providers() -> None:
    if ProviderRegistry.get("wecom") is None:
        ProviderRegistry.register(WecomProvider())
    if ProviderRegistry.get("feishu") is None:
        ProviderRegistry.register(FeishuProvider())


register_builtin_providers()
