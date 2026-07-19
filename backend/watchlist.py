"""自选股数据层 —— 读 VR_DATA_DIR/watchlist.json（08 规格子集，供 digest/CLI 使用）。"""

from __future__ import annotations

import json
import os
import threading

CACHE_DIR = os.environ.get("VR_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".vibe-research")
WATCHLIST_FILE = os.path.join(CACHE_DIR, "watchlist.json")
_LOCK = threading.Lock()


def _empty() -> dict:
    return {"version": 1, "items": []}


def load_all() -> list[dict]:
    """返回 items 列表；文件不存在抛 FileNotFoundError。"""
    with _LOCK:
        with open(WATCHLIST_FILE, encoding="utf-8") as f:
            data = json.load(f)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("symbol") or raw.get("code") or "").strip()
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "code": symbol,
                "market": raw.get("market", "a-share"),
                "name": raw.get("name", ""),
                "note": raw.get("note", ""),
            }
        )
    return out


def is_configured() -> bool:
    return os.path.isfile(WATCHLIST_FILE)
