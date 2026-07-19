# Feat 10 · MCP / AI 工具面扩展 — 设计规格

> 日期：2026-07-19（修订：完备性审视 + **完整性方案 B**）  
> 状态：待确认  
> 来源：`docs/feats/99-backlog.md` §10  
> 取代：backlog 中 feat 10 的工具清单草案

---

## 0. 完备性审视结论（相对初版的硬约束）

初版规格存在以下风险，**本修订一律堵死**，禁止实现时用占位/半截逻辑交差：

| 风险 | 初版问题 | 修订要求 |
|------|----------|----------|
| 数据路径弱于 HTTP API | `query_quote` 写死 `tencent_quote`，而 `/api/quote` 已走 `fetch_quote`（含 fallback） | 凡 API 已有 fallback 链的能力，工具必须走同一数据函数 |
| 「与 /api 相同」过虚 | 未绑定函数名、参数、返回裁剪 | §5 给出**逐工具契约** |
| 模块名冲突 | `tools/market.py` 与顶层 `market.py` 易混 | 域文件统一 `*_tools.py` |
| 载荷炸弹 / 半截 JSON | 全量塞入 + Chat `[:6000]` 字符硬切 | **方案 B**：语义分页 + `meta` 信封；**废除**字符串硬切（见 §4） |
| 半截个人数据 | 仅 `list_notes` 无全文 | MCP 增加 `get_note` |
| 参数不可用 | `hot_concepts` 要 `code`；`industry` 要 `top` | Schema 与真实签名一致 |
| 异常漏捕 | 未要求 `AllSourcesFailed` / `FetchResult` | §6 统一包装 |
| 测试过稀 | 「每域 1 个」 | **每个工具**注册 + 契约测；分页续取测 |
| 校验缺失 | 无 6 位代码校验 | 共享 `params.py` |

**质量门禁：** 无 stub handler；任意工具结果对 Chat/MCP 均可合法 `json.loads`；`meta.truncated=true` 时可用参数续取剩余数据。

---

## 1. 目标

将 Vibe-Research 的 AI 工具面从当前 5 个 `chat.TOOLS` 扩展为完整、可调用的数据工具层：

- **MCP**：全量只读工具（行情 / 市场 / 资金 / 基本面 / 事件 / 个人数据）。
- **网页 Chat**：12 个对话高频工具（控 token）。
- **按域注册表**统一 schema + handler；**方案 B** 保证默认可控、多轮可凑齐全量。

**注册表规模：** **29** 个工具（Chat+MCP 共有 12；仅 MCP 17，含 `get_note`）。

**本功能明确不做：**

- 写操作工具（增删改自选 / 笔记）
- 工具输出中的买卖建议、评分、目标价
- 图片 OCR / Vision
- Handler 经 HTTP 打本机 FastAPI
- Electron / SQLite / Phase 3 其他项
- 从 `app.py` 大拆共享 HTTP 缓存
- **方案 C**（为本 feat 再拆「摘要工具 / 明细工具」双注册）— 个别工具后续可从 B 升级为 C

---

## 2. 架构

### 2.1 包结构（禁止与顶层模块同名）

```
backend/tools/
  __init__.py              # 导出 openai_tools / mcp_tools / execute；导入全部 *_tools 完成注册
  registry.py              # ToolSpec、register、surface 过滤、execute
  params.py                # validate_a_code / validate_codes / clamp_int / 面别默认 limit
  trim.py                  # page_slice、attach_page_meta、fit_json_budget、JSON 安全
  quote_tools.py
  market_tools.py
  funds_tools.py
  fundamentals_tools.py
  events_tools.py
  personal_tools.py
```

**禁止**创建 `backend/tools/market.py`、`notes.py` 等同名文件。

### 2.2 ToolSpec

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str                 # 中文；须说明可分页续取（若适用）
    parameters: dict                 # 完整 JSON Schema（含 limit/offset 等）
    handler: Callable[[dict], Any]
    surfaces: frozenset[str]         # {"chat","mcp"} 的非空子集
```

### 2.3 对外 API

| 函数 | 行为 |
|------|------|
| `openai_tools(surface) -> list` | OpenAI tools 数组 |
| `mcp_tools(surface) -> list` | MCP `{name,description,inputSchema}` |
| `execute(name, args, *, surface=None) -> Any` | 分发 + 跨面拒绝 + 统一异常；Chat 面可再走 `fit_json_budget` |

### 2.4 消费方

- **`chat.py`**
  - `TOOLS = openai_tools("chat")`
  - `_exec_tool` → `tools.execute(..., surface="chat")`
  - **删除**对工具结果 `json.dumps(...)[:_TOOL_RESULT_CAP]` 的字符串切片；改为注入**完整合法 JSON**（由 execute/trim 保证低于预算）
  - `SYSTEM_PROMPT`：列出 12 个 Chat 工具；并写明「若返回 `meta.truncated=true`，用更大 `limit` 或 `offset=meta.next_offset` 再调同一工具；禁止臆造未返回数据」
- **`mcp_server.py`**
  - 使用 `mcp_tools` / `execute(..., surface="mcp")`；不依赖 `chat.TOOLS`
  - MCP **不做**字符预算裁剪（只遵守参数硬顶）
  - `SERVER_INFO["version"]` → 如 `0.2.0`

### 2.5 数据面规则

- Handler 只调：`astock` / `gstock` / `market` / `newsradar` / `watchlist` / `notes` / `digest`。
- 函数名以 `app.py` 路由体为准（§5 写死）。

---

## 3. 工具面分层

| 面 | 数量 | 策略 |
|----|------|------|
| **chat** | 12 | §3.1 |
| **mcp** | 29 | 全部 |

### 3.1 Chat 白名单

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

### 3.2 仅 MCP

**market：** `query_market_emotion`、`query_turnover_top`、`query_hot_concepts`、`query_global_indices`  
**fundamentals：** `query_financials`、`query_finance`、`query_holders`、`query_dividend`、`query_industry`  
**events：** `query_announcements`、`query_disclosure`、`query_lockup`、`query_investor_qa`  
**personal：** `list_watchlist`、`list_notes`、`get_note`、`get_latest_digest`

跨面拒绝：chat 调用仅 MCP 名 → `{"error":"工具 … 不可用于 chat 面"}`。

---

## 4. 完整性与分页（方案 B）— 生产基线

### 4.1 问题分层

| 层 | 行为 | 处理 |
|----|------|------|
| **有害：字符硬切** | `json.dumps(result)[:6000]` | **废除**；会导致半截 JSON、功能不可用 |
| **可控：语义分页** | 默认只返回最近 N 条 / 每赛道 N 条 | **保留**；用 `meta` 标明并支持续取 |

### 4.2 分页信封（发生裁剪或支持分页的列表工具必须遵守）

```json
{
  "data": [ ],
  "meta": {
    "truncated": true,
    "total": 120,
    "returned": 20,
    "offset": 0,
    "next_offset": 20,
    "hint": "还有剩余数据；使用 offset=20 或增大 limit 继续取"
  }
}
```

规则：

- `truncated=false` 且一次拿全时：可省略 `meta`，或带 `truncated:false`（实现任选，测试两者皆可）。
- `data` 始终是**完整可解析**的当前页；禁止静默丢字段却不标 `truncated`。
- 时间序列（资金流等）：默认取**最近**一段；`offset` 表示从序列末尾往前的起点（实现文档化：`offset=0` 为最近一页，`offset=20` 为再往前一页），**不得留重叠漏洞或空洞**（契约测试锁定）。
- 非列表小对象（估值、龙虎榜聚合 dict 等）：一般不分页；仅当 Chat 预算仍超标时由 `fit_json_budget` 降级（见 §4.4）。

### 4.3 按面默认值与硬顶

| 工具 | Chat 默认 / 硬顶 | MCP 默认 / 硬顶 | 续取参数 |
|------|------------------|-----------------|----------|
| `query_fund_flow` | 20 / 60 | 60 / **120** | `limit`,`offset` |
| `query_kline` | `offset` 根数默认 60 / 硬顶 120 | 同左 | 已有 `offset`（根数）；本工具语义保持与 API 一致，不另造第二套 offset |
| `query_radar` | `per_track` 默认 5 / 硬顶 10 | 10 / 30 | `per_track`；`force` 仅刷新缓存 |
| `query_market_overview` | `sectors` 最多 30 | 最多 50 | 本轮不分页续取板块（全表本身有限）；超则标 truncated |
| `query_margin` / `block_trade` / `announcements` / `investor_qa` / `dividend` 等 | 15 / 30 | 30 / 50 | `limit`（必要时 `offset`） |
| `query_holders` | 10 / 20 | 15 / 30 | `limit` |
| `query_disclosure` | — | ≤20 / 可用 limit | `limit` |
| `list_notes` | — | 20 / 50 | 已有 `limit`,`offset`；返回须带分页 meta |
| `get_note` | — | 全文；content **≤20000** 字一次给满；超出则字符窗 + `content_offset` / `next_content_offset` | 见 §5.6 |
| `query_reports` / `query_news` | 15 / 20 | 15 / 20 | `limit` |

`params.py` 提供 `limit_for(surface, tool_name, raw)`，按上表 clamp。

### 4.4 Chat 字符预算（替代 `[:6000]`）

- 常量：`CHAT_TOOL_JSON_BUDGET = 8000`（字符，可配置；替代旧 `_TOOL_RESULT_CAP` 的**硬切**语义）。
- `execute(..., surface="chat")` 在 handler 返回后调用 `trim.fit_json_budget(payload, budget)`：
  1. 若 `json.dumps` 长度 ≤ budget → 原样返回；
  2. 若 payload 含列表型 `data` → **从当前页尾部丢弃更旧/更靠后的元素**，同步更新 `meta.truncated/returned/next_offset/hint`，直到 ≤ budget；
  3. 若仍超（巨大单对象）→ 保留关键标量字段 + `meta.truncated=true` + `hint` 提示改用 MCP 或缩小参数；**仍保证合法 JSON**。
- **禁止**任何路径再对 JSON 字符串做 `[:N]`。

### 4.5 完整性如何保障（验收语义）

1. **单次调用**：当前页数据字段完整、JSON 可解析。  
2. **全量获取**：Agent/测试按 `next_offset`（或增大 `limit` 至硬顶）多轮调用，拼接后覆盖 `total`（资金流等）。  
3. **MCP**：硬顶允许一次取到数据源上限（如资金流 120），减少往返。  
4. **不臆造**：prompt + description 禁止补全未返回区间。

### 4.6 明确不采用（本 feat）

- 方案 A：取消语义裁剪只靠更大 CAP。  
- 方案 C：再注册平行的摘要/明细工具对（可作后续优化入口，不进基线）。

---

## 5. 逐工具契约（实现必须满足）

通用约定：

- A 股 `code` → `validate_a_code`；非法 → `{"error":"代码必须是 6 位数字"}`。
- `query_quote.codes` 去重后最多 20。
- `FetchResult` → `{"data": result.data, "_meta": {source,stale,chain,...}}`（源 meta 用 `_meta`，分页用 `meta`，避免键冲突）。
- 空列表允许；加 `hint`；禁止假数据。

### 5.1 quote_tools

| 工具 | 面 | 调用 | 参数要点 | 返回 |
|------|----|------|----------|------|
| `query_quote` | C | `astock.fetch_quote` | `codes[]` | 解包 FetchResult；`AllSourcesFailed`→error |
| `query_valuation` | C | `astock.full_valuation` | `code` | dict |
| `query_reports` | C | `eastmoney_reports(..., max_pages=1)` | `code`,`limit` | 字段裁剪；分页 meta 若截断 |
| `query_news` | C | `astock.fetch_news`（与 API 新闻链一致） | `code`,`limit` | 字段裁剪；解包 |
| `query_global_stock` | C | `gstock.us_hk_stock` | `symbol` | 未找到→error |
| `query_kline` | C | `astock.fetch_kline` | `code`,`category` 默认 4，`offset` 默认 60 硬顶 120 | 解包；DependencyMissing / AllSourcesFailed |

### 5.2 market_tools

| 工具 | 面 | 调用 | 参数 | 返回 |
|------|----|------|------|------|
| `query_market_overview` | C | `market.get_overview` | 无；sectors 按面截断 | sentiment 全量 + sectors 截断 + meta |
| `query_radar` | C | `newsradar.get_radar` | `force` 默认 false；`per_track` 按面 | 摘要：stats + 每赛道 items[:per_track] + meta（含各赛道 total） |
| `query_market_emotion` | M | `get_short_term_emotion` | 无 | 空则 hint |
| `query_turnover_top` | M | `get_turnover_top` | 无 | 原样 |
| `query_hot_concepts` | M | `astock.hot_concepts` | **`code` required** | list + 空 hint |
| `query_global_indices` | M | `get_global_indices` | 无 | list |

### 5.3 funds_tools

| 工具 | 面 | 调用 | 参数 | 返回 |
|------|----|------|------|------|
| `query_fund_flow` | C | `stock_fund_flow_120d` | `code`,`limit`,`offset`（按 §4.3） | `data` 当前页 + **必须**可续取的 meta；空加风控 hint |
| `query_margin` | C | `margin_trading` | `code`,`limit` | 页 + meta |
| `query_dragon_tiger` | C | `dragon_tiger_board` | `code` | 聚合 dict（一般不分页） |
| `query_block_trade` | C | `block_trade` | `code`,`limit` | 页 + meta |

### 5.4 fundamentals_tools

| 工具 | 面 | 调用 | 参数 | 返回 |
|------|----|------|------|------|
| `query_financials` | M | `financials` | `code` | DependencyMissing→error |
| `query_finance` | M | `finance` | `code` | 空 dict + hint |
| `query_holders` | M | `holder_num_change` | `code`,`limit` | 页 + meta |
| `query_dividend` | M | `dividend_history` | `code`,`limit` | 页 + meta |
| `query_industry` | M | `industry_comparison` | **`top` 5–50**，默认 20 | `{top,bottom,total}` |

### 5.5 events_tools

| 工具 | 面 | 调用 | 参数 | 返回 |
|------|----|------|------|------|
| `query_announcements` | M | `announcements` | `code`,`limit` | 页 + meta |
| `query_disclosure` | M | `disclosure` | `code`,`limit` | 页 + meta；DependencyMissing |
| `query_lockup` | M | `lockup_expiry` | `code` | dict |
| `query_investor_qa` | M | `investor_qa` | `code`,`limit` | 页 + meta；单字段文本 ≤500 字（超则该字段截断并标 truncated） |

### 5.6 personal_tools

| 工具 | 面 | 调用 | 参数 | 返回 |
|------|----|------|------|------|
| `list_watchlist` | M | `watchlist.get_state` | 无 | 全量只读（通常无需分页） |
| `list_notes` | M | `notes.list_notes` | `kind`,`q`,`limit`,`offset` | `{items,total}` + 分页 meta |
| `get_note` | M | `notes.get_note` | `note_id`；可选 `content_offset` 默认 0，`content_limit` 默认 20000 | 含 content 窗；超长则 meta.truncated + next_content_offset；NoteError→error |
| `get_latest_digest` | M | `load_latest` + `to_markdown` | 无 | `{date,markdown}` 或 error；markdown 已合规 |

---

## 6. 数据流、错误与非功能

### 6.1 调用链

```
Chat / MCP
  → tools.execute(name, args, surface=…)
      → 查表 + surface 校验
      → handler（内含 params clamp + page_slice + attach_page_meta）
      → surface=="chat" 时 fit_json_budget
      → 失败：{"error": str}
  → Chat：完整 json.dumps 注入（无 [:N]）
  → MCP：文本 content；含 error 则 isError
```

### 6.2 必须捕获

`DependencyMissing`、`AllSourcesFailed`、`NoteError`、其它 `Exception` → error dict。

### 6.3 JSON 安全

`datetime` / 非有限 float 等须可 dumps。

### 6.4 缓存

本轮不拆 HTTP `_DC_CACHE`；直调数据层；禁止假数据 handler。

### 6.5 SYSTEM_PROMPT

12 工具列表 + 合规句段 + **截断续取说明**（§4）。

---

## 7. 合规

- 全部 description `assert_compliant` / `scan_text`。
- Handler 不做荐股润色。
- digest markdown 复用现有合规路径。

---

## 8. 测试与验收（反 demo）

### 8.1 文件

- `test_tools_registry.py` — 注册、surface、跨面  
- `test_tools_handlers.py` — 每工具 mock 契约  
- `test_tools_pagination.py` — 方案 B 专测  

### 8.2 最低覆盖

1. Chat 工具数 12；MCP 29（含 `get_note`）  
2. 每工具 mock execute 成功形状  
3. Chat 拒绝 `list_notes` / `get_note`  
4. 非法 code → error  
5. FetchResult 解包  
6. **资金流 120 条：第一页 + next_offset；第二页无重叠、无空洞，并集覆盖**  
7. **radar 每赛道 items ≤ per_track，且 meta 含 total**  
8. **Chat 路径：超大 payload 经 fit_json_budget 后仍可 json.loads；源码/行为无 `[:_TOOL_RESULT_CAP]` 式硬切**  
9. description 合规  
10. `mcp_server` 不引用 `chat.TOOLS`  

### 8.3 验收

1. Chat body `tools` 长度 12；mock tool 循环可跑通。  
2. MCP list=29；personal 抽样非 stub。  
3. 相关 pytest 全绿。  
4. 无写操作工具。  
5. 文档：`docs/feats/10-mcp-tool-expansion.md`；从 backlog 移除 §10。

---

## 9. 实现顺序

1. `params` / `trim`（page_meta + fit_json_budget）+ 分页测试（红→绿）  
2. `registry` + 迁移升级原 5 工具 + 接通 chat/mcp（去掉字符串硬切）  
3. Chat 新增工具（含 fund_flow / radar 分页）  
4. MCP-only + `get_note` 字符窗  
5. SYSTEM_PROMPT + 合规 + 全契约测试  
6. feat 文档与 backlog 清理  

禁止空壳 name 合入。

---

## 10. 决策记录

| 决策点 | 选择 |
|--------|------|
| 范围 | 注册表 + P1–P4 全包 + `get_note` |
| Chat vs MCP | 12 / 29 |
| 完整性 | **方案 B**（语义分页 + meta；废除字符硬切） |
| 方案 C | 本 feat 不做；可作后续单工具升级 |
| 注册表形态 | `*_tools.py` |
| 数据路径 | 与生产 API 对齐 |
| 跨面 | surface 强制拒绝 |
| HTTP 缓存拆分 | 不做 |

---

## 11. 修订摘要

1. 29 工具 + `get_note`  
2. 逐工具契约写死  
3. `*_tools.py` 命名  
4. fallback 链对齐  
5. 每工具测试  
6. **方案 B 专章**：分页信封、按面限额、`fit_json_budget`、废除 `[:6000]`  

---

*请确认本修订版后，再进入 writing-plans。*
