from __future__ import annotations

# (surface, tool) -> (default, hard_max)
LIMITS: dict[tuple[str, str], tuple[int, int]] = {
    ("chat", "query_fund_flow"): (20, 60),
    ("mcp", "query_fund_flow"): (60, 120),
    ("chat", "query_kline"): (60, 120),
    ("mcp", "query_kline"): (60, 120),
    ("chat", "query_radar"): (5, 10),
    ("mcp", "query_radar"): (10, 30),
    ("chat", "query_margin"): (15, 30),
    ("mcp", "query_margin"): (30, 50),
    ("chat", "query_block_trade"): (15, 30),
    ("mcp", "query_block_trade"): (30, 50),
    ("chat", "query_reports"): (15, 20),
    ("mcp", "query_reports"): (15, 20),
    ("chat", "query_news"): (15, 20),
    ("mcp", "query_news"): (15, 20),
    ("mcp", "query_holders"): (15, 30),
    ("mcp", "query_dividend"): (30, 50),
    ("mcp", "query_announcements"): (15, 50),
    ("mcp", "query_disclosure"): (20, 50),
    ("mcp", "query_investor_qa"): (15, 50),
    ("mcp", "list_notes"): (20, 50),
    ("chat", "query_market_overview"): (30, 30),
    ("mcp", "query_market_overview"): (50, 50),
}

CHAT_TOOL_JSON_BUDGET = 8000
MAX_QUOTE_CODES = 20


def validate_a_code(code: object) -> str | None:
    s = str(code or "").strip()
    if not s.isdigit() or len(s) != 6:
        return None
    return s


def validate_codes(codes: object) -> list[str] | None:
    if not isinstance(codes, list) or not codes:
        return None
    out: list[str] = []
    seen: set[str] = set()
    for c in codes:
        v = validate_a_code(c)
        if v is None:
            return None
        if v not in seen:
            seen.add(v)
            out.append(v)
    if len(out) > MAX_QUOTE_CODES:
        return None
    return out


def clamp_limit(surface: str, tool: str, raw: object | None) -> int:
    default, hard = LIMITS.get((surface, tool), (15, 50))
    if raw is None:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return default
    return min(n, hard)
