"""NotifyService：编排渲染、合规、并行发送、幂等与状态。"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from compliance import assert_compliant
from notify import config as cfg_mod
from notify.base import NotifyMessage, NotifyResult
from notify.registry import ProviderRegistry
from notify.render import render_digest_brief, render_review_brief, render_test_message

# 确保 providers 已注册
import notify.providers  # noqa: F401

_log = logging.getLogger("vibe.notify")
BEIJING = timezone(timedelta(hours=8))


class NotifyService:
    def __init__(self, config_loader=None) -> None:
        self._loader = config_loader or cfg_mod.load_config

    def send_digest(self, digest, *, review_content: str | None = None) -> list[NotifyResult]:
        cfg = self._loader()
        if not cfg.get("enabled"):
            return []

        dashboard = cfg.get("dashboard_url") or ""
        if review_content and review_content.strip():
            msg = render_review_brief(digest, review_content, dashboard)
        else:
            msg = render_digest_brief(digest, dashboard)

        assert_compliant(f"{msg.body_markdown}\n{msg.footer}", context="notify")

        date = digest.date if hasattr(digest, "date") else digest.get("date")
        return self._dispatch(msg, cfg, idempotency_date=date)

    def send_test(self, provider_id: str | None = None) -> list[NotifyResult]:
        cfg = self._loader()
        msg = render_test_message(cfg.get("dashboard_url"))
        assert_compliant(f"{msg.body_markdown}\n{msg.footer}", context="notify_test")
        return self._dispatch(msg, cfg, provider_filter=provider_id, idempotency_date=None, force=True)

    def _dispatch(
        self,
        msg: NotifyMessage,
        cfg: dict,
        *,
        provider_filter: str | None = None,
        idempotency_date: str | None = None,
        force: bool = False,
    ) -> list[NotifyResult]:
        if not cfg.get("enabled") and not force:
            return []

        targets: list[tuple[object, dict]] = []
        results: list[NotifyResult] = []

        for ch in cfg.get("channels") or []:
            pid = ch.get("provider")
            if not pid:
                continue
            if provider_filter and pid != provider_filter:
                continue
            if not ch.get("enabled") and not (force and provider_filter == pid):
                # 强制测试指定渠道时允许即使 channel disabled? API 设计：测试 enabled 且 configured
                if not (force and provider_filter):
                    continue
            if force and provider_filter and not ch.get("enabled"):
                # 仍允许测试指定渠道
                pass
            elif not ch.get("enabled"):
                continue

            prov = ProviderRegistry.get(pid)
            if not prov:
                results.append(NotifyResult(pid, ok=False, error="未知 provider"))
                continue

            if idempotency_date and cfg_mod.already_sent(idempotency_date, pid):
                results.append(NotifyResult(pid, ok=True, skipped=True))
                continue

            targets.append((prov, ch))

        if not targets:
            return results

        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = {pool.submit(prov.send, msg, ch): (prov, ch) for prov, ch in targets}
            for fut in as_completed(futs):
                prov, ch = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:  # noqa: BLE001
                    res = NotifyResult(prov.provider_id, ok=False, error=str(e))
                results.append(res)
                self._after_send(res, idempotency_date)

        for r in results:
            _log.info(
                "notify sent provider=%s ok=%s skipped=%s latency=%s error=%s",
                r.provider_id,
                r.ok,
                r.skipped,
                r.latency_ms,
                r.error,
            )
        return results

    def _after_send(self, res: NotifyResult, idempotency_date: str | None) -> None:
        now = datetime.now(BEIJING).isoformat(timespec="seconds")
        if res.skipped:
            return
        if res.ok:
            cfg_mod.update_channel_status(res.provider_id, last_sent=now, last_error="")
            if idempotency_date:
                cfg_mod.mark_sent(idempotency_date, res.provider_id, now)
        else:
            cfg_mod.update_channel_status(res.provider_id, last_error=res.error or "error")


def send_digest(digest, *, review_content: str | None = None) -> list[NotifyResult]:
    return NotifyService().send_digest(digest, review_content=review_content)


def send_test(provider_id: str | None = None) -> list[NotifyResult]:
    return NotifyService().send_test(provider_id)


def status_payload() -> dict:
    from notify.registry import ProviderRegistry

    cfg = cfg_mod.load_config()
    channels = []
    for ch in cfg.get("channels") or []:
        pid = ch.get("provider")
        prov = ProviderRegistry.get(pid) if pid else None
        st = (cfg.get("status") or {}).get(pid) or {}
        webhook = ch.get("webhook_url") or ""
        channels.append(
            {
                "provider": pid,
                "display_name": prov.display_name if prov else pid,
                "enabled": bool(ch.get("enabled")),
                "configured": bool(webhook),
                "webhook_masked": cfg_mod.mask_webhook(webhook) if webhook else None,
                "last_sent": st.get("last_sent"),
                "last_error": st.get("last_error") or None,
            }
        )
    return {
        "enabled": bool(cfg.get("enabled")),
        "dashboard_url": cfg.get("dashboard_url") or "",
        "channels": channels,
    }
