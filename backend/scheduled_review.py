"""收盘定时 AI 复盘 —— 基于 digest 快照 + 可选实时情绪，调用户配置的 LLM/CLI。"""

from __future__ import annotations

import logging
import os
import sys

import astock
import market
from compliance import ComplianceViolation, assert_compliant
import digest
from digest import DailyDigest

_log = logging.getLogger("vibe.scheduled_review")

REVIEW_USER_PROMPT = (
    "请用中文做一段当天大盘复盘：整体涨跌、主要指数表现、短线情绪与盘面值得注意的点。"
    "只做客观陈述与多视角分析，不预测涨跌、不推荐任何标的、不构成投资建议。"
)


def llm_enabled() -> bool:
    return os.getenv("VR_DIGEST_INCLUDE_LLM", "false").strip().lower() in ("1", "true", "yes")


def llm_config_from_env() -> dict | None:
    """读取定时复盘 LLM 配置；未启用或未配置返回 None。"""
    if not llm_enabled():
        return None
    mode = os.getenv("VR_DIGEST_LLM_MODE", "").strip().lower()
    api_key = os.getenv("VR_DIGEST_LLM_API_KEY", "").strip()
    if mode == "cli" or (mode != "api" and not api_key):
        cli = os.getenv("VR_DIGEST_LLM_CLI", "claude").strip()
        return {"provider": f"cli-{cli}"}
    if not api_key:
        _log.warning("VR_DIGEST_INCLUDE_LLM=true 但未配置 VR_DIGEST_LLM_API_KEY，跳过 AI 复盘")
        return None
    return {
        "baseURL": os.getenv("VR_DIGEST_LLM_BASE_URL", "https://api.deepseek.com").strip(),
        "apiKey": api_key,
        "model": os.getenv("VR_DIGEST_LLM_MODEL", "deepseek-chat").strip(),
    }


def build_review_context(d: DailyDigest) -> str:
    """组装与 DailyReview 页相近的客观数据上下文（供 AI 复盘，不含结论）。"""
    parts = [digest.to_markdown(d)]

    try:
        indices = astock.index_quote()
        if indices:
            idx_line = "；".join(
                f"{i.get('name', '')} {i.get('price', '—')}（{i.get('change_pct', '—')}%）"
                for i in indices[:6]
            )
            parts.append(f"\n## 指数明细（实时）\n{idx_line}")
    except Exception as e:  # noqa: BLE001
        _log.debug("review context indices skip: %s", e)

    try:
        overview = market.get_overview()
        sent = overview.get("sentiment") or {}
        if sent:
            parts.append(
                "\n## 市场情绪\n"
                f"- 宽度：{sent.get('breadth', '—')} · 投机：{sent.get('speculation', '—')}\n"
                f"- 上涨 {sent.get('up', '—')} / 下跌 {sent.get('down', '—')}"
            )
        sectors = overview.get("sectors") or []
        if sectors:
            top = sectors[:3]
            bot = sectors[-2:] if len(sectors) >= 2 else []
            sec_lines = ["\n## 板块资金（行业）"]
            if top:
                sec_lines.append("流入靠前：" + " · ".join(f"{s.get('name')} {s.get('pct')}%" for s in top))
            if bot:
                sec_lines.append("靠后：" + " · ".join(f"{s.get('name')} {s.get('pct')}%" for s in bot))
            parts.append("\n".join(sec_lines))
    except Exception as e:  # noqa: BLE001
        _log.debug("review context overview skip: %s", e)

    try:
        emotion = market.get_short_term_emotion()
        if emotion:
            parts.append(
                "\n## 短线情绪\n"
                f"- 涨停 {emotion.get('zt_count', '—')} · 跌停 {emotion.get('dt_count', '—')} · "
                f"最高连板 {emotion.get('max_boards', '—')}\n"
                f"- 封板率 {emotion.get('seal_rate', '—')} · 炸板率 {emotion.get('break_rate', '—')}"
            )
    except Exception as e:  # noqa: BLE001
        _log.debug("review context emotion skip: %s", e)

    wl = d.watchlist_summary or {}
    if wl.get("total", 0) > 0 and wl.get("items"):
        lines = ["\n## 自选股明细"]
        for item in wl.get("items", [])[:15]:
            chg = item.get("change_pct")
            chg_s = f"{chg:+.2f}%" if isinstance(chg, (int, float)) else "N/A"
            lines.append(f"- {item.get('code')} {item.get('name')} {chg_s}")
        parts.append("\n".join(lines))

    return "\n".join(parts)


def generate_review(d: DailyDigest) -> str | None:
    """生成 AI 复盘正文；未配置 LLM 或失败返回 None（不阻断 digest）。"""
    cfg = llm_config_from_env()
    if not cfg:
        return None

    import chat as chat_layer

    context = build_review_context(d)
    user_msg = f"以下是今天 A 股大盘的客观数据：\n{context}\n\n{REVIEW_USER_PROMPT}"
    try:
        content = chat_layer.run_review_chat(cfg, user_msg, context=context)
        assert_compliant(content, context="scheduled_review")
        return content.strip()
    except ComplianceViolation as e:
        _log.error("scheduled review compliance failed: %s", e)
        print(f"[vibe-research] scheduled review rejected (compliance): {e}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        _log.exception("scheduled review failed: %s", e)
        print(f"[vibe-research] scheduled review failed: {e}", file=sys.stderr)
        return None


def run_for_digest(d: DailyDigest) -> str | None:
    """digest 落盘后尝试生成并写入复盘笔记。"""
    import notes as notes_mod

    content = generate_review(d)
    if not content:
        return None
    notes_mod.create_from_scheduled_review(d, content)
    print(f"[vibe-research] scheduled review saved: review-{d.date}", file=sys.stderr)
    return content
