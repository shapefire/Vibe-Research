"""企业微信群机器人 Provider。"""

from __future__ import annotations

import logging
import time

import requests

from notify.base import NotifyMessage, NotifyResult
from notify.ssrf import validate_webhook_url

_log = logging.getLogger("vibe.notify.wecom")


class WecomProvider:
    provider_id = "wecom"
    display_name = "企业微信"

    def validate_config(self, config: dict) -> list[str]:
        return validate_webhook_url(
            str(config.get("webhook_url") or ""),
            required_prefix="https://qyapi.weixin.qq.com/",
        )

    def send(self, message: NotifyMessage, config: dict) -> NotifyResult:
        errs = self.validate_config(config)
        if errs:
            return NotifyResult(self.provider_id, ok=False, error="; ".join(errs))

        content = f"## {message.title}\n\n{message.body_markdown}\n\n{message.footer}"
        if message.link:
            content += f"\n\n[打开看板]({message.link})"
        # wecom markdown 限制
        if len(content.encode("utf-8")) > 4096:
            content = content.encode("utf-8")[:4090].decode("utf-8", errors="ignore") + "…"

        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        started = time.perf_counter()
        try:
            r = requests.post(config["webhook_url"], json=payload, timeout=10)
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code != 200:
                return NotifyResult(
                    self.provider_id,
                    ok=False,
                    error=f"HTTP {r.status_code}: {r.text[:200]}",
                    latency_ms=latency,
                )
            data = {}
            try:
                data = r.json()
            except Exception:  # noqa: BLE001
                pass
            if isinstance(data, dict) and data.get("errcode", 0) not in (0, None):
                return NotifyResult(
                    self.provider_id,
                    ok=False,
                    error=f"errcode={data.get('errcode')} {data.get('errmsg', '')}",
                    latency_ms=latency,
                )
            return NotifyResult(self.provider_id, ok=True, latency_ms=latency)
        except Exception as e:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            _log.warning("wecom send failed: %s", e)
            return NotifyResult(self.provider_id, ok=False, error=str(e), latency_ms=latency)
