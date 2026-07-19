"""自选股数据层 —— ~/.vibe-research/watchlist.json。

供前端 API、digest CLI、GHA 共用。多市场 normalize；原子写 + 锁。
合规：只存用户主动添加的标的，不预置、不推荐。
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime, timedelta, timezone

CACHE_DIR = os.environ.get("VR_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".vibe-research")
WL_FILE = os.path.join(CACHE_DIR, "watchlist.json")
WATCHLIST_FILE = WL_FILE  # digest / 旧 stub 兼容别名
_LOCK = threading.Lock()

BEIJING = timezone(timedelta(hours=8))
CURRENT_VERSION = 1
DEFAULT_MAX = 200


class WatchlistError(ValueError):
    """校验/业务错误（对应 HTTP 400）。"""


class CapacityExceeded(WatchlistError):
    """条数达上限（对应 HTTP 400）。"""


class WatchlistConflict(WatchlistError):
    """symbol 冲突（对应 HTTP 409）。"""


def _max_items() -> int:
    try:
        return max(1, int(os.environ.get("VR_WATCHLIST_MAX", str(DEFAULT_MAX))))
    except ValueError:
        return DEFAULT_MAX


def _now_iso() -> str:
    return datetime.now(BEIJING).isoformat(timespec="seconds")


def _empty() -> dict:
    return {"version": CURRENT_VERSION, "items": [], "updated_at": _now_iso()}


def _quarantine_corrupt(reason: str) -> None:
    if not os.path.isfile(WL_FILE):
        return
    dest = WL_FILE + ".corrupt"
    if os.path.exists(dest):
        stamp = datetime.now(BEIJING).strftime("%Y%m%d%H%M%S")
        dest = f"{WL_FILE}.corrupt.{stamp}"
    try:
        os.replace(WL_FILE, dest)
        print(f"[vibe-research] watchlist.json 损坏已备份为 {dest}: {reason}", file=sys.stderr)
    except OSError as e:
        print(f"[vibe-research] watchlist.json 损坏且备份失败: {e}", file=sys.stderr)


def _load() -> dict:
    if not os.path.isfile(WL_FILE):
        return _empty()
    try:
        with open(WL_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise TypeError("root not object")
        items = data.get("items")
        if not isinstance(items, list):
            raise TypeError("items not list")
        data.setdefault("version", CURRENT_VERSION)
        data.setdefault("updated_at", _now_iso())
        return data
    except (json.JSONDecodeError, OSError, TypeError) as e:
        _quarantine_corrupt(str(e))
        return _empty()


def _save(d: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    d["version"] = CURRENT_VERSION
    d["updated_at"] = _now_iso()
    tmp = WL_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, WL_FILE)


def normalize_symbol(raw: str) -> tuple[str, str] | None:
    """Return (symbol, market) or None if unrecognized."""
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None

    if s.endswith(".KS"):
        body = s[:-3]
        if re.fullmatch(r"\d{1,6}", body):
            return f"{body}.KS", "kr"
        return None

    if s.endswith(".SH") or s.endswith(".SZ"):
        body = s[:-3]
        if re.fullmatch(r"\d{6}", body):
            return body, "a-share"
        return None

    if s.endswith(".HK"):
        body = s[:-3]
        if re.fullmatch(r"\d{1,5}", body):
            return body.zfill(5), "hk"
        return None

    if re.fullmatch(r"\d{6}", s):
        return s, "a-share"

    if re.fullmatch(r"\d{1,5}", s):
        return s.zfill(5), "hk"

    if re.fullmatch(r"[A-Z]{1,5}", s):
        return s, "us"

    return None


def parse_symbols(raw: str) -> list[dict]:
    """Parse pasted text; skip invalid tokens; dedupe by first occurrence."""
    if not raw or not str(raw).strip():
        return []
    tokens = re.split(r"[\s,，、;；]+", str(raw).strip())
    seen: set[str] = set()
    out: list[dict] = []
    for tok in tokens:
        if not tok:
            continue
        norm = normalize_symbol(tok)
        if not norm:
            continue
        symbol, market = norm
        if symbol in seen:
            continue
        seen.add(symbol)
        out.append({"symbol": symbol, "market": market})
    return out


def _item_public(item: dict) -> dict:
    return {
        "symbol": item["symbol"],
        "market": item.get("market", "a-share"),
        "added_at": item.get("added_at") or _now_iso(),
        "note": item.get("note") or "",
    }


def _digest_row(item: dict) -> dict:
    symbol = item["symbol"]
    return {
        "symbol": symbol,
        "code": symbol,
        "market": item.get("market", "a-share"),
        "name": item.get("name") or "",
        "note": item.get("note") or "",
    }


def is_configured() -> bool:
    return os.path.isfile(WL_FILE)


def load_all() -> list[dict]:
    """Digest-compatible items list; FileNotFoundError if file missing."""
    if not os.path.isfile(WL_FILE):
        raise FileNotFoundError(WL_FILE)
    with _LOCK:
        data = _load()
    return [_digest_row(i) for i in data.get("items", []) if isinstance(i, dict) and i.get("symbol")]


def list_items() -> list[dict]:
    with _LOCK:
        data = _load()
    return [_item_public(i) for i in data.get("items", []) if isinstance(i, dict) and i.get("symbol")]


def get_state() -> dict:
    with _LOCK:
        data = _load()
    items = [_item_public(i) for i in data.get("items", []) if isinstance(i, dict) and i.get("symbol")]
    return {"items": items, "total": len(items), "updated_at": data.get("updated_at")}


def _append_parsed(parsed: list[dict]) -> tuple[list[dict], int]:
    if not parsed:
        raise WatchlistError("未识别到有效代码")
    with _LOCK:
        data = _load()
        items: list[dict] = [
            i for i in (data.get("items") or []) if isinstance(i, dict) and i.get("symbol")
        ]
        by_sym = {i["symbol"]: i for i in items}
        added = 0
        for p in parsed:
            symbol = p["symbol"]
            market = p["market"]
            if symbol in by_sym:
                old_m = by_sym[symbol].get("market", "a-share")
                if old_m != market:
                    raise WatchlistConflict(
                        f"symbol {symbol} 已存在（market={old_m}），不能以 market={market} 追加"
                    )
                continue
            if len(items) + 1 > _max_items():
                raise CapacityExceeded(f"自选股已达上限 {_max_items()} 条")
            row = {
                "symbol": symbol,
                "market": market,
                "added_at": _now_iso(),
                "note": p.get("note") or "",
            }
            items.append(row)
            by_sym[symbol] = row
            added += 1
        data["items"] = items
        _save(data)
        return [_item_public(i) for i in items], added


def add_symbols(symbols: list[str]) -> tuple[list[dict], int]:
    """Append; skip invalid; same-market existing is idempotent."""
    parsed: list[dict] = []
    seen: set[str] = set()
    for raw in symbols or []:
        norm = normalize_symbol(raw)
        if not norm:
            continue
        symbol, market = norm
        if symbol in seen:
            continue
        seen.add(symbol)
        parsed.append({"symbol": symbol, "market": market})
    return _append_parsed(parsed)


def add_raw(raw: str) -> tuple[list[dict], int]:
    return _append_parsed(parse_symbols(raw))


def replace_all(items_in: list[dict]) -> list[dict]:
    """Full replace. Reject invalid items; allow empty; duplicate symbol -> conflict."""
    if items_in is None:
        raise WatchlistError("items 必填")
    if len(items_in) > _max_items():
        raise CapacityExceeded(f"items 超过上限 {_max_items()} 条")

    pending: list[dict] = []
    seen: set[str] = set()
    for idx, raw in enumerate(items_in):
        if not isinstance(raw, dict):
            raise WatchlistError(f"items[{idx}] 必须是对象")
        symbol_raw = raw.get("symbol")
        if symbol_raw is None or str(symbol_raw).strip() == "":
            raise WatchlistError(f"items[{idx}].symbol 无效")
        norm = normalize_symbol(str(symbol_raw))
        if not norm:
            raise WatchlistError(f"items[{idx}].symbol 无法识别: {symbol_raw}")
        symbol, market = norm
        hint = raw.get("market")
        if hint and str(hint) != market:
            raise WatchlistError(
                f"items[{idx}] market 与 symbol 不匹配: {symbol} → {market}, 给定 {hint}"
            )
        if symbol in seen:
            raise WatchlistConflict(f"items 中重复 symbol: {symbol}")
        seen.add(symbol)
        note = raw.get("note") or ""
        if not isinstance(note, str):
            note = str(note)
        pending.append(
            {
                "symbol": symbol,
                "market": market,
                "added_at": raw.get("added_at"),
                "note": note,
            }
        )

    with _LOCK:
        data = _load()
        old_by = {
            i["symbol"]: i
            for i in (data.get("items") or [])
            if isinstance(i, dict) and i.get("symbol")
        }
        normalized: list[dict] = []
        for row in pending:
            added_at = row.get("added_at")
            if not added_at:
                old = old_by.get(row["symbol"])
                added_at = (old or {}).get("added_at") or _now_iso()
            normalized.append(
                {
                    "symbol": row["symbol"],
                    "market": row["market"],
                    "added_at": added_at,
                    "note": row["note"],
                }
            )
        data["items"] = normalized
        _save(data)
        return [_item_public(i) for i in normalized]


def remove(symbol: str) -> tuple[list[dict], bool]:
    """Delete; missing symbol is idempotent. Returns (items, removed)."""
    norm = normalize_symbol(symbol) if symbol else None
    key = norm[0] if norm else str(symbol or "").strip().upper()
    with _LOCK:
        data = _load()
        items: list[dict] = [
            i for i in (data.get("items") or []) if isinstance(i, dict) and i.get("symbol")
        ]
        before = len(items)
        items = [i for i in items if i["symbol"] != key]
        removed = len(items) < before
        data["items"] = items
        _save(data)
        return [_item_public(i) for i in items], removed


def migrate(codes: list[str]) -> tuple[list[dict], int]:
    """Migrate legacy localStorage codes; merge with existing."""
    if not codes:
        raise WatchlistError("codes 为空")
    parsed: list[dict] = []
    seen: set[str] = set()
    for c in codes:
        norm = normalize_symbol(str(c))
        if not norm:
            continue
        symbol, market = norm
        if symbol in seen:
            continue
        seen.add(symbol)
        parsed.append({"symbol": symbol, "market": market})
    if not parsed:
        raise WatchlistError("未识别到有效代码")
    return _append_parsed(parsed)
