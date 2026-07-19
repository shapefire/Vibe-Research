"""notify providers（mock httpx/requests）。"""

from __future__ import annotations

from notify.base import NotifyMessage
from notify.providers.wecom import WecomProvider
from notify.providers.feishu import FeishuProvider
from notify.render import FOOTER


def _msg() -> NotifyMessage:
    return NotifyMessage(
        title="t",
        body_markdown="hello world",
        link="https://example.com",
        footer=FOOTER,
    )


def test_wecom_rejects_bad_host():
    p = WecomProvider()
    errs = p.validate_config({"webhook_url": "https://evil.com/hook"})
    assert errs


def test_wecom_send_ok(monkeypatch):
    p = WecomProvider()
    cfg = {"webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=x"}

    class Resp:
        status_code = 200
        text = "{}"

        def json(self):
            return {"errcode": 0}

    monkeypatch.setattr("notify.providers.wecom.requests.post", lambda *a, **k: Resp())
    r = p.send(_msg(), cfg)
    assert r.ok


def test_feishu_send_ok(monkeypatch):
    p = FeishuProvider()
    cfg = {"webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/x"}

    class Resp:
        status_code = 200
        text = "{}"

        def json(self):
            return {"code": 0}

    monkeypatch.setattr("notify.providers.feishu.requests.post", lambda *a, **k: Resp())
    r = p.send(_msg(), cfg)
    assert r.ok
