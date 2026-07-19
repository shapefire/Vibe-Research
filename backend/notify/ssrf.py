"""Webhook SSRF 校验工具。"""

from __future__ import annotations

import os
from urllib.parse import urlparse

DEFAULT_ALLOW_HOSTS = ("qyapi.weixin.qq.com", "open.feishu.cn")


def allowed_hosts() -> set[str]:
    raw = os.environ.get("VR_NOTIFY_ALLOW_HOSTS", "").strip()
    if not raw:
        return set(DEFAULT_ALLOW_HOSTS)
    return {h.strip().lower() for h in raw.split(",") if h.strip()} | set(DEFAULT_ALLOW_HOSTS)


def validate_webhook_url(url: str, *, required_prefix: str | None = None) -> list[str]:
    errs: list[str] = []
    if not url:
        errs.append("缺少 webhook_url")
        return errs
    p = urlparse(url)
    if p.scheme != "https":
        errs.append("webhook_url 必须为 HTTPS")
    host = (p.hostname or "").lower()
    if host not in allowed_hosts():
        errs.append(f"webhook host 不在白名单：{host or '?'}")
    if required_prefix and not url.startswith(required_prefix):
        errs.append(f"webhook_url 必须是 {required_prefix} 开头")
    return errs
