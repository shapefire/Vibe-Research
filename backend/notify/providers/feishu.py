"""飞书自定义机器人 Provider（优先 interactive 卡片，失败可回退 text）。"""

from __future__ import annotations

import logging
import time

import requests

from notify.base import NotifyMessage, NotifyResult
from notify.ssrf import validate_webhook_url

_log = logging.getLogger("vibe.notify.feishu")


class FeishuProvider:
    provider_id = "feishu"
    display_name = "飞书"

    def validate_config(self, config: dict) -> list[str]:
        return validate_webhook_url(
            str(config.get("webhook_url") or ""),
            required_prefix="https://open.feishu.cn/",
        )

    def send(self, message: NotifyMessage, config: dict) -> NotifyResult:
        errs = self.validate_config(config)
        if errs:
            return NotifyResult(self.provider_id, ok=False, error="; ".join(errs))

        card_payload = self._card_payload(message)
        started = time.perf_counter()
        try:
            r = requests.post(config["webhook_url"], json=card_payload, timeout=10)
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code == 200 and self._ok_body(r):
                return NotifyResult(self.provider_id, ok=True, latency_ms=latency)
            # 降级 text
            text_payload = {
                "msg_type": "text",
                "content": {
                    "text": f"{message.title}\n\n{message.body_markdown}\n\n{message.footer}"
                    + (f"\n{message.link}" if message.link else "")
                },
            }
            r2 = requests.post(config["webhook_url"], json=text_payload, timeout=10)
            latency = int((time.perf_counter() - started) * 1000)
            if r2.status_code == 200 and self._ok_body(r2):
                return NotifyResult(self.provider_id, ok=True, latency_ms=latency)
            return NotifyResult(
                self.provider_id,
                ok=False,
                error=f"HTTP {r2.status_code}: {r2.text[:200]}",
                latency_ms=latency,
            )
        except Exception as e:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            _log.warning("feishu send failed: %s", e)
            return NotifyResult(self.provider_id, ok=False, error=str(e), latency_ms=latency)

    def _card_payload(self, message: NotifyMessage) -> dict:
        elements: list[dict] = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{message.body_markdown}\n\n{message.footer}",
                },
            }
        ]
        if message.link:
            elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "打开看板"},
                            "url": message.link,
                            "type": "primary",
                        }
                    ],
                }
            )
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": message.title},
                    "template": "orange",
                },
                "elements": elements,
            },
        }

    @staticmethod
    def _ok_body(resp: requests.Response) -> bool:
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            return resp.status_code == 200
        if not isinstance(data, dict):
            return True
        # 飞书成功常见 StatusCode=0 或 code=0
        if data.get("StatusCode") not in (None, 0):
            return False
        if data.get("code") not in (None, 0):
            return False
        return True
