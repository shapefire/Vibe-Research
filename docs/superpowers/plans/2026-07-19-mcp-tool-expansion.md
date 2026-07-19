# Feat 10 MCP Tool Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a domain-split `backend/tools/` registry with 29 read-only tools, Chat surface 12 / MCP surface 29, semantic pagination (scheme B), and remove Chat JSON string hard-truncation.

**Architecture:** `ToolSpec` registry in `backend/tools/`; domain modules `*_tools.py` register handlers at import; `chat.py` and `mcp_server.py` consume `openai_tools` / `mcp_tools` / `execute`; list tools return `data` + optional `meta` pagination envelope; Chat uses `fit_json_budget` instead of `[:6000]`.

**Tech Stack:** Python 3.12, pytest, existing `astock` / `gstock` / `market` / `newsradar` / `watchlist` / `notes` / `digest`, stdlib MCP JSON-RPC server.

**Spec:** `docs/superpowers/specs/2026-07-19-mcp-tool-expansion-design.md`

## Global Constraints

- Backend is not a package: run tests from `backend/` with `pytest tests/...`; imports are `import tools`, `import astock` (cwd/`sys.path` = `backend/`).
- Never HTTP self-call FastAPI from handlers.
- No write tools; no buy/sell language in descriptions.
- File names must be `*_tools.py` — never `tools/market.py`.
- Scheme B only: pagination meta + `fit_json_budget`; no `json.dumps(...)[:N]`; no summary/detail tool pairs (scheme C).
- Chat tools exactly 12 names in §3.1 of the spec; MCP 29 including `get_note`.
- Source meta key `_meta`; pagination key `meta`.

## File map

| Path | Responsibility |
|------|----------------|
| Create `backend/tools/__init__.py` | Export API; import all domain modules to register |
| Create `backend/tools/registry.py` | ToolSpec, register, openai/mcp lists, execute |
| Create `backend/tools/params.py` | Code validation, limit clamp by surface |
| Create `backend/tools/trim.py` | page_from_end, attach_page_meta, fit_json_budget, json_safe |
| Create `backend/tools/quote_tools.py` | 6 quote/kline tools |
| Create `backend/tools/market_tools.py` | overview/radar/emotion/turnover/hot/indices |
| Create `backend/tools/funds_tools.py` | fund_flow/margin/dragon_tiger/block_trade |
| Create `backend/tools/fundamentals_tools.py` | financials/finance/holders/dividend/industry |
| Create `backend/tools/events_tools.py` | announcements/disclosure/lockup/investor_qa |
| Create `backend/tools/personal_tools.py` | watchlist/notes/get_note/digest |
| Modify `backend/chat.py` | TOOLS from registry; _exec_tool→execute; drop hard cut; SYSTEM_PROMPT |
| Modify `backend/mcp_server.py` | Use tools package; version 0.2.0 |
| Create `backend/tests/test_tools_pagination.py` | Scheme B |
| Create `backend/tests/test_tools_registry.py` | Surfaces, cross-surface, unknown |
| Create `backend/tests/test_tools_handlers.py` | Per-tool mock contracts |
| Create `docs/feats/10-mcp-tool-expansion.md` | Feat doc |
| Modify `docs/feats/99-backlog.md` | Remove §10 |

---

### Task 1: params + trim + pagination unit tests

**Files:**
- Create: `backend/tools/params.py`
- Create: `backend/tools/trim.py`
- Create: `backend/tools/__init__.py` (minimal stub exporting nothing yet except allowing package import — or empty)
- Create: `backend/tests/test_tools_pagination.py`
- Test: `backend/tests/test_tools_pagination.py`

**Interfaces:**
- Produces: `validate_a_code`, `validate_codes`, `clamp_limit`, `LIMITS`, `page_from_end`, `attach_page_meta`, `fit_json_budget`, `json_safe`, `CHAT_TOOL_JSON_BUDGET`

- [ ] **Step 1: Write failing pagination tests**

Create `backend/tests/test_tools_pagination.py`:

```python
from __future__ import annotations

import json

from tools import trim
from tools.params import clamp_limit, validate_a_code, validate_codes


def test_validate_a_code_ok():
    assert validate_a_code("600519") == "600519"


def test_validate_a_code_bad():
    assert validate_a_code("1") is None
    assert validate_a_code("abcdef") is None


def test_validate_codes_max_20():
    codes = [f"{i:06d}" for i in range(21)]
    assert validate_codes(codes) is None  # signals error to caller


def test_page_from_end_no_overlap():
    rows = [{"i": i} for i in range(120)]
    p0, meta0 = trim.page_from_end(rows, limit=20, offset=0)
    assert [r["i"] for r in p0] == list(range(100, 120))
    assert meta0["truncated"] is True
    assert meta0["total"] == 120
    assert meta0["returned"] == 20
    assert meta0["offset"] == 0
    assert meta0["next_offset"] == 20

    p1, meta1 = trim.page_from_end(rows, limit=20, offset=20)
    assert [r["i"] for r in p1] == list(range(80, 100))
    assert meta1["next_offset"] == 40
    assert {r["i"] for r in p0} & {r["i"] for r in p1} == set()


def test_page_from_end_covers_all():
    rows = [{"i": i} for i in range(45)]
    seen = []
    offset = 0
    while True:
        page, meta = trim.page_from_end(rows, limit=20, offset=offset)
        seen.extend(r["i"] for r in page)
        if not meta.get("truncated"):
            break
        offset = meta["next_offset"]
    assert sorted(seen) == list(range(45))


def test_fit_json_budget_keeps_valid_json():
    payload = {
        "data": [{"x": "y" * 200} for _ in range(50)],
        "meta": {"truncated": False, "total": 50, "returned": 50, "offset": 0},
    }
    out = trim.fit_json_budget(payload, budget=3000)
    s = json.dumps(out, ensure_ascii=False)
    assert len(s) <= 3000
    json.loads(s)
    assert out["meta"]["truncated"] is True
    assert out["meta"]["returned"] == len(out["data"])


def test_clamp_limit_chat_fund_flow():
    assert clamp_limit("chat", "query_fund_flow", None) == 20
    assert clamp_limit("chat", "query_fund_flow", 999) == 60
    assert clamp_limit("mcp", "query_fund_flow", None) == 60
    assert clamp_limit("mcp", "query_fund_flow", 999) == 120
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && python -m pytest tests/test_tools_pagination.py -v`

Expected: FAIL (cannot import `tools.trim` / `tools.params`)

- [ ] **Step 3: Implement params.py and trim.py**

`backend/tools/__init__.py` (temporary minimal):

```python
"""AI / MCP tool registry package."""
```

`backend/tools/params.py`:

```python
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
```

`backend/tools/trim.py`:

```python
from __future__ import annotations

import json
import math
from typing import Any


def json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else str(obj)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(x) for x in obj]
    return str(obj)


def page_from_end(rows: list, *, limit: int, offset: int) -> tuple[list, dict]:
    """Paginate from the end (newest-last lists like fund flow). offset skips already-returned newest items."""
    total = len(rows)
    offset = max(0, int(offset))
    limit = max(1, int(limit))
    end = total - offset
    if end <= 0:
        meta = {
            "truncated": False,
            "total": total,
            "returned": 0,
            "offset": offset,
            "next_offset": offset,
            "hint": "没有更多数据",
        }
        return [], meta
    start = max(0, end - limit)
    page = rows[start:end]
    truncated = start > 0
    next_offset = offset + len(page) if truncated else offset
    meta = {
        "truncated": truncated,
        "total": total,
        "returned": len(page),
        "offset": offset,
        "next_offset": next_offset if truncated else offset,
        "hint": (
            f"还有 {start} 条；使用 offset={next_offset} 或增大 limit 继续取"
            if truncated
            else ""
        ),
    }
    if not truncated:
        meta.pop("hint", None)
    return page, meta


def attach_page_meta(data: Any, meta: dict) -> dict:
    return {"data": data, "meta": meta}


def fit_json_budget(payload: Any, budget: int) -> Any:
    """Shrink list payload['data'] from the front (older) until JSON fits; never slice the JSON string."""
    payload = json_safe(payload)
    def _len(p: Any) -> int:
        return len(json.dumps(p, ensure_ascii=False))

    if _len(payload) <= budget:
        return payload
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return {
            "data": None,
            "meta": {
                "truncated": True,
                "hint": "结果过大，请缩小 limit 或改用 MCP 面",
            },
        }
    data = list(payload["data"])
    meta = dict(payload.get("meta") or {})
    total = meta.get("total", len(data))
    while data and _len({"data": data, "meta": meta}) > budget:
        data = data[1:]  # drop older end of current page window
        meta["truncated"] = True
        meta["returned"] = len(data)
        meta["hint"] = "受 Chat token 预算裁剪；增大分页次数或改用 MCP"
    out = {"data": data, "meta": meta}
    if "total" not in meta:
        meta["total"] = total
    return out
```

Fix `test_validate_codes_max_20`: returning `None` means invalid — good.

Fix `page_from_end` last-page `truncated=False` when `start==0`.

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && python -m pytest tests/test_tools_pagination.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tools/__init__.py backend/tools/params.py backend/tools/trim.py backend/tests/test_tools_pagination.py
git commit -m "feat(tools): add params/trim pagination helpers (scheme B)"
```

---

### Task 2: Registry core + surface filtering

**Files:**
- Create: `backend/tools/registry.py`
- Modify: `backend/tools/__init__.py`
- Create: `backend/tests/test_tools_registry.py`
- Test: `backend/tests/test_tools_registry.py`

**Interfaces:**
- Produces: `ToolSpec`, `register`, `openai_tools`, `mcp_tools`, `execute`, `all_specs`
- Consumes: `trim.fit_json_budget`, `params.CHAT_TOOL_JSON_BUDGET`

- [ ] **Step 1: Write failing registry tests**

```python
from __future__ import annotations

from tools.registry import ToolSpec, execute, mcp_tools, openai_tools, register, _REGISTRY
from tools import trim


def setup_function():
    _REGISTRY.clear()


def test_surface_filter_and_execute():
    register(
        ToolSpec(
            name="t_chat",
            description="客观测试工具",
            parameters={"type": "object", "properties": {}},
            handler=lambda args: {"ok": True},
            surfaces=frozenset({"chat", "mcp"}),
        )
    )
    register(
        ToolSpec(
            name="t_mcp",
            description="客观 MCP 工具",
            parameters={"type": "object", "properties": {}},
            handler=lambda args: {"secret": 1},
            surfaces=frozenset({"mcp"}),
        )
    )
    assert [t["function"]["name"] for t in openai_tools("chat")] == ["t_chat"]
    assert {t["name"] for t in mcp_tools("mcp")} == {"t_chat", "t_mcp"}
    assert execute("t_chat", {}, surface="chat") == {"ok": True}
    assert "error" in execute("t_mcp", {}, surface="chat")
    assert execute("t_mcp", {}, surface="mcp") == {"secret": 1}
    assert "error" in execute("nope", {})


def test_execute_chat_applies_budget(monkeypatch):
    big = {"data": [{"x": "z" * 100} for _ in range(200)], "meta": {"truncated": False}}
    register(
        ToolSpec(
            name="t_big",
            description="客观大数据",
            parameters={"type": "object", "properties": {}},
            handler=lambda args: big,
            surfaces=frozenset({"chat", "mcp"}),
        )
    )
    out = execute("t_big", {}, surface="chat")
    import json
    assert len(json.dumps(out, ensure_ascii=False)) <= 8000
    assert out["meta"]["truncated"] is True
```

Note: these tests clear `_REGISTRY` — domain modules must re-import after. Prefer testing against real registered tools in later tasks; for Task 2 keep registry isolated by exporting `_REGISTRY` for tests only, then Task 3+ tests import `tools` package which re-registers.

Better approach for Task 2: do not clear global registry in final design; instead test with names that won't collide, OR test only after full package load in Task 3. For Task 2, implement registry and a tiny self-test that registers temporary tools then leaves them (or use a `Registry` class instance `default_registry`).

**Prefer instance-based registry to avoid clear issues:**

```python
# registry.py uses module-level _registry: dict[str, ToolSpec] = {}
# tests that need isolation can save/restore — or only assert APIs exist after quote_tools loads in Task 3.

```

Simplify Task 2 tests to unit-test `execute` unknown tool without clearing, by calling execute on a random name:

```python
def test_unknown_tool():
    from tools.registry import execute
    assert "error" in execute("__no_such_tool__", {})
```

And defer surface tests to Task 3 after real tools exist. Still implement full registry in Task 2.

- [ ] **Step 2: Run — fail on missing registry**

`cd backend && python -m pytest tests/test_tools_registry.py::test_unknown_tool -v`

- [ ] **Step 3: Implement registry.py**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from tools.params import CHAT_TOOL_JSON_BUDGET
from tools import trim

Handler = Callable[[dict], Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Handler
    surfaces: frozenset[str]


_REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    if not spec.surfaces:
        raise ValueError(f"{spec.name}: surfaces empty")
    _REGISTRY[spec.name] = spec


def all_specs() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def openai_tools(surface: str) -> list[dict]:
    out = []
    for spec in _REGISTRY.values():
        if surface in spec.surfaces:
            out.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            })
    return sorted(out, key=lambda t: t["function"]["name"])


def mcp_tools(surface: str) -> list[dict]:
    out = []
    for spec in _REGISTRY.values():
        if surface in spec.surfaces:
            out.append({
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.parameters,
            })
    return sorted(out, key=lambda t: t["name"])


def execute(name: str, args: dict | None = None, *, surface: str | None = None) -> Any:
    args = args or {}
    spec = _REGISTRY.get(name)
    if spec is None:
        return {"error": f"未知工具 {name}"}
    if surface is not None and surface not in spec.surfaces:
        return {"error": f"工具 {name} 不可用于 {surface} 面"}
    try:
        result = spec.handler(args if isinstance(args, dict) else {})
        result = trim.json_safe(result)
        if surface == "chat":
            result = trim.fit_json_budget(result, CHAT_TOOL_JSON_BUDGET)
        return result
    except Exception as e:  # noqa: BLE001
        return {"error": f"{name} 执行失败：{e}"}
```

`backend/tools/__init__.py`:

```python
"""AI / MCP tool registry package."""
from tools.registry import execute, mcp_tools, openai_tools, all_specs

__all__ = ["execute", "mcp_tools", "openai_tools", "all_specs"]
```

- [ ] **Step 4: Write `test_unknown_tool` + run pass**

- [ ] **Step 5: Commit**

```bash
git add backend/tools/registry.py backend/tools/__init__.py backend/tests/test_tools_registry.py
git commit -m "feat(tools): add ToolSpec registry and execute dispatch"
```

---

### Task 3: quote_tools (6) + wire chat.py / mcp_server.py

**Files:**
- Create: `backend/tools/quote_tools.py`
- Modify: `backend/tools/__init__.py` (import quote_tools)
- Modify: `backend/chat.py`
- Modify: `backend/mcp_server.py`
- Modify: `backend/tests/test_tools_registry.py` / handlers
- Test: `backend/tests/test_tools_handlers.py` (start with quote tests)

**Interfaces:**
- Produces: chat-surface tools: quote, valuation, reports, news, global_stock, kline
- Handler signature: `def _h(args: dict, *, surface: str = "mcp")` — **surface must reach handlers for limit clamp**. 

**Critical design detail:** `execute` must pass surface into handler. Update registry:

```python
# ToolSpec.handler becomes Callable[[dict, str], Any]  # args, surface
result = spec.handler(args, surface or "mcp")
```

Update Task 2 registry accordingly if not done — **do this in Task 3 before quote tools**.

- [ ] **Step 1: Change handler signature to `(args, surface)` and fix execute**

- [ ] **Step 2: Write quote handler tests (mock fetch_*)**

```python
from data_fetcher.base import FetchResult
import tools.quote_tools  # noqa: F401
from tools.registry import execute


def test_query_quote_unwrap(monkeypatch):
    import astock
    monkeypatch.setattr(
        astock,
        "fetch_quote",
        lambda codes: FetchResult(data={"600519": {"price": 1}}, source="tencent", chain="quote"),
    )
    out = execute("query_quote", {"codes": ["600519"]}, surface="chat")
    assert out["data"]["600519"]["price"] == 1
    assert out["_meta"]["source"] == "tencent"


def test_query_quote_bad_code():
    out = execute("query_quote", {"codes": ["1"]}, surface="chat")
    assert "error" in out
```

- [ ] **Step 3: Implement `quote_tools.py`**

Register all 6 tools. Pattern for FetchResult unwrap:

```python
def _meta_from(result):
    m = {"source": result.source, "stale": result.stale, "chain": result.chain}
    if result.cached_at:
        m["cached_at"] = result.cached_at
    if result.partial:
        m["partial"] = True
    return m
```

`query_quote` uses `validate_codes`; on None return `{"error":"codes 必须是最多 20 个 6 位数字"}`.

`query_kline`: clamp offset via `clamp_limit(surface,"query_kline", args.get("offset"))` — note kline uses `offset` as bar count not page offset.

`query_news`: `astock.fetch_news`; trim fields like old chat.

`query_reports`: keep field whitelist; use clamp_limit for row count.

Catch `DependencyMissing` and `AllSourcesFailed` inside each handler → `{"error": ...}`.

Surfaces: all six `frozenset({"chat","mcp"})`.

- [ ] **Step 4: Update `__init__.py`**

```python
from tools.registry import execute, mcp_tools, openai_tools, all_specs
from tools import quote_tools as _quote_tools  # noqa: F401

__all__ = ["execute", "mcp_tools", "openai_tools", "all_specs"]
```

- [ ] **Step 5: Wire chat.py**

- Remove inline `TOOLS = [...]` list and old `_exec_tool` body.
- Add:

```python
import tools as tools_mod

def _tools_chat():
    return tools_mod.openai_tools("chat")

# For _call_llm use_tools branch:
payload["tools"] = _tools_chat()

def _exec_tool(name: str, args: dict):
    return tools_mod.execute(name, args, surface="chat")
```

- Replace both `json.dumps(result, ensure_ascii=False)[:_TOOL_RESULT_CAP]` with `json.dumps(result, ensure_ascii=False)` (no slice).
- Remove `_TOOL_RESULT_CAP` or keep unused — **delete** it.
- Update `SYSTEM_PROMPT` tool list to mention the 6 quote tools for now (full 12 in Task 4).

- [ ] **Step 6: Wire mcp_server.py**

```python
import tools as tools_mod

SERVER_INFO = {"name": "vibe-research", "version": "0.2.0"}

# tools/list:
_result(rid, {"tools": tools_mod.mcp_tools("mcp")})

# tools/call:
data = tools_mod.execute(name, args, surface="mcp")
```

Remove `import chat` for tools (chat import may still be unused — delete it).

- [ ] **Step 7: Run tests**

```bash
cd backend && python -m pytest tests/test_tools_pagination.py tests/test_tools_registry.py tests/test_tools_handlers.py tests/test_fixes.py tests/test_api.py -v --tb=short
```

Expected: PASS (fix any monkeypatch that assumed old TOOLS length if any).

- [ ] **Step 8: Commit**

```bash
git commit -m "feat(tools): migrate quote tools and wire chat/mcp registry"
```

---

### Task 4: market_tools + funds_tools (complete Chat surface = 12)

**Files:**
- Create: `backend/tools/market_tools.py`
- Create: `backend/tools/funds_tools.py`
- Modify: `backend/tools/__init__.py`
- Modify: `backend/chat.py` SYSTEM_PROMPT (all 12)
- Extend: `backend/tests/test_tools_handlers.py`, `test_tools_pagination.py` (fund_flow via execute)

**Chat names after this task must equal:**

```python
CHAT_NAMES = {
  "query_quote","query_valuation","query_reports","query_news","query_global_stock",
  "query_kline","query_market_overview","query_radar","query_fund_flow",
  "query_margin","query_dragon_tiger","query_block_trade",
}
assert {t["function"]["name"] for t in openai_tools("chat")} == CHAT_NAMES
```

- [ ] **Step 1: Failing test for chat count == 12 and fund_flow pagination via execute**

```python
def test_chat_surface_twelve():
    import tools  # registers all imported domains
    from tools.registry import openai_tools
    names = {t["function"]["name"] for t in openai_tools("chat")}
    assert len(names) == 12

def test_fund_flow_pagination(monkeypatch):
    import astock
    rows = [{"date": str(i), "main_net": float(i)} for i in range(120)]
    monkeypatch.setattr(astock, "stock_fund_flow_120d", lambda code: rows)
    from tools.registry import execute
    p0 = execute("query_fund_flow", {"code": "600519"}, surface="chat")
    assert p0["meta"]["returned"] == 20
    assert p0["meta"]["next_offset"] == 20
    p1 = execute("query_fund_flow", {"code": "600519", "offset": 20}, surface="chat")
    assert set(x["date"] for x in p0["data"]) & set(x["date"] for x in p1["data"]) == set()
```

- [ ] **Step 2: Implement market_tools.py**

- `query_market_overview`: `market.get_overview()`; truncate `sectors` to clamp_limit for overview; attach meta if truncated.
- `query_radar`: `newsradar.get_radar(force=bool)`; `per_track = clamp_limit(surface,"query_radar", args.get("per_track"))`; each industry keep `items[:per_track]` with field whitelist (`title`/`url`/`published` or whatever keys exist — inspect one cached shape; keep title + link + time keys present); meta with truncated flag.
- `query_market_emotion`, `query_turnover_top`, `query_global_indices`: mcp-only surfaces.
- `query_hot_concepts`: mcp-only; requires code.

Emotion/turnover/hot/indices can be registered in this file with `surfaces=frozenset({"mcp"})` even though Task 5 is MCP-only — OK to register early.

- [ ] **Step 3: Implement funds_tools.py**

- `query_fund_flow`: validate code; fetch full list; `limit=clamp_limit(...)`; `offset=int(args.get("offset") or 0)`; `page_from_end` + `attach_page_meta`; empty → hint 东财风控.
- `query_margin` / `query_block_trade`: call astock with page_size=limit; if returns longer, slice; meta.
- `query_dragon_tiger`: full dict; chat+mcp.

- [ ] **Step 4: Import both in `__init__.py`**

- [ ] **Step 5: Update SYSTEM_PROMPT** listing all 12 Chat tools + truncated续取规则 (from spec §4 / §6.5)

- [ ] **Step 6: pytest pass + commit**

```bash
git commit -m "feat(tools): add market and funds tools for full Chat surface"
```

---

### Task 5: fundamentals_tools + events_tools (MCP-only)

**Files:**
- Create: `backend/tools/fundamentals_tools.py`
- Create: `backend/tools/events_tools.py`
- Modify: `__init__.py`
- Extend handler tests (one mock each + invalid code)

- [ ] **Step 1: Failing tests** — execute each new tool name with mocks; chat surface rejects `query_financials`

- [ ] **Step 2: Implement fundamentals** — bind exactly:

- `financials` → `astock.financials`
- `finance` → `astock.finance`
- `holders` → `astock.holder_num_change`
- `dividend` → `astock.dividend_history`
- `industry` → `astock.industry_comparison(top_n=clamp 5..50)`

- [ ] **Step 3: Implement events**

- `announcements` → `astock.announcements`
- `disclosure` → `astock.disclosure`
- `lockup` → `astock.lockup_expiry`
- `investor_qa` → `astock.investor_qa`; truncate answer/question fields to 500 chars with note in meta if needed

All `surfaces=frozenset({"mcp"})`.

- [ ] **Step 4: pytest + commit**

```bash
git commit -m "feat(tools): add fundamentals and events MCP tools"
```

---

### Task 6: personal_tools (watchlist, notes, get_note, digest)

**Files:**
- Create: `backend/tools/personal_tools.py`
- Modify: `__init__.py`
- Tests for list_notes meta-only, get_note window, digest missing, chat rejects personal

- [ ] **Step 1: Failing tests**

```python
def test_personal_mcp_only():
    from tools.registry import execute
    assert "error" in execute("list_notes", {}, surface="chat")
    assert "error" in execute("get_note", {"note_id": "x"}, surface="chat")

def test_list_watchlist(monkeypatch):
    import watchlist
    monkeypatch.setattr(watchlist, "get_state", lambda: {"items": [], "total": 0, "updated_at": None})
    from tools.registry import execute
    assert execute("list_watchlist", {}, surface="mcp")["total"] == 0

def test_get_note_content_window(monkeypatch):
    import notes
    monkeypatch.setattr(notes, "get_note", lambda nid: {"id": nid, "title": "t", "content": "a" * 25000, "kind": "问AI"})
    from tools.registry import execute
    out = execute("get_note", {"note_id": "n1"}, surface="mcp")
    assert out["meta"]["truncated"] is True
    assert len(out["content"]) == 20000
```

- [ ] **Step 2: Implement personal_tools.py**

- `list_watchlist` → `watchlist.get_state()`
- `list_notes` → `notes.list_notes`; clamp limit; attach pagination meta from total/offset/returned
- `get_note` → catch `notes.NoteError`; content window via `content_offset` / `content_limit` default 20000
- `get_latest_digest` → `digest.load_latest()`; if None error; else `{date, markdown: digest.to_markdown(d)}`

- [ ] **Step 3: Assert mcp count == 29**

```python
assert len(mcp_tools("mcp")) == 29
```

- [ ] **Step 4: pytest + commit**

```bash
git commit -m "feat(tools): add personal MCP tools including get_note"
```

---

### Task 7: Compliance + full handler matrix + remove hard-cut regression

**Files:**
- Modify: `backend/tests/test_compliance.py` or extend `test_tools_registry.py`
- Modify: `backend/tests/test_tools_handlers.py` — loop all specs
- Grep chat.py for `[:` tool cap — must be gone

- [ ] **Step 1: Tests**

```python
from compliance import assert_compliant
from tools.registry import all_specs, execute, openai_tools, mcp_tools

def test_all_descriptions_compliant():
    for spec in all_specs():
        assert_compliant(spec.description, context=spec.name)

def test_every_tool_execute_mocked_smoke(monkeypatch):
    # For tools needing network, monkeypatch the underlying astock/market/... functions
    # used by that tool to return minimal fixtures; then execute(name, minimal_args, surface="mcp")
    # Must not contain "未实现" / NotImplemented
    ...

def test_chat_no_string_hard_cap():
    import inspect, chat
    src = inspect.getsource(chat)
    assert "[:_TOOL_RESULT_CAP]" not in src
    assert "json.dumps(result, ensure_ascii=False)[" not in src
```

Implement smoke by maintaining `MIN_ARGS = {"query_quote": {"codes":["600519"]}, ...}` for all 29 names and patching modules at once with broad lambdas returning `[]`/`{}`/`FetchResult(...)`.

- [ ] **Step 2: Fix any non-compliant descriptions**

- [ ] **Step 3: Full pytest**

```bash
cd backend && python -m pytest tests/ -v --tb=short -m "not live"
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git commit -m "test(tools): compliance and full tool contract coverage"
```

---

### Task 8: Feat doc + backlog cleanup

**Files:**
- Create: `docs/feats/10-mcp-tool-expansion.md`
- Modify: `docs/feats/99-backlog.md` (remove §10 MCP section including tool table)
- Update feats README/index if present

- [ ] **Step 1: Write `10-mcp-tool-expansion.md`** summarizing goal, surfaces 12/29, scheme B, file layout, acceptance — mirror other feat docs' style (read `docs/feats/08-watchlist-persistence.md` header structure).

- [ ] **Step 2: Remove §10 from backlog**; bump backlog「最后更新」date.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs: promote feat 10 MCP tool expansion out of backlog"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Domain-split `*_tools.py` | 3–6 |
| Chat 12 / MCP 29 + get_note | 4, 6 |
| fetch_quote / fetch_kline / fetch_news | 3 |
| Scheme B meta + page_from_end | 1, 4, 6 |
| Abolish `[:6000]` | 3, 7 |
| fit_json_budget on chat | 2, 7 |
| Cross-surface reject | 2, 6 |
| Compliance descriptions | 7 |
| Feat doc + backlog | 8 |
| No scheme C / no HTTP self-call | Global constraints |

No TBD placeholders. Handler signature `(args, surface)` must be applied consistently from Task 3 onward.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-19-mcp-tool-expansion.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration  

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch with checkpoints  

**Which approach?**
