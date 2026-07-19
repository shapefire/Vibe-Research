"""notify 配置：默认 < env < notify.json。"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

_LOCK = threading.Lock()
CONFIG_VERSION = 1
DEFAULT_DASHBOARD = "http://127.0.0.1:5899/daily-review"


def _data_dir() -> Path:
    return Path(os.environ.get("VR_DATA_DIR") or Path.home() / ".vibe-research")


def config_path() -> Path:
    return _data_dir() / "notify.json"


def sent_dir() -> Path:
    return _data_dir() / "notify_sent"


def mask_webhook(url: str | None) -> str | None:
    if not url:
        return None
    if len(url) <= 28:
        return "***"
    # 保留 scheme+host 前缀，隐藏 key
    return url[:32] + "***"


def _default_config() -> dict:
    return {
        "version": CONFIG_VERSION,
        "enabled": False,
        "dashboard_url": DEFAULT_DASHBOARD,
        "channels": [
            {"provider": "wecom", "enabled": False, "webhook_url": ""},
            {"provider": "feishu", "enabled": False, "webhook_url": ""},
        ],
        "status": {},
    }


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _merge_env(cfg: dict) -> dict:
    out = deepcopy(cfg)
    if "VR_NOTIFY_ENABLED" in os.environ:
        out["enabled"] = _env_bool("VR_NOTIFY_ENABLED")
    if os.environ.get("VR_DASHBOARD_URL", "").strip():
        out["dashboard_url"] = os.environ["VR_DASHBOARD_URL"].strip()

    channel_map = {c["provider"]: c for c in out.get("channels", [])}

    def ensure(provider: str) -> dict:
        if provider not in channel_map:
            channel_map[provider] = {"provider": provider, "enabled": False, "webhook_url": ""}
        return channel_map[provider]

    if "VR_NOTIFY_WECOM_ENABLED" in os.environ:
        ensure("wecom")["enabled"] = _env_bool("VR_NOTIFY_WECOM_ENABLED")
    if os.environ.get("VR_NOTIFY_WECOM_WEBHOOK", "").strip():
        ensure("wecom")["webhook_url"] = os.environ["VR_NOTIFY_WECOM_WEBHOOK"].strip()
    if "VR_NOTIFY_FEISHU_ENABLED" in os.environ:
        ensure("feishu")["enabled"] = _env_bool("VR_NOTIFY_FEISHU_ENABLED")
    if os.environ.get("VR_NOTIFY_FEISHU_WEBHOOK", "").strip():
        ensure("feishu")["webhook_url"] = os.environ["VR_NOTIFY_FEISHU_WEBHOOK"].strip()

    out["channels"] = list(channel_map.values())
    return out


def load_config() -> dict:
    """优先级：notify.json 覆盖 env 覆盖默认。"""
    cfg = _default_config()
    cfg = _merge_env(cfg)
    path = config_path()
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg = _merge_file_over(cfg, data)
        except (OSError, json.JSONDecodeError):
            pass
    cfg.setdefault("status", {})
    cfg.setdefault("version", CONFIG_VERSION)
    return cfg


def _merge_file_over(base: dict, file_data: dict) -> dict:
    out = deepcopy(base)
    if "enabled" in file_data:
        out["enabled"] = bool(file_data["enabled"])
    if "dashboard_url" in file_data and file_data["dashboard_url"] is not None:
        out["dashboard_url"] = str(file_data["dashboard_url"])
    if "status" in file_data and isinstance(file_data["status"], dict):
        out["status"] = file_data["status"]
    if "channels" in file_data and isinstance(file_data["channels"], list):
        by_p = {c["provider"]: deepcopy(c) for c in out.get("channels", []) if "provider" in c}
        for ch in file_data["channels"]:
            if not isinstance(ch, dict) or "provider" not in ch:
                continue
            pid = ch["provider"]
            cur = by_p.get(pid, {"provider": pid, "enabled": False, "webhook_url": ""})
            if "enabled" in ch:
                cur["enabled"] = bool(ch["enabled"])
            if "webhook_url" in ch and ch["webhook_url"]:
                cur["webhook_url"] = str(ch["webhook_url"])
            by_p[pid] = cur
        out["channels"] = list(by_p.values())
    return out


def save_config(cfg: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CONFIG_VERSION,
        "enabled": bool(cfg.get("enabled")),
        "dashboard_url": str(cfg.get("dashboard_url") or ""),
        "channels": [],
        "status": cfg.get("status") or {},
    }
    for ch in cfg.get("channels") or []:
        if not isinstance(ch, dict):
            continue
        payload["channels"].append(
            {
                "provider": ch.get("provider"),
                "enabled": bool(ch.get("enabled")),
                "webhook_url": str(ch.get("webhook_url") or ""),
            }
        )
    tmp = path.with_suffix(".tmp")
    with _LOCK:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)


def merge_put_body(current: dict, body: dict) -> dict:
    """部分更新：webhook_url 省略则保留。"""
    out = deepcopy(current)
    if "enabled" in body:
        out["enabled"] = bool(body["enabled"])
    if "dashboard_url" in body:
        out["dashboard_url"] = str(body["dashboard_url"] or "")
    if "channels" in body and isinstance(body["channels"], list):
        by_p = {c["provider"]: deepcopy(c) for c in out.get("channels", [])}
        for ch in body["channels"]:
            if not isinstance(ch, dict) or "provider" not in ch:
                continue
            pid = ch["provider"]
            cur = by_p.get(pid, {"provider": pid, "enabled": False, "webhook_url": ""})
            if "enabled" in ch:
                cur["enabled"] = bool(ch["enabled"])
            if "webhook_url" in ch and ch["webhook_url"]:
                # 若前端传 masked 值则忽略
                url = str(ch["webhook_url"])
                if "***" not in url:
                    cur["webhook_url"] = url
            by_p[pid] = cur
        out["channels"] = list(by_p.values())
    return out


def validate_dashboard_url(url: str) -> list[str]:
    if not url:
        return []
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return ["dashboard_url 须为 http(s)://..."]
    return []


def update_channel_status(provider_id: str, *, last_sent: str | None = None, last_error: str | None = None) -> None:
    cfg = load_config()
    st = cfg.setdefault("status", {})
    cur = dict(st.get(provider_id) or {})
    if last_sent is not None:
        cur["last_sent"] = last_sent
    if last_error is not None:
        cur["last_error"] = last_error
    st[provider_id] = cur
    # 仅当 notify.json 存在或需持久化 status 时写入；始终写入以保证 status 可查
    save_config(cfg)


def already_sent(date: str, provider_id: str) -> bool:
    return (sent_dir() / f"{date}_{provider_id}.lock").is_file()


def mark_sent(date: str, provider_id: str, sent_at: str) -> None:
    d = sent_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{date}_{provider_id}.lock"
    payload = {"date": date, "provider_id": provider_id, "sent_at": sent_at, "digest_date": date}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
