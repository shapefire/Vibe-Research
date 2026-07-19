"""notify HTTP API。"""

from __future__ import annotations

from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app)


def test_notify_providers():
    from notify.registry import ProviderRegistry
    import notify.providers as _p

    ProviderRegistry.clear()
    _p.register_builtin_providers()
    r = client.get("/api/notify/providers")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["providers"]}
    assert "wecom" in ids and "feishu" in ids


def test_notify_status(tmp_path, monkeypatch):
    from notify.registry import ProviderRegistry
    import notify.providers as _p

    ProviderRegistry.clear()
    _p.register_builtin_providers()
    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("VR_NOTIFY_ENABLED", raising=False)
    r = client.get("/api/notify/status")
    assert r.status_code == 200
    body = r.json()
    assert "channels" in body
    assert body["enabled"] is False or isinstance(body["enabled"], bool)


def test_notify_config_put(tmp_path, monkeypatch):
    from notify.registry import ProviderRegistry
    import notify.providers as _p

    ProviderRegistry.clear()
    _p.register_builtin_providers()
    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "_API_KEY", "")
    r = client.put(
        "/api/notify/config",
        json={
            "enabled": True,
            "dashboard_url": "https://example.com/daily-review",
            "channels": [
                {
                    "provider": "wecom",
                    "enabled": True,
                    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc",
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    st = r.json()
    assert st["enabled"] is True
    wecom = next(c for c in st["channels"] if c["provider"] == "wecom")
    assert wecom["configured"] is True
    assert "***" in (wecom["webhook_masked"] or "")


def test_notify_test_disabled_returns_400_not_503(tmp_path, monkeypatch):
    """总开关关闭且未指定渠道时，应 400（避免前端把 503 当成数据源故障）。"""
    from notify.registry import ProviderRegistry
    import notify.providers as _p
    from notify import config as notify_cfg

    ProviderRegistry.clear()
    _p.register_builtin_providers()
    monkeypatch.setenv("VR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "_API_KEY", "")
    for k in list(__import__("os").environ):
        if k.startswith("VR_NOTIFY"):
            monkeypatch.delenv(k, raising=False)
    notify_cfg.save_config(
        {
            "enabled": False,
            "dashboard_url": "http://127.0.0.1:5899/daily-review",
            "channels": [],
            "status": {},
        }
    )
    r = client.post("/api/notify/test", json={})
    assert r.status_code == 400
    assert "总开关" in r.json()["detail"]
