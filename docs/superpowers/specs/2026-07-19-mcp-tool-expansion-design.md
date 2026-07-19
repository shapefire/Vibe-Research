# Feat 10 · MCP / AI 工具面扩展 — Design Spec

> Date: 2026-07-19  
> Status: Approved (brainstorming)  
> Source: `docs/feats/99-backlog.md` §10  
> Supersedes: backlog draft tool list for feat 10

---

## 1. Goal

Expand Vibe-Research’s AI tool surface beyond the current 5 `chat.TOOLS` entries so that:

- **MCP** (Claude Code / external agents) can call market, funds, fundamentals, events, and personal (watchlist / notes / digest) data tools.
- **Web Chat** keeps a smaller, dialogue-friendly subset to control token cost.
- Tools are registered once via a **domain-split registry** (DSA-inspired), not duplicated between `chat.py` and `mcp_server.py`.

**Registry size:** 28 tools total (12 on Chat+MCP, 16 MCP-only).

**Non-goals (this feat):**

- Write tools (add/remove watchlist or notes)
- Buy/sell advice, scoring, or target prices in tool output
- Image OCR / Vision import
- HTTP self-calls to local FastAPI routes from handlers
- `get_note` (full note body) — YAGNI; `list_notes` returns meta only
- Electron, SQLite, or other Phase 3 backlog items

---

## 2. Architecture

### 2.1 Package layout

```
backend/tools/
  __init__.py          # export openai_tools, mcp_tools, execute
  registry.py          # ToolSpec, register, surface filter, dispatch + cap helpers
  quote.py             # quote / valuation / reports / news / global / kline
  market.py            # overview / radar / emotion / turnover / hot concepts / indices
  funds.py             # fund flow / margin / dragon-tiger / block trade
  fundamentals.py      # financials / finance / holders / dividend / industry
  events.py            # announcements / disclosure / lockup / investor QA
  personal.py          # list_watchlist / list_notes / get_latest_digest
```

### 2.2 ToolSpec

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict          # JSON Schema object
    handler: Callable[[dict], Any]
    surfaces: frozenset[str]  # subset of {"chat", "mcp"}
```

### 2.3 Public API

| Function | Behavior |
|----------|----------|
| `openai_tools(surface: str) -> list` | OpenAI function-calling format for that surface |
| `mcp_tools(surface: str) -> list` | MCP `{name, description, inputSchema}` list |
| `execute(name, args, *, surface: str \| None = None) -> Any` | Dispatch; if `surface` set, reject tools not on that surface |

### 2.4 Consumers

- **`chat.py`**: Keep SYSTEM_PROMPT + LLM loop. `TOOLS = openai_tools("chat")`. `_exec_tool` delegates to `tools.execute(..., surface="chat")`.
- **`mcp_server.py`**: `tools/list` / `tools/call` use `mcp_tools("mcp")` + `execute(..., surface="mcp")`. **Do not** import `chat.TOOLS`.

### 2.5 Data-plane rules

- Handlers call existing modules directly (`astock`, `gstock`, `market`, `newsradar`, `watchlist`, `notes`, `digest`) — never HTTP to self.
- Align with `docs/feats/00-implementation-constraints.md` (backend is not a package; same-dir imports).

---

## 3. Surface split

| Surface | Count (approx.) | Policy |
|---------|-----------------|--------|
| **chat** | 12 | Existing 5 + market overview/radar + kline + full funds pack |
| **mcp** | 28 | All registered tools |

### 3.1 Chat whitelist (`surfaces` includes `"chat"`)

1. `query_quote`
2. `query_valuation`
3. `query_reports`
4. `query_news`
5. `query_global_stock`
6. `query_kline`
7. `query_market_overview`
8. `query_radar`
9. `query_fund_flow`
10. `query_margin`
11. `query_dragon_tiger`
12. `query_block_trade`

### 3.2 MCP-only (plus all of §3.1)

**market:** `query_market_emotion`, `query_turnover_top`, `query_hot_concepts`, `query_global_indices`  
**fundamentals:** `query_financials`, `query_finance`, `query_holders`, `query_dividend`, `query_industry`  
**events:** `query_announcements`, `query_disclosure`, `query_lockup`, `query_investor_qa`  
**personal:** `list_watchlist`, `list_notes`, `get_latest_digest`

Cross-surface guard: `execute(..., surface="chat")` on an MCP-only name returns `{"error": "..."}` (blocks prompt-injection misuse of `list_notes` etc. from the web chat loop).

---

## 4. Tool catalog (handlers)

Handlers wrap existing functions. List/row responses apply field trimming and row limits consistent with current `chat._exec_tool` patterns.

| Tool | Primary backend | Notes |
|------|-----------------|-------|
| `query_quote` | `astock.tencent_quote` | `codes: string[]` |
| `query_valuation` | `astock.full_valuation` | |
| `query_reports` | `astock.eastmoney_reports` | trim fields; ≤15 rows |
| `query_news` | `astock.stock_news` | trim fields; ≤15 rows |
| `query_global_stock` | `gstock.us_hk_stock` | |
| `query_kline` | `astock.fetch_kline` | default `offset=60`, hard max 120; `category` as today |
| `query_market_overview` | `market.get_overview` | |
| `query_radar` | `newsradar.get_radar` | no force refresh by default |
| `query_market_emotion` | `market.get_short_term_emotion` | |
| `query_turnover_top` | `market.get_turnover_top` | |
| `query_hot_concepts` | same as `/api/hot-concepts` | |
| `query_global_indices` | `market.get_global_indices` | |
| `query_fund_flow` | `astock.stock_fund_flow_120d` | |
| `query_margin` | `astock.margin_trading` | |
| `query_dragon_tiger` | `astock.dragon_tiger_board` | |
| `query_block_trade` | `astock.block_trade` | |
| `query_financials` | `astock.financials` | |
| `query_finance` | same as `/api/finance` | |
| `query_holders` | `astock.holder_num_change` | |
| `query_dividend` | `astock.dividend_history` | |
| `query_industry` | same as `/api/industry` | |
| `query_announcements` | `astock.announcements` | |
| `query_disclosure` | same as `/api/disclosure` | |
| `query_lockup` | `astock.lockup_expiry` | |
| `query_investor_qa` | same as `/api/investor-qa` | |
| `list_watchlist` | `watchlist.list_items` | |
| `list_notes` | `notes.list_notes` | optional `kind`/`q`/`limit` (default ≤20, hard max 50); **meta only** (no full content) |
| `get_latest_digest` | `digest.load_latest` + `to_markdown` | `{date, markdown}` or `{"error": ...}` |

Exact `astock` / module function names for “same as `/api/...`” rows must match the current `app.py` route bodies at implementation time (no new data sources).

---

## 5. Data flow & errors

```
Chat / MCP
  → tools.execute(name, args, surface=...)
      → lookup ToolSpec (+ surface check)
      → handler(args)
      → success: JSON-serializable payload
      → failure: {"error": "..."}  (DependencyMissing and generic Exception caught)
  → Chat: existing `json.dumps(...)[:_TOOL_RESULT_CAP]` (6000) before model inject
  → MCP: text content + `isError` when result dict has `error` key
```

**SYSTEM_PROMPT:** Update the tool name list to describe the Chat surface (~12 tools). Keep compliance rules unchanged (no recommendations, no price targets, no timing advice).

---

## 6. Compliance

- Tool `description` strings must not contain buy/sell advice language (买入/卖出/推荐/目标价/必涨 etc.).
- Handlers return objective data only.
- Extend or mirror existing `test_compliance` patterns for new descriptions where applicable.
- Product disclaimer / UI compliance remains feat 14 territory; this feat only constrains tool copy and outputs.

---

## 7. Testing & acceptance

### 7.1 Tests

New: `backend/tests/test_tools_registry.py`

- Chat tool count == 12 and names match §3.1
- MCP tool set is full registry; includes personal tools
- `execute` with mocks for at least one handler per domain
- Cross-surface rejection for chat → MCP-only name
- Unknown tool → error dict
- `DependencyMissing` → error dict, no raise
- Description compliance smoke for registered tools

No mandatory live stdio MCP subprocess in CI.

### 7.2 Acceptance

1. Web chat completion payloads include exactly 12 tools.
2. MCP `tools/list` returns the full set (28).
3. Existing chat / notes / watchlist / digest tests still pass.
4. No write operations exposed as tools.
5. After implementation: add `docs/feats/10-mcp-tool-expansion.md`, remove §10 from `docs/feats/99-backlog.md`, update feats index if present.

---

## 8. Implementation order (high level)

1. Skeleton `backend/tools/` + `ToolSpec` / `execute` / surface filters + tests (red → green).
2. Migrate existing 5 tools into `quote.py`; wire `chat.py` + `mcp_server.py`.
3. Add Chat-surface new tools (kline, market overview/radar, funds pack).
4. Add MCP-only domains (remaining market, fundamentals, events, personal).
5. SYSTEM_PROMPT + compliance assertions.
6. Feat doc upgrade + backlog cleanup.

---

## 9. Decisions log

| Decision | Choice |
|----------|--------|
| Scope | Registry + backlog 5 + P1–P4 all packs (28 tools) |
| Chat vs MCP | Layered: Chat 12 / MCP full |
| Chat extras | overview, radar, kline, full funds pack (not list_notes) |
| Registry shape | Domain-split package `backend/tools/` (not single file, not in-place chat.py) |
| Cross-surface | `execute(..., surface=)` rejects off-surface tools |
| list_notes body | Meta only; no `get_note` this feat |

---

*Spec approved in brainstorming session 2026-07-19.*
