"""推送通知抽象：渠道无关消息模型 + Provider Protocol。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class NotifyMessage:
    title: str
    body_markdown: str
    link: str | None
    footer: str


@dataclass
class NotifyResult:
    provider_id: str
    ok: bool
    error: str | None = None
    latency_ms: int = 0
    skipped: bool = False


class NotifyProvider(Protocol):
    provider_id: str
    display_name: str

    def validate_config(self, config: dict) -> list[str]: ...

    def send(self, message: NotifyMessage, config: dict) -> NotifyResult: ...
