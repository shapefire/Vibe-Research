# Changelog

All notable changes to Vibe-Research are documented in this file.

## [Unreleased]

### Added

- **数据源 fallback 链**（feat 02）：`backend/data_fetcher/` 模块，行情链 `tencent` → `stale_cache`
- **`GET /api/health/sources`**：数据源与 fallback chain 健康状态（鉴权白名单，与 `/api/health` 相同）
- API 响应可选 **`_meta`** 字段：`source`、`stale`、`partial`、`cached_at`、`chain`
- 东财缓存端点（margin / fund-flow 等）fetch 失败时回退过期 `_DC_CACHE` 并标注 `_meta.stale: true`
- 前端 **`SourceStatusBanner`**：chain degraded 时全局黄条提示
- 自选股 / 个股页 **「滞后」角标**（`StaleBadge`）
- `api.quoteWithMeta()`：前端解析 quote 响应的 `_meta`

### Changed

- **Breaking**：`/api/quote` 全部数据源失败时 HTTP 状态码由 **502 改为 503**，响应体含结构化 `attempts` 数组
- `/api/kline`：mootdx 连接失败时返回 **503**（`AllSourcesFailed`）；未安装仍为 **501**
- `/api/news`：经 akshare chain 包装，单源失败返回 **503**
- `portfolio.py` 持仓行情改走 **`astock.fetch_quote`**（含 stale 缓存降级）

### Fixed

- 腾讯行情源短暂不可用时，自选股 / `/api/quote` 可降级展示内存缓存（标注 `stale: true`），避免白屏
