"""渠道无关推送文案渲染。"""

from __future__ import annotations

from compliance import DIGEST_FOOTER, PUSH_FOOTER
from notify.base import NotifyMessage

# 推送 footer 与合规常量对齐
FOOTER = PUSH_FOOTER.replace("*", "").strip() or "纯数据摘要，不构成投资建议。"
MAX_BODY = 500


def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_num(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def render_digest_brief(digest, dashboard_url: str | None = None) -> NotifyMessage:
    """纯数据摘要 brief。"""
    m = getattr(digest, "market", None) or {}
    if isinstance(digest, dict):
        m = digest.get("market") or {}
        date = digest.get("date", "")
        wl = digest.get("watchlist_summary") or {}
        intel = digest.get("intel_summary") or {}
    else:
        date = digest.date
        wl = digest.watchlist_summary or {}
        intel = digest.intel_summary or {}

    sh = m.get("sh_index") or {}
    sz = m.get("sz_index") or {}
    sent = m.get("sentiment") or {}
    global_map = m.get("global") or {}

    lines = [
        f"Vibe-Research 数据摘要 {date}",
        "",
        f"上证 {_fmt_num(sh.get('close'))} ({_fmt_pct(sh.get('change_pct'))}) · "
        f"深证 {_fmt_num(sz.get('close'))} ({_fmt_pct(sz.get('change_pct'))})",
        f"上涨 {sent.get('up_count', 'N/A')} / 下跌 {sent.get('down_count', 'N/A')} · "
        f"涨停 {sent.get('limit_up', 'N/A')} / 跌停 {sent.get('limit_down', 'N/A')}",
    ]
    if global_map:
        g_parts = []
        for key, label in (("dji", "道指"), ("spx", "标普"), ("ndx", "纳指"), ("hsi", "恒生")):
            g = global_map.get(key) or {}
            if g:
                g_parts.append(f"{label} {_fmt_pct(g.get('change_pct'))}")
        if g_parts:
            lines.append("全球：" + " · ".join(g_parts))

    if wl.get("unconfigured"):
        lines.append("自选股：未配置")
    else:
        lines.append(f"自选股：{wl.get('total', 0)} 只（涨 {wl.get('up', 0)} / 跌 {wl.get('down', 0)}）")

    lines.append(f"资讯：今日新增 {intel.get('new_items', 0)} 条")

    body = "\n".join(lines)
    if len(body) > MAX_BODY:
        body = body[: MAX_BODY - 3] + "..."

    link = (dashboard_url or "").strip() or None
    return NotifyMessage(
        title=f"Vibe-Research 数据摘要 {date}",
        body_markdown=body,
        link=link,
        footer=FOOTER,
    )


def render_review_brief(
    digest,
    review_content: str,
    dashboard_url: str | None = None,
) -> NotifyMessage:
    """优先推送 AI 复盘节选 + 数据一行提示。"""
    if isinstance(digest, dict):
        date = digest.get("date", "")
    else:
        date = digest.date

    preview = (review_content or "").strip().replace("\r\n", "\n")
    # 去掉过长 markdown 标题噪音，取前几行
    plain_lines = [ln.strip() for ln in preview.split("\n") if ln.strip()]
    snippet = " ".join(plain_lines)[:280]
    if len(" ".join(plain_lines)) > 280:
        snippet += "..."

    digest_msg = render_digest_brief(digest, dashboard_url=None)
    lines = [
        f"Vibe-Research 定时复盘 {date}",
        "",
        snippet,
        "",
        "——",
        digest_msg.body_markdown.split("\n")[2] if len(digest_msg.body_markdown.split("\n")) > 2 else "",
    ]
    body = "\n".join(ln for ln in lines if ln is not None)
    if len(body) > MAX_BODY:
        body = body[: MAX_BODY - 3] + "..."

    link = (dashboard_url or "").strip() or None
    return NotifyMessage(
        title=f"Vibe-Research 定时复盘 {date}",
        body_markdown=body,
        link=link,
        footer=FOOTER,
    )


def render_test_message(dashboard_url: str | None = None) -> NotifyMessage:
    link = (dashboard_url or "").strip() or None
    return NotifyMessage(
        title="Vibe-Research 测试推送",
        body_markdown="这是一条测试消息，验证 Webhook 配置正确。",
        link=link,
        footer=FOOTER,
    )


# DIGEST_FOOTER 引用防 unused / 与 compliance 联调
_ = DIGEST_FOOTER
