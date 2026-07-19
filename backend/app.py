"""Vibe-Research 后端 —— A股数据层 HTTP 接口（FastAPI）。

端点全部在 /api 下，前端 vite 代理 /api → localhost:8900。
只读、无状态、按用户传入代码返回客观数据。不预置标的、不建议。

启动：
    uvicorn app:app --host 127.0.0.1 --port 8900
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

import astock
import chat as chat_layer
import cli_runtime
import compare as compare_mod
import digest as digest_mod
from data_fetcher.base import AllSourcesFailed, FetchResult
from data_fetcher.registry import registry
import gstock
import newsradar
import portfolio as pf
import market
import myreports as mr
import notes as notes_mod
from env_loader import load_env_file

_env_file_loaded = load_env_file()

app = FastAPI(title="Vibe-Research API", version="0.1.3")

_log = logging.getLogger("vibe-research")

_scheduler = None
if os.getenv("VR_SCHEDULER_ENABLED", "true").lower() == "true":
    from scheduler import Scheduler
    from jobs import daily_digest as daily_digest_job
    from jobs import portfolio_refresh as portfolio_refresh_job
    from jobs import radar_cache_warm as radar_cache_warm_job

    _tz = os.getenv("VR_DIGEST_TIMEZONE", "Asia/Shanghai")
    _digest_time = os.getenv("VR_DIGEST_TIME", "18:00").strip()
    _jobs = os.getenv("VR_JOBS", "portfolio_refresh,daily_digest")
    _scheduler = Scheduler(timezone=_tz)
    _scheduler.register(portfolio_refresh_job.spec())
    _scheduler.register(daily_digest_job.spec())
    _scheduler.register(radar_cache_warm_job.spec())
    _scheduler.start()
    _log.info(
        "scheduler enabled timezone=%s digest_time=%s jobs=%s",
        _tz,
        _digest_time,
        _jobs,
    )
    print(
        f"[vibe-research] scheduler started · timezone={_tz} · digest_time={_digest_time} · jobs={_jobs}",
        file=sys.stderr,
    )
else:
    print("[vibe-research] scheduler disabled (VR_SCHEDULER_ENABLED=false)", file=sys.stderr)

if not _env_file_loaded:
    print(
        "[vibe-research] backend/.env not found — using system env / defaults only",
        file=sys.stderr,
    )

# CORS：默认放开（本地自托管友好）；公网部署时用 VR_ALLOW_ORIGINS 收紧成白名单。
#   例：VR_ALLOW_ORIGINS="https://myhost"  （逗号分隔多个）
_ORIGINS = [o.strip() for o in os.environ.get("VR_ALLOW_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 可选鉴权：设了 VR_API_KEY 就要求所有 /api/* 带 `Authorization: Bearer <key>`
#   （本地自托管不设=开放；公网部署务必设，否则别人能读你的持仓/调你的后端）。
_API_KEY = os.environ.get("VR_API_KEY", "").strip()
_HEALTH_PATHS = {"/api/health", "/api/health/sources"}


@app.middleware("http")
async def _require_api_key(request: Request, call_next):
    if (
        _API_KEY
        and request.method != "OPTIONS"
        and request.url.path.startswith("/api/")
        and request.url.path not in _HEALTH_PATHS
    ):
        if request.headers.get("authorization", "") != f"Bearer {_API_KEY}":
            return JSONResponse({"detail": "未授权：缺少或错误的 API Key（VR_API_KEY）"}, status_code=401)
    return await call_next(request)

_CODE_RE = r"^\d{6}$"


def _validate(code: str) -> str:
    code = (code or "").strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(400, "代码必须是 6 位数字")
    return code


@app.get("/api/health")
def health():
    return {"ok": True, "service": "vibe-research-api", "version": "0.1.3"}


@app.get("/api/health/sources")
def health_sources():
    """数据源与 fallback chain 健康状态（只读内存 registry）。"""
    try:
        _probe_idle_sources()
        return registry.to_dict()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"健康状态读取异常：{e}") from e


_PROBE_CODE = "600519"


def _probe_idle_sources() -> None:
    """惰性探测尚未调用的 kline/news 链路，刷新 registry 真实状态。"""
    snap = registry.to_dict()
    sources = snap.get("sources", {})
    if sources.get("mootdx", {}).get("status") == "idle":
        try:
            astock.fetch_kline(_PROBE_CODE, category=4, offset=5)
        except Exception:  # noqa: BLE001
            pass
    if sources.get("akshare", {}).get("status") == "idle":
        try:
            astock.fetch_news(_PROBE_CODE, limit=3)
        except Exception:  # noqa: BLE001
            pass


def _meta_from(result: FetchResult) -> dict:
    meta = {"source": result.source, "stale": result.stale, "chain": result.chain}
    if result.cached_at:
        meta["cached_at"] = result.cached_at
    if result.partial:
        meta["partial"] = True
    return meta


def _sources_failed(exc: AllSourcesFailed, label: str) -> HTTPException:
    return HTTPException(
        503,
        detail={
            "detail": f"{label}所有数据源不可用",
            "chain": exc.endpoint,
            "attempts": exc.attempts,
        },
    )


class LLMConfig(BaseModel):
    provider: str = ""       # cli-* = 订阅接入（调本机 CLI）；其余 = API 接入
    baseURL: str = ""        # 订阅接入时留空
    apiKey: str = ""         # 订阅接入时留空
    model: str


class ChatReq(BaseModel):
    messages: list[dict]
    context: str = ""
    llm: LLMConfig


@app.post("/api/chat")
def chat(req: ChatReq):
    """系统 AI 对话，**流式** NDJSON（每行一个事件 {type: tool|delta|done|error}）。

    - API 接入：OpenAI 兼容 function-calling，边流答案边推工具调用事件。
    - 订阅接入（provider=cli-*）：调本机已登录的 CLI，stdout 边出边流（数据靠 context）。
    配置错误（缺 key / 未装 CLI）走 HTTP 400；运行时错误走流内 error 事件。用户配置随请求传入，后端不持久化。
    """
    if not req.messages:
        raise HTTPException(400, "messages 不能为空")
    if not req.llm.model:
        raise HTTPException(400, "缺少模型配置，请先在「接入 AI」里选择")

    is_cli = req.llm.provider.startswith("cli-")
    if is_cli:
        kind = req.llm.provider[4:]
        if not cli_runtime.detect_cli(kind):
            raise HTTPException(400, f"未检测到「{kind}」对应的本机命令。请先安装并登录该 CLI，或改用「API 接入」。")
    elif not req.llm.apiKey or not req.llm.baseURL:
        raise HTTPException(400, "缺少 Base URL 或 API Key，请先在「接入 AI」里填写")

    cfg = req.llm.model_dump()

    def gen():
        try:
            events = (chat_layer.run_chat_cli_stream if is_cli else chat_layer.run_chat_stream)(cfg, req.messages, req.context)
            for ev in events:
                yield json.dumps(ev, ensure_ascii=False) + "\n"
        except Exception as e:  # noqa: BLE001 — 运行时错误以流内事件上报，不中断连接
            yield json.dumps({"type": "error", "message": f"对话失败：{e}"}, ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


class HoldingIn(BaseModel):
    code: str
    shares: float
    cost: float


@app.get("/api/portfolio")
def portfolio_get():
    """持仓 + 实时盈亏（浮动盈亏红涨绿跌）。"""
    try:
        return {"data": pf.get_portfolio()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"持仓读取异常：{e}") from e


@app.post("/api/portfolio/holding")
def portfolio_add(h: HoldingIn):
    """加一笔持仓（同代码按加权平均成本合并）。存本地，不上传。"""
    code = (h.code or "").strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(400, "代码必须是 6 位数字")
    if h.shares <= 0:
        raise HTTPException(400, "数量必须大于 0")
    # 成本价不限正负：融券 / 返息 / 摊薄后为负成本等情形按结果计算，用户想怎么输就怎么输。
    return {"data": pf.add_holding(code, h.shares, h.cost)}


@app.delete("/api/portfolio/holding")
def portfolio_remove(code: str = Query(...)):
    return {"data": pf.remove_holding(code.strip())}


# ---- 我的研报（用户上传自己的研报，存本地、不上传、不进开源仓库）----

class ReportIn(BaseModel):
    name: str
    content_b64: str


@app.get("/api/myreports")
def myreports_list():
    return {"data": mr.list_reports()}


@app.post("/api/myreports")
def myreports_upload(r: ReportIn):
    """上传一份研报（base64）→ 存本地 + 按文件名自动打行业标签。"""
    try:
        return {"data": mr.save_report(r.name, r.content_b64)}
    except mr.ReportError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/myreports/file/{rid}")
def myreports_file(rid: str):
    """下载/预览某份研报原文件。"""
    hit = mr.report_path(rid)
    if not hit:
        raise HTTPException(404, "研报不存在")
    path, name = hit
    return FileResponse(str(path), filename=name)


@app.delete("/api/myreports/{rid}")
def myreports_delete(rid: str):
    return {"data": {"ok": mr.delete_report(rid)}}


# ---- 研究记录（用户主动保存的 AI 复盘/要点/问答，存本地、不上传）----

class NoteIn(BaseModel):
    kind: str
    title: str
    content: str
    tags: list[str] = []
    snapshot: dict | None = None


class MigrateIn(BaseModel):
    notes: list[dict]


class CompareRequest(BaseModel):
    id_a: str
    id_b: str


def _note_summary(meta: dict) -> dict:
    return {
        "id": meta.get("id"),
        "title": meta.get("title"),
        "ts": meta.get("ts", 0),
        "kind": meta.get("kind"),
        "tags": meta.get("tags") or [],
    }


def _compare_response(
    meta_a: dict,
    meta_b: dict,
    *,
    comparable: bool,
    diff: dict | None = None,
    reason: str | None = None,
) -> dict:
    return {
        "note_a": _note_summary(meta_a),
        "note_b": _note_summary(meta_b),
        "comparable": comparable,
        "reason": reason,
        "diff": diff or {},
    }


@app.get("/api/notes")
def notes_list(
    kind: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return {"data": notes_mod.list_notes(kind=kind, q=q, limit=limit, offset=offset)}


@app.post("/api/notes/migrate")
def notes_migrate(body: MigrateIn):
    """从 localStorage 批量导入研究记录（一次性迁移）。"""
    try:
        return {"data": notes_mod.migrate_notes(body.notes)}
    except notes_mod.NoteError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/api/notes")
def notes_delete_all():
    """清空所有研究记录。"""
    return {"data": notes_mod.delete_all_notes()}


@app.post("/api/notes/compare")
def notes_compare(body: CompareRequest):
    """对比两条笔记的 snapshot 客观数据 delta。"""
    if body.id_a == body.id_b:
        raise HTTPException(400, "不能对比同一条笔记")
    meta_a = notes_mod.get_meta(body.id_a)
    meta_b = notes_mod.get_meta(body.id_b)
    if not meta_a or not meta_b:
        raise HTTPException(404, "笔记不存在")
    snap_a = meta_a.get("snapshot")
    snap_b = meta_b.get("snapshot")
    if not isinstance(snap_a, dict) or not snap_a or not isinstance(snap_b, dict) or not snap_b:
        resp = _compare_response(meta_a, meta_b, comparable=False, reason="missing_snapshot")
        _log.info(
            "compare id_a=%s id_b=%s comparable=%s keys=%d",
            body.id_a, body.id_b, False, 0,
        )
        return {"data": resp}
    tree = compare_mod.diff_snapshots(snap_a, snap_b)
    flat = compare_mod.flatten_diff(tree)
    if not flat:
        resp = _compare_response(meta_a, meta_b, comparable=False, reason="no_common_keys")
        _log.info(
            "compare id_a=%s id_b=%s comparable=%s keys=%d",
            body.id_a, body.id_b, False, 0,
        )
        return {"data": resp}
    if meta_a.get("ts", 0) > meta_b.get("ts", 0):
        meta_a, meta_b = meta_b, meta_a
        flat = compare_mod.swap_before_after(flat)
    resp = _compare_response(meta_a, meta_b, comparable=True, diff=flat)
    _log.info(
        "compare id_a=%s id_b=%s comparable=%s keys=%d",
        body.id_a, body.id_b, True, len(flat),
    )
    return {"data": resp}


@app.get("/api/notes/by-tag")
def notes_by_tag(
    tag: str,
    has_snapshot: bool = False,
    limit: int = Query(50, ge=1, le=200),
):
    """按标的 tag 筛选笔记，供对比选择器使用。"""
    tag = _validate(tag)
    return {"data": notes_mod.list_by_tag(tag, has_snapshot=has_snapshot, limit=limit)}


@app.get("/api/notes/{note_id}")
def notes_get(note_id: str):
    try:
        return {"data": notes_mod.get_note(note_id)}
    except notes_mod.NoteError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/notes")
def notes_create(n: NoteIn):
    try:
        return {"data": notes_mod.add_note(
            kind=n.kind,
            title=n.title,
            content=n.content,
            tags=n.tags,
            snapshot=n.snapshot,
        )}
    except notes_mod.CapacityExceeded as e:
        raise HTTPException(409, str(e)) from e
    except notes_mod.NoteError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/api/notes/{note_id}")
def notes_delete(note_id: str):
    if not notes_mod.delete_note(note_id):
        raise HTTPException(404, "笔记不存在")
    return {"data": {"ok": True, "id": note_id}}


class CloseIn(BaseModel):
    code: str
    date: str
    price: float
    shares: float
    cost: float


@app.post("/api/portfolio/close")
def portfolio_close(c: CloseIn):
    """记一笔已清仓（已实现盈亏）。存本地。"""
    code = (c.code or "").strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(400, "代码必须是 6 位数字")
    if c.price <= 0 or c.shares <= 0:
        raise HTTPException(400, "清仓价与股数必须大于 0")
    # 买入成本不限正负（同持仓录入）：按 (清仓价 - 成本) × 股数 的结果计算已实现盈亏。
    date = (c.date or "").strip()
    if not date:
        raise HTTPException(400, "请填清仓日期")
    from datetime import datetime
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "清仓日期格式应为 YYYY-MM-DD") from None
    return {"data": pf.close_position(code, date, c.price, c.shares, c.cost)}


@app.delete("/api/portfolio/close")
def portfolio_close_remove(index: int = Query(...)):
    return {"data": pf.remove_closed(index)}


@app.post("/api/portfolio/refresh")
def portfolio_refresh():
    """手动刷新：立即重拉行情算盈亏。"""
    try:
        return {"data": pf.get_portfolio()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"刷新失败：{e}") from e


_JOB_URL_MAP = {
    "daily-digest": "daily_digest",
    "portfolio-refresh": "portfolio_refresh",
    "radar-cache-warm": "radar_cache_warm",
}


def _digest_to_dict(d: digest_mod.DailyDigest) -> dict:
    from dataclasses import asdict

    return asdict(d)


@app.get("/api/review/latest")
def review_latest(date: str | None = Query(None, description="YYYY-MM-DD，默认今天（上海）")):
    """返回定时 AI 复盘笔记（review-{date}）。"""
    d = date or digest_mod.today_shanghai()
    note = notes_mod.get_scheduled_review(d)
    if not note:
        raise HTTPException(404, "暂无定时复盘")
    return note


@app.get("/api/review/{date}")
def review_by_date(date: str):
    note = notes_mod.get_scheduled_review(date)
    if not note:
        raise HTTPException(404, "暂无定时复盘")
    return note


@app.get("/api/digest/latest")
def digest_latest():
    d = digest_mod.load_latest()
    if not d:
        raise HTTPException(404, "暂无摘要")
    return _digest_to_dict(d)


@app.get("/api/digest/{date}")
def digest_by_date(date: str):
    d = digest_mod.load(date)
    if not d:
        raise HTTPException(404, "暂无摘要")
    return _digest_to_dict(d)


class NotifyTestBody(BaseModel):
    provider: str | None = None


class NotifyConfigBody(BaseModel):
    enabled: bool | None = None
    dashboard_url: str | None = None
    channels: list[dict] | None = None


def _require_mutating_auth(request: Request) -> None:
    """PUT/POST notify：若配置了 VR_API_KEY 则必须匹配（与全局中间件一致，双保险）。"""
    if _API_KEY and request.headers.get("authorization", "") != f"Bearer {_API_KEY}":
        raise HTTPException(401, "未授权：缺少或错误的 API Key（VR_API_KEY）")


@app.get("/api/notify/providers")
def notify_providers():
    from notify.registry import ProviderRegistry
    import notify.providers  # noqa: F401

    return {"providers": ProviderRegistry.list_providers()}


@app.get("/api/notify/status")
def notify_status():
    from notify.service import status_payload

    return status_payload()


@app.post("/api/notify/test")
def notify_test(request: Request, body: NotifyTestBody | None = None):
    _require_mutating_auth(request)
    from notify.service import NotifyService
    from notify.registry import ProviderRegistry
    import notify.providers  # noqa: F401

    provider = body.provider if body else None
    if provider and ProviderRegistry.get(provider) is None:
        raise HTTPException(400, f"未知 provider：{provider}")
    svc = NotifyService()
    cfg = svc._loader()
    if not cfg.get("enabled") and not provider:
        raise HTTPException(503, "推送总开关未开启")
    results = svc.send_test(provider)
    return {
        "results": [
            {
                "provider_id": r.provider_id,
                "ok": r.ok,
                "error": r.error,
                "latency_ms": r.latency_ms,
                "skipped": r.skipped,
            }
            for r in results
        ]
    }


@app.put("/api/notify/config")
def notify_config_put(request: Request, body: NotifyConfigBody):
    _require_mutating_auth(request)
    from notify import config as notify_cfg
    from notify.registry import ProviderRegistry
    from notify.service import status_payload
    import notify.providers  # noqa: F401

    raw = body.model_dump(exclude_none=True)
    current = notify_cfg.load_config()
    merged = notify_cfg.merge_put_body(current, raw)

    errs: dict[str, list[str]] = {}
    dash_errs = notify_cfg.validate_dashboard_url(merged.get("dashboard_url") or "")
    if dash_errs:
        errs["dashboard_url"] = dash_errs
    for ch in merged.get("channels") or []:
        pid = ch.get("provider")
        if not pid:
            continue
        prov = ProviderRegistry.get(pid)
        if not prov:
            errs[pid] = ["未知 provider"]
            continue
        if ch.get("enabled") and ch.get("webhook_url"):
            ve = prov.validate_config(ch)
            if ve:
                errs[pid] = ve
        elif ch.get("enabled") and not ch.get("webhook_url"):
            errs[pid] = ["缺少 webhook_url"]
    if errs:
        raise HTTPException(400, {"detail": "配置校验失败", "errors": errs})

    notify_cfg.save_config(merged)
    return status_payload()


@app.get("/api/jobs/status")
def jobs_status():
    enabled = os.getenv("VR_SCHEDULER_ENABLED", "true").lower() == "true"
    tz = os.getenv("VR_DIGEST_TIMEZONE", "Asia/Shanghai")
    jobs = _scheduler.get_status() if _scheduler else []
    return {"scheduler_enabled": enabled, "timezone": tz, "jobs": jobs}


class JobRunBody(BaseModel):
    date: str | None = None


@app.post("/api/jobs/{name}/run")
def jobs_run(name: str, body: JobRunBody | None = None):
    internal = _JOB_URL_MAP.get(name)
    if not internal:
        raise HTTPException(404, f"未知 job：{name}")
    if _scheduler and _scheduler.is_job_running(internal):
        raise HTTPException(409, f"job {name} 正在运行")
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(os.getenv("VR_DIGEST_TIMEZONE", "Asia/Shanghai"))
    started = datetime.now(tz)
    try:
        if internal == "daily_digest":
            from jobs import daily_digest as daily_digest_job

            d = daily_digest_job.run(body.date if body else None)
            path = digest_mod.DIGESTS_DIR / f"{d.date}.json"
            result = {"date": d.date, "digest_path": str(path), "note_id": f"digest-{d.date}"}
        elif internal == "portfolio_refresh":
            from jobs import portfolio_refresh as portfolio_refresh_job

            portfolio_refresh_job.run()
            result = {"job": internal}
        elif internal == "radar_cache_warm":
            from jobs import radar_cache_warm as radar_cache_warm_job

            radar_cache_warm_job.run()
            result = {"job": internal}
        else:
            raise HTTPException(404, f"未知 job：{name}")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"job 执行失败：{e}") from e
    finished = datetime.now(tz)
    duration_ms = int((finished - started).total_seconds() * 1000)
    return {
        "job": name,
        "status": "success",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_ms": duration_ms,
        "result": result,
    }


@app.get("/api/radar")
def radar():
    """资讯雷达：12 赛道公开 RSS 资讯（读缓存，无缓存返回赛道骨架）。"""
    try:
        return {"data": newsradar.get_radar(force=False)}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"资讯雷达异常：{e}") from e


@app.post("/api/radar/refresh")
def radar_refresh():
    """强制重抓全部 RSS 源（耗时约 20-40s），更新缓存。"""
    try:
        return {"data": newsradar.fetch_radar()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"资讯雷达刷新失败：{e}") from e


@app.get("/api/market/overview")
def market_overview():
    """市场情绪 + 板块资金流（板块/大盘级，全站共享缓存 5 分钟）。"""
    try:
        return {"data": market.get_overview()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"市场总览异常：{e}") from e


@app.get("/api/market/emotion")
def market_emotion():
    """短线情绪：连板梯队 / 最高连板 / 炸板率 / 封板率 / 晋级率 / 涨跌停家数。

    含连板梯队个股清单（code/name/连板数等）——2026-07-05 起如实展示客观公开榜单（东财同款），
    只呈现事实，不附推荐/评分/预测/买卖时机。全站共享缓存 5 分钟。
    """
    try:
        return {"data": market.get_short_term_emotion()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"短线情绪异常：{e}") from e


@app.get("/api/market/turnover-top")
def market_turnover_top():
    """全市场成交额榜 Top20（客观公开榜单数据，非推荐/非预测/不评分）。全站共享缓存 5 分钟。"""
    try:
        return {"data": market.get_turnover_top()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"成交额榜异常：{e}") from e


@app.get("/api/global/indices")
def global_indices():
    """全球指数快照（道指 / 标普500 / 纳斯达克 / 恒生 / 恒生科技）—— A 股看隔夜外围脸色。缓存 5 分钟。"""
    try:
        return {"data": market.get_global_indices()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"全球指数异常：{e}") from e


@app.get("/api/global/stock")
def global_stock(symbol: str = Query(..., min_length=1, max_length=16)):
    """美股 / 港股个股聚合：行情 + 关键财务指标（东财域内源）。symbol 如 AAPL / BABA / 00700。"""
    try:
        data = gstock.us_hk_stock(symbol.strip())
        if not data:
            raise HTTPException(404, f"未找到美股/港股代码「{symbol}」")
        return {"data": data}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"美港股查询异常：{e}") from e


@app.get("/api/indices")
def indices():
    """A股大盘指数实时行情（上证/深证成指/创业板指/沪深300）。仅标准库。"""
    try:
        return {"data": astock.index_quote()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"指数行情异常：{e}") from e


@app.get("/api/quote")
def quote(codes: str = Query(..., description="逗号分隔的 6 位代码")):
    """实时行情：现价/涨跌/PE/PB/市值/换手/涨跌停。腾讯主源，失败降级 stale 缓存。"""
    lst = [c.strip() for c in codes.split(",") if c.strip()]
    if not lst or any(not c.isdigit() or len(c) != 6 for c in lst):
        raise HTTPException(400, "codes 必须是逗号分隔的 6 位数字")
    try:
        result = astock.fetch_quote(lst)
        return {"data": result.data, "_meta": _meta_from(result)}
    except AllSourcesFailed as e:
        raise _sources_failed(e, "行情") from e


import time as _time
_PCT_CACHE: dict = {}


@app.get("/api/valuation/percentile")
def valuation_percentile(code: str = Query(...)):
    """PE-TTM / PB 历史分位（近5年）。全站缓存 30 分钟/代码（历史序列日频、变化慢）。"""
    code = _validate(code)
    hit = _PCT_CACHE.get(code)
    if hit and _time.time() - hit[0] < 1800:
        return {"data": hit[1]}
    try:
        data = astock.valuation_percentile(code)
        _PCT_CACHE[code] = (_time.time(), data)
        return {"data": data}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"估值分位异常：{e}") from e


_ANN_CACHE: dict = {}


@app.get("/api/announcements")
def announcements(code: str = Query(...)):
    """个股近期公告（东财，仅 requests）。缓存 15 分钟/代码。"""
    code = _validate(code)
    hit = _ANN_CACHE.get(code)
    if hit and _time.time() - hit[0] < 900:
        return {"data": hit[1]}
    try:
        data = astock.announcements(code)
        _ANN_CACHE[code] = (_time.time(), data)
        return {"data": data}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"公告源异常：{e}") from e


_FIN_CACHE: dict = {}


@app.get("/api/financials")
def financials(code: str = Query(...)):
    """财务关键指标（同花顺财务摘要，最新报告期）。缓存 30 分钟/代码。"""
    code = _validate(code)
    hit = _FIN_CACHE.get(code)
    if hit and _time.time() - hit[0] < 1800:
        return {"data": hit[1]}
    try:
        data = astock.financials(code)
        _FIN_CACHE[code] = (_time.time(), data)
        return {"data": data}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"财务摘要异常：{e}") from e


@app.get("/api/valuation")
def valuation(code: str = Query(...)):
    """完整估值：行情 + 一致预期 + 前向PE/PEG/消化年数。"""
    code = _validate(code)
    try:
        return {"data": astock.full_valuation(code)}
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"估值计算异常：{e}") from e


@app.get("/api/reports")
def reports(code: str = Query(...), pages: int = Query(2, ge=1, le=5)):
    """个股研报列表（东财，含 PDF 链接）。仅需 requests。"""
    code = _validate(code)
    try:
        rows = astock.eastmoney_reports(code, max_pages=pages)
        for r in rows:
            r["pdfUrl"] = astock.pdf_url(r.get("infoCode", "")) if r.get("infoCode") else None
        return {"data": rows}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"研报源异常：{e}") from e


@app.get("/api/news")
def news(code: str = Query(...), limit: int = Query(20, ge=1, le=50)):
    """个股新闻（东财，需 akshare）。"""
    code = _validate(code)
    try:
        result = astock.fetch_news(code, limit=limit)
        return {"data": result.data, "_meta": _meta_from(result)}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except AllSourcesFailed as e:
        raise _sources_failed(e, "新闻") from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"新闻源异常：{e}") from e


@app.get("/api/info")
def info(code: str = Query(...)):
    """个股基本面：行业/股本/上市时间（需 akshare）。"""
    code = _validate(code)
    try:
        return {"data": astock.individual_info(code)}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"基本面源异常：{e}") from e


@app.get("/api/disclosure")
def disclosure(code: str = Query(...)):
    """巨潮公告列表（需 akshare）。"""
    code = _validate(code)
    try:
        return {"data": astock.disclosure(code)}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"公告源异常：{e}") from e


@app.get("/api/kline")
def kline(code: str = Query(...), category: int = Query(4), offset: int = Query(60, ge=1, le=800)):
    """K线（需 mootdx）。category 4=日 5=周 6=月 11=60分钟。"""
    code = _validate(code)
    try:
        result = astock.fetch_kline(code, category=category, offset=offset)
        return {"data": result.data, "_meta": _meta_from(result)}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except AllSourcesFailed as e:
        raise _sources_failed(e, "K线") from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"K线源异常：{e}") from e


@app.get("/api/finance")
def finance(code: str = Query(...)):
    """季报财务快照（需 mootdx）。"""
    code = _validate(code)
    try:
        return {"data": astock.finance(code)}
    except astock.DependencyMissing as e:
        raise HTTPException(501, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"财务源异常：{e}") from e


# ---------------------------------------------------------------------------
# 资金面 / 筹码 / 信号（东财数据中心，v3.3 并入）—— 均为「用户查的那只股」的公开数据。
# 东财有 1s 限流，这些多为日/季级静态数据，统一走 30 分钟缓存，进一步降低被封风险。
# ---------------------------------------------------------------------------

_DC_CACHE: dict = {}  # key=(endpoint, code) -> (ts, data)


@dataclass(frozen=True)
class _CachedResult:
    data: object
    stale: bool = False


def _cached(key: tuple, ttl: int, fetch) -> _CachedResult:
    hit = _DC_CACHE.get(key)
    if hit and _time.time() - hit[0] < ttl:
        return _CachedResult(data=hit[1], stale=False)
    try:
        data = fetch()
        registry.mark_ok("eastmoney")
        _DC_CACHE[key] = (_time.time(), data)
        return _CachedResult(data=data, stale=False)
    except Exception as e:  # noqa: BLE001
        registry.mark_fail("eastmoney", str(e))
        if hit:
            return _CachedResult(data=hit[1], stale=True)
        raise


def _eastmoney_response(key: tuple, ttl: int, fetch, err_label: str) -> dict:
    try:
        result = _cached(key, ttl, fetch)
        body: dict = {"data": result.data}
        if result.stale:
            body["_meta"] = {"source": "eastmoney", "stale": True, "chain": "eastmoney"}
        return body
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"{err_label}异常：{e}") from e


@app.get("/api/margin")
def margin(code: str = Query(...)):
    """融资融券明细（东财，日级）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("margin", code), 1800, lambda: astock.margin_trading(code), "融资融券")


@app.get("/api/block-trade")
def block_trade(code: str = Query(...)):
    """大宗交易（东财）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("block", code), 1800, lambda: astock.block_trade(code), "大宗交易")


@app.get("/api/holders")
def holders(code: str = Query(...)):
    """股东户数变化（东财，季度级）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("holders", code), 1800, lambda: astock.holder_num_change(code), "股东户数")


@app.get("/api/dividend")
def dividend(code: str = Query(...)):
    """分红送转历史（东财）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("dividend", code), 1800, lambda: astock.dividend_history(code), "分红送转")


@app.get("/api/fund-flow")
def fund_flow(code: str = Query(...)):
    """个股资金流（东财 push2his，120 日主力净流入）。缓存 15 分钟。
    注：push2his 对部分大陆住宅 IP 有间歇风控，可能返回空（非代码问题）。"""
    code = _validate(code)
    return _eastmoney_response(("fundflow", code), 900, lambda: astock.stock_fund_flow_120d(code), "资金流")


@app.get("/api/dragon-tiger")
def dragon_tiger(code: str = Query(...)):
    """龙虎榜：该股近期上榜记录 + 买卖席位 + 机构净买（东财）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("dt", code), 1800, lambda: astock.dragon_tiger_board(code), "龙虎榜")


@app.get("/api/lockup")
def lockup(code: str = Query(...)):
    """限售解禁日历：历史解禁 + 未来 90 天待解禁（东财）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("lockup", code), 1800, lambda: astock.lockup_expiry(code), "解禁日历")


@app.get("/api/blocks")
def blocks(code: str = Query(...)):
    """个股所属板块/概念归属（东财 slist）。缓存 30 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("blocks", code), 1800, lambda: astock.concept_blocks(code), "板块归属")


@app.get("/api/hot-concepts")
def hot_concepts(code: str = Query(...)):
    """个股当下被市场归到哪些概念在炒（东财热门概念命中）。缓存 15 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("hotcon", code), 900, lambda: astock.hot_concepts(code), "热门概念")


@app.get("/api/investor-qa")
def investor_qa(code: str = Query(...)):
    """互动易问答（巨潮）：投资者提问 + 公司回复。缓存 15 分钟。"""
    code = _validate(code)
    return _eastmoney_response(("irm", code), 900, lambda: astock.investor_qa(code), "互动易")


@app.get("/api/industry")
def industry(top: int = Query(20, ge=5, le=50)):
    """全行业涨跌幅排名（东财行业板块，板块级、零个股名单）。缓存 5 分钟。"""
    return _eastmoney_response(("industry", str(top)), 300, lambda: astock.industry_comparison(top_n=top), "行业排名")


# 生产模式：Docker 或 npm run build 后，同端口托管前端 dist（开发仍走 Vite :5899 代理）。
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """SPA fallback：无真实静态文件时回退 index.html，供 React Router 处理深链刷新。"""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            # 带扩展名的路径（.js/.css/.svg）是真缺失，保持 404
            if path and "." in path.rsplit("/", 1)[-1]:
                raise
            return await super().get_response("index.html", scope)


if _DIST.is_dir():
    app.mount("/", SPAStaticFiles(directory=_DIST, html=True), name="static")
