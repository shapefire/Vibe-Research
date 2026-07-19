"""每日数据摘要 —— 聚合市场/自选股/持仓/资讯客观数据，不含 AI 结论。"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import astock
import market
import newsradar
import portfolio as pf
import watchlist

_log = logging.getLogger("vibe.digest")

CACHE_DIR = os.environ.get("VR_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".vibe-research")
DIGESTS_DIR = Path(CACHE_DIR) / "digests"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DISCLAIMER = "*纯数据摘要，不构成投资建议。详细分析请打开看板使用你的 AI。*"
_LOCK = threading.Lock()
_NA = {"close": None, "change_pct": None}


@dataclass
class DailyDigest:
    date: str
    market: dict
    watchlist_summary: dict
    portfolio_summary: dict | None
    intel_summary: dict
    generated_at: str
    errors: list[dict] = field(default_factory=list)
    version: int = 1

    def to_markdown(self) -> str:
        return to_markdown(self)


def _tz() -> ZoneInfo:
    name = os.environ.get("VR_DIGEST_TIMEZONE", DEFAULT_TIMEZONE)
    return ZoneInfo(name)


def today_shanghai() -> str:
    return datetime.now(_tz()).date().isoformat()


def generate(date: str | None = None) -> DailyDigest:
    """聚合各数据源；单段失败记 errors，整体仍生成。"""
    digest_date = date or today_shanghai()
    errors: list[dict] = []
    market_data = _fetch_market(errors)
    watchlist_data = _fetch_watchlist(errors)
    portfolio_data = _fetch_portfolio(errors)
    intel_data = _fetch_intel(errors, digest_date)
    generated_at = datetime.now(_tz()).isoformat(timespec="seconds")
    return DailyDigest(
        date=digest_date,
        market=market_data,
        watchlist_summary=watchlist_data,
        portfolio_summary=portfolio_data,
        intel_summary=intel_data,
        generated_at=generated_at,
        errors=errors,
    )


def _fetch_market(errors: list[dict]) -> dict:
    out: dict = {
        "sh_index": dict(_NA),
        "sz_index": dict(_NA),
        "global": {},
        "sentiment": {
            "up_count": None,
            "down_count": None,
            "limit_up": None,
            "limit_down": None,
        },
    }
    try:
        indices = astock.index_quote()
        for idx in indices:
            name = idx.get("name", "")
            entry = {
                "close": idx.get("price"),
                "change_pct": idx.get("change_pct"),
            }
            if "上证" in name:
                out["sh_index"] = entry
            elif "深证" in name or "成指" in name:
                out["sz_index"] = entry
    except Exception as e:  # noqa: BLE001
        errors.append({"section": "market.indices", "message": str(e)})
        _log.warning("market indices failed: %s", e)

    try:
        overview = market.get_overview()
        sent = overview.get("sentiment") or {}
        out["sentiment"] = {
            "up_count": sent.get("up"),
            "down_count": sent.get("down"),
            "limit_up": sent.get("zt_real", sent.get("zt")),
            "limit_down": sent.get("dt_real", sent.get("dt")),
        }
    except Exception as e:  # noqa: BLE001
        errors.append({"section": "market.sentiment", "message": str(e)})
        _log.warning("market sentiment failed: %s", e)

    try:
        global_list = market.get_global_indices()
        global_map: dict = {}
        for item in global_list:
            key = item.get("key")
            if not key:
                continue
            global_map[key] = {
                "close": item.get("price"),
                "change_pct": item.get("change_pct"),
            }
        out["global"] = global_map
    except Exception as e:  # noqa: BLE001
        errors.append({"section": "market.global", "message": str(e)})
        _log.warning("market global failed: %s", e)

    return out


def _fetch_watchlist(errors: list[dict]) -> dict:
    empty = {
        "total": 0,
        "up": 0,
        "down": 0,
        "flat": 0,
        "unconfigured": True,
        "items": [],
    }
    try:
        if not watchlist.is_configured():
            return empty
        items_raw = watchlist.load_all()
    except FileNotFoundError:
        return empty
    except Exception as e:  # noqa: BLE001
        errors.append({"section": "watchlist", "message": str(e)})
        return empty

    if not items_raw:
        return {**empty, "unconfigured": False}

    a_share_codes = [i["code"] for i in items_raw if i.get("market", "a-share") == "a-share" and i["code"].isdigit() and len(i["code"]) == 6]
    quotes: dict[str, dict] = {}
    if a_share_codes:
        try:
            quotes = astock.fetch_quote(a_share_codes).data
        except Exception as e:  # noqa: BLE001
            errors.append({"section": "watchlist.quotes", "message": str(e)})

    items: list[dict] = []
    up = down = flat = 0
    for row in items_raw:
        code = row["code"]
        q = quotes.get(code, {})
        change_pct = q.get("change_pct")
        name = q.get("name") or row.get("name") or code
        if change_pct is None:
            flat += 1
        elif change_pct > 0:
            up += 1
        elif change_pct < 0:
            down += 1
        else:
            flat += 1
        items.append(
            {
                "code": code,
                "name": name,
                "change_pct": change_pct,
                "pe": q.get("pe"),
            }
        )

    return {
        "total": len(items),
        "up": up,
        "down": down,
        "flat": flat,
        "unconfigured": False,
        "items": items,
    }


def _fetch_portfolio(errors: list[dict]) -> dict | None:
    try:
        data = pf.get_portfolio()
        holdings = data.get("holdings") or []
        if not holdings:
            return None
        totals = data.get("totals") or {}
        items = [{"code": h.get("code"), "pnl_pct": h.get("pnl_pct")} for h in holdings]
        return {
            "total_pnl_pct": totals.get("pnl_pct"),
            "items": items,
        }
    except Exception as e:  # noqa: BLE001
        errors.append({"section": "portfolio", "message": str(e)})
        return None


def _fetch_intel(errors: list[dict], digest_date: str) -> dict:
    try:
        stats = newsradar.get_cache_stats(digest_date)
        return stats
    except Exception as e:  # noqa: BLE001
        errors.append({"section": "intel", "message": str(e)})
        return {"new_items": 0, "tracks": []}


def save(digest: DailyDigest) -> Path:
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGESTS_DIR / f"{digest.date}.json"
    tmp = path.with_suffix(".tmp")
    payload = asdict(digest)
    with _LOCK:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    return path


def load(date: str) -> DailyDigest | None:
    path = DIGESTS_DIR / f"{date}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _from_dict(data)
    except (json.JSONDecodeError, OSError, TypeError, KeyError) as e:
        _log.warning("load digest %s failed: %s", date, e)
        return None


def load_latest() -> DailyDigest | None:
    if not DIGESTS_DIR.is_dir():
        return None
    files = sorted(p.stem for p in DIGESTS_DIR.glob("*.json") if p.is_file())
    if not files:
        return None
    return load(files[-1])


def to_markdown(digest: DailyDigest) -> str:
    lines = [f"# 每日数据摘要 {digest.date}", ""]
    m = digest.market
    sh = m.get("sh_index") or {}
    sz = m.get("sz_index") or {}
    lines.append("## 大盘")
    lines.append(
        f"- 上证 {_fmt_num(sh.get('close'))} ({_fmt_pct(sh.get('change_pct'))}) · "
        f"深证 {_fmt_num(sz.get('close'))} ({_fmt_pct(sz.get('change_pct'))})"
    )
    sent = m.get("sentiment") or {}
    lines.append(
        f"- 上涨 {_fmt_int(sent.get('up_count'))} / 下跌 {_fmt_int(sent.get('down_count'))} · "
        f"涨停 {_fmt_int(sent.get('limit_up'))} / 跌停 {_fmt_int(sent.get('limit_down'))}"
    )
    global_map = m.get("global") or {}
    if global_map:
        parts = []
        labels = {"dji": "道指", "spx": "标普", "ndx": "纳指", "hsi": "恒生"}
        for key, label in labels.items():
            g = global_map.get(key) or {}
            parts.append(f"{label} {_fmt_pct(g.get('change_pct'))}")
        if parts:
            lines.append(f"- 全球：{' · '.join(parts)}")
    lines.append("")

    wl = digest.watchlist_summary
    lines.append(f"## 自选股（{wl.get('total', 0)}）")
    if wl.get("unconfigured"):
        lines.append("未配置自选股。")
    elif wl.get("total", 0) == 0:
        lines.append("暂无自选股。")
    else:
        lines.append("| 代码 | 名称 | 涨跌 |")
        lines.append("| --- | --- | --- |")
        for item in wl.get("items") or []:
            lines.append(
                f"| {item.get('code', '')} | {item.get('name', '')} | {_fmt_pct(item.get('change_pct'))} |"
            )
    lines.append("")

    ps = digest.portfolio_summary
    if ps:
        lines.append("## 持仓")
        lines.append(f"总浮动盈亏 {_fmt_pct(ps.get('total_pnl_pct'))}")
        lines.append("| 代码 | 盈亏 |")
        lines.append("| --- | --- |")
        for item in ps.get("items") or []:
            lines.append(f"| {item.get('code', '')} | {_fmt_pct(item.get('pnl_pct'))} |")
        lines.append("")

    intel = digest.intel_summary or {}
    lines.append("## 资讯雷达")
    tracks = intel.get("tracks") or []
    track_txt = " · ".join(f"{t.get('name', '')} {t.get('count', 0)}" for t in tracks[:8])
    lines.append(f"今日新增 {_fmt_int(intel.get('new_items'))} 条" + (f" · {track_txt}" if track_txt else ""))
    lines.append("")
    lines.append("---")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _from_dict(data: dict) -> DailyDigest:
    return DailyDigest(
        date=str(data["date"]),
        market=data.get("market") or {},
        watchlist_summary=data.get("watchlist_summary") or {},
        portfolio_summary=data.get("portfolio_summary"),
        intel_summary=data.get("intel_summary") or {},
        generated_at=str(data.get("generated_at", "")),
        errors=list(data.get("errors") or []),
        version=int(data.get("version", 1)),
    )


def _fmt_num(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_int(v) -> str:
    if v is None:
        return "N/A"
    try:
        return str(int(v))
    except (TypeError, ValueError):
        return "N/A"
