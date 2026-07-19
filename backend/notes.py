"""研究记录数据层 —— 用户主动保存的 AI 复盘/要点/问答。

存储：~/.vibe-research/notes/（index.json + {id}.md）
合规：只存用户主动保存内容；snapshot 仅客观数据字段，不含 AI 买卖结论。
"""

from __future__ import annotations

import json
import os
import random
import re
import string
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

CACHE_DIR = os.environ.get("VR_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".vibe-research")
NOTES_DIR = os.path.join(CACHE_DIR, "notes")
INDEX_FILE = os.path.join(NOTES_DIR, "index.json")
LEGACY_BACKUP = os.path.join(NOTES_DIR, "notes_legacy_localStorage.json")
BEIJING = timezone(timedelta(hours=8))
_LOCK = threading.Lock()

CURRENT_VERSION = 1
DEFAULT_MAX = 500
DEFAULT_MAX_CONTENT = 102400
MAX_TITLE_LEN = 200
MAX_TAGS = 10
MAX_TAG_LEN = 32
MAX_MIGRATE_BATCH = 200

_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class NoteError(ValueError):
    """笔记校验/读写错误（对应 HTTP 400）。"""


class CapacityExceeded(NoteError):
    """笔记数量达上限（对应 HTTP 409）。"""


@dataclass
class NoteMeta:
    id: str
    kind: str
    title: str
    ts: int
    tags: list[str] = field(default_factory=list)
    snapshot: dict | None = None


def _max_notes() -> int:
    try:
        return max(1, int(os.environ.get("VR_NOTES_MAX", str(DEFAULT_MAX))))
    except ValueError:
        return DEFAULT_MAX


def _max_content_bytes() -> int:
    try:
        return max(1, int(os.environ.get("VR_NOTES_MAX_CONTENT_BYTES", str(DEFAULT_MAX_CONTENT))))
    except ValueError:
        return DEFAULT_MAX_CONTENT


def _now_iso() -> str:
    return datetime.now(BEIJING).isoformat(timespec="seconds")


def _ensure_dir() -> None:
    os.makedirs(NOTES_DIR, exist_ok=True)


def _empty_index() -> dict:
    return {"version": CURRENT_VERSION, "updated_at": _now_iso(), "items": []}


def _load_index() -> dict:
    if not os.path.exists(INDEX_FILE):
        return _empty_index()
    try:
        with open(INDEX_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_index()
        items = data.get("items")
        if not isinstance(items, list):
            data["items"] = []
        data.setdefault("version", CURRENT_VERSION)
        data.setdefault("updated_at", _now_iso())
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[vibe-research] notes index 损坏，重置为空: {e}", file=sys.stderr)
        return _empty_index()


def _save_index(data: dict) -> None:
    _ensure_dir()
    data["version"] = CURRENT_VERSION
    data["updated_at"] = _now_iso()
    tmp = INDEX_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, INDEX_FILE)


def _content_path(note_id: str) -> str:
    return os.path.join(NOTES_DIR, f"{note_id}.md")


def _validate_id(note_id: str) -> str:
    nid = (note_id or "").strip()
    if not nid or ".." in nid or "/" in nid or "\\" in nid:
        raise NoteError("非法笔记 ID")
    if not _ID_RE.match(nid):
        raise NoteError("非法笔记 ID")
    return nid


def _validate_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    out: list[str] = []
    for t in tags[:MAX_TAGS]:
        s = (t or "").strip()
        if not s:
            continue
        if len(s) > MAX_TAG_LEN:
            raise NoteError(f"标签长度不能超过 {MAX_TAG_LEN} 字符")
        out.append(s)
    return out


def _validate_fields(kind: str, title: str, content: str) -> None:
    if not (kind or "").strip():
        raise NoteError("kind 不能为空")
    if not (title or "").strip():
        raise NoteError("title 不能为空")
    if len(title.strip()) > MAX_TITLE_LEN:
        raise NoteError(f"title 不能超过 {MAX_TITLE_LEN} 字符")
    if not (content or "").strip():
        raise NoteError("content 不能为空")
    if len(content.encode("utf-8")) > _max_content_bytes():
        raise NoteError(f"content 不能超过 {_max_content_bytes() // 1024}KB")


def _generate_id(ts: int | None = None) -> str:
    ms = ts if ts is not None else int(time.time() * 1000)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{ms}-{suffix}"


def _save_content(note_id: str, content: str) -> None:
    _ensure_dir()
    path = _content_path(note_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def _delete_content(note_id: str) -> None:
    path = _content_path(note_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _read_content(note_id: str) -> str:
    path = _content_path(note_id)
    if not os.path.exists(path):
        raise NoteError("笔记正文不存在")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _meta_to_dict(meta: NoteMeta) -> dict:
    d = asdict(meta)
    if d.get("snapshot") is None:
        d["snapshot"] = None
    return d


def _enforce_capacity(items: list[dict], adding: int = 1) -> None:
    if len(items) + adding > _max_notes():
        raise CapacityExceeded(f"已达笔记上限 {_max_notes()} 条，请删除旧记录后再保存")


def list_notes(
    kind: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """返回元数据列表（不含 content），按 ts 降序。"""
    data = _load_index()
    items = list(data.get("items", []))
    if kind:
        items = [i for i in items if i.get("kind") == kind]
    if q:
        low = q.lower()
        items = [i for i in items if low in (i.get("title") or "").lower()]
    items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    total = len(items)
    page = items[offset : offset + limit]
    return {"items": page, "total": total}


def get_note(note_id: str) -> dict:
    """返回完整笔记（含 content）。"""
    nid = _validate_id(note_id)
    data = _load_index()
    hit = next((i for i in data.get("items", []) if i.get("id") == nid), None)
    if not hit:
        raise NoteError("笔记不存在")
    content = _read_content(nid)
    return {**hit, "content": content}


def get_meta(note_id: str) -> dict | None:
    """仅 index.json 元数据；不存在返回 None。"""
    try:
        nid = _validate_id(note_id)
    except NoteError:
        return None
    data = _load_index()
    return next((i for i in data.get("items", []) if i.get("id") == nid), None)


def _has_snapshot(item: dict) -> bool:
    snap = item.get("snapshot")
    return isinstance(snap, dict) and bool(snap)


def _note_matches_tag(item: dict, tag: str) -> bool:
    """匹配 tags 或 snapshot.code（兼容旧笔记未写 tags 的情况）。"""
    if tag in (item.get("tags") or []):
        return True
    snap = item.get("snapshot")
    if isinstance(snap, dict) and snap.get("code") == tag:
        return True
    return False


def list_by_tag(tag: str, *, has_snapshot: bool = False, limit: int = 50) -> dict:
    """按 tag 筛选笔记，按 ts 降序。"""
    data = _load_index()
    items = [i for i in data.get("items", []) if _note_matches_tag(i, tag)]
    if has_snapshot:
        items = [i for i in items if _has_snapshot(i)]
    items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    total = len(items)
    page = items[:limit]
    out = []
    for i in page:
        row = {k: v for k, v in i.items() if k != "snapshot"}
        row["has_snapshot"] = _has_snapshot(i)
        out.append(row)
    return {"items": out, "total": total, "tag": tag}


def add_note(
    kind: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
    snapshot: dict | None = None,
    note_id: str | None = None,
    ts: int | None = None,
) -> dict:
    """新建笔记，返回元数据（不含 content）。"""
    _validate_fields(kind, title, content)
    safe_tags = _validate_tags(tags)
    ts_val = ts if ts is not None else int(time.time() * 1000)
    nid = _validate_id(note_id) if note_id else _generate_id(ts_val)

    with _LOCK:
        data = _load_index()
        items = data.setdefault("items", [])
        if any(i.get("id") == nid for i in items):
            raise NoteError("笔记 ID 已存在")
        _enforce_capacity(items)
        meta = NoteMeta(
            id=nid,
            kind=kind.strip(),
            title=title.strip(),
            ts=ts_val,
            tags=safe_tags,
            snapshot=snapshot,
        )
        _save_content(nid, content)
        items.insert(0, _meta_to_dict(meta))
        _save_index(data)
    return _meta_to_dict(meta)


def delete_note(note_id: str) -> bool:
    """删除单条笔记。"""
    nid = _validate_id(note_id)
    with _LOCK:
        data = _load_index()
        items = data.get("items", [])
        new_items = [i for i in items if i.get("id") != nid]
        if len(new_items) == len(items):
            return False
        data["items"] = new_items
        _save_index(data)
        _delete_content(nid)
    return True


def delete_all_notes() -> dict:
    """清空所有笔记。"""
    with _LOCK:
        data = _load_index()
        count = len(data.get("items", []))
        for item in data.get("items", []):
            iid = item.get("id")
            if iid:
                _delete_content(iid)
        data["items"] = []
        _save_index(data)
    return {"ok": True, "count": count}


def migrate_notes(notes: list[dict]) -> dict:
    """从 localStorage 批量导入；id 去重，保留原始 ts。"""
    if len(notes) > MAX_MIGRATE_BATCH:
        raise NoteError(f"单次迁移不能超过 {MAX_MIGRATE_BATCH} 条")

    imported = 0
    skipped = 0

    with _LOCK:
        _ensure_dir()
        try:
            tmp = LEGACY_BACKUP + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"migrated_at": _now_iso(), "notes": notes}, f, ensure_ascii=False, indent=2)
            os.replace(tmp, LEGACY_BACKUP)
        except OSError as e:
            print(f"[vibe-research] notes 迁移备份写入失败: {e}", file=sys.stderr)

        data = _load_index()
        existing_ids = {i.get("id") for i in data.get("items", [])}

        for raw in notes:
            if not isinstance(raw, dict):
                skipped += 1
                continue
            try:
                nid = _validate_id(str(raw.get("id", "")))
                kind = str(raw.get("kind", "")).strip()
                title = str(raw.get("title", "")).strip()
                content = str(raw.get("content", ""))
                ts_val = int(raw.get("ts", 0))
                if nid in existing_ids:
                    skipped += 1
                    continue
                _validate_fields(kind, title, content)
                _enforce_capacity(data.get("items", []))
                meta = NoteMeta(
                    id=nid,
                    kind=kind,
                    title=title,
                    ts=ts_val,
                    tags=_validate_tags(raw.get("tags")),
                    snapshot=raw.get("snapshot") if isinstance(raw.get("snapshot"), dict) else None,
                )
                _save_content(nid, content)
                data.setdefault("items", []).insert(0, _meta_to_dict(meta))
                existing_ids.add(nid)
                imported += 1
            except (NoteError, ValueError, TypeError):
                skipped += 1

        if imported > 0:
            _save_index(data)

    total = imported + skipped
    print(f"[vibe-research] notes migrate: imported={imported} skipped={skipped}", file=sys.stderr)
    return {"imported": imported, "skipped": skipped, "total": total}


def create_from_digest(digest_obj) -> dict:
    """将每日摘要写入 kind=摘要 笔记；同 date 幂等 upsert。"""
    if hasattr(digest_obj, "to_markdown"):
        content = digest_obj.to_markdown()
        date = digest_obj.date
        snapshot = {
            "date": digest_obj.date,
            "generated_at": digest_obj.generated_at,
            "market": digest_obj.market,
            "watchlist_summary": digest_obj.watchlist_summary,
            "portfolio_summary": digest_obj.portfolio_summary,
            "intel_summary": digest_obj.intel_summary,
        }
    elif isinstance(digest_obj, dict):
        content = str(digest_obj.get("content", ""))
        date = str(digest_obj.get("date", ""))
        snapshot = digest_obj.get("snapshot")
    else:
        raise NoteError("digest 格式无效")

    if not date:
        raise NoteError("digest 缺少 date")
    title = f"每日数据摘要 {date}"
    nid = f"digest-{date}"
    _validate_fields("摘要", title, content)

    with _LOCK:
        data = _load_index()
        items = data.setdefault("items", [])
        existing = next((i for i in items if i.get("id") == nid), None)
        ts_val = int(time.time() * 1000)
        if existing:
            existing["title"] = title
            existing["kind"] = "摘要"
            existing["tags"] = _validate_tags(["digest"])
            existing["snapshot"] = snapshot if isinstance(snapshot, dict) else None
            _save_content(nid, content)
            _save_index(data)
            return {k: v for k, v in existing.items() if k != "snapshot"}

        _enforce_capacity(items)
        meta = NoteMeta(
            id=nid,
            kind="摘要",
            title=title,
            ts=ts_val,
            tags=_validate_tags(["digest"]),
            snapshot=snapshot if isinstance(snapshot, dict) else None,
        )
        _save_content(nid, content)
        items.insert(0, _meta_to_dict(meta))
        _save_index(data)
    return _meta_to_dict(meta)


def create_from_scheduled_review(digest_obj, content: str) -> dict:
    """定时 AI 复盘写入 kind=复盘 笔记；同 date 幂等 upsert。"""
    if not hasattr(digest_obj, "date"):
        raise NoteError("digest 格式无效")
    date = digest_obj.date
    title = f"定时复盘 {date}"
    nid = f"review-{date}"
    _validate_fields("复盘", title, content)
    snapshot = {
        "date": digest_obj.date,
        "generated_at": digest_obj.generated_at,
        "market": digest_obj.market,
        "watchlist_summary": digest_obj.watchlist_summary,
        "portfolio_summary": digest_obj.portfolio_summary,
        "intel_summary": digest_obj.intel_summary,
        "source": "scheduled",
    }

    with _LOCK:
        data = _load_index()
        items = data.setdefault("items", [])
        existing = next((i for i in items if i.get("id") == nid), None)
        ts_val = int(time.time() * 1000)
        if existing:
            existing["title"] = title
            existing["kind"] = "复盘"
            existing["tags"] = _validate_tags(["scheduled", "digest"])
            existing["snapshot"] = snapshot
            _save_content(nid, content)
            _save_index(data)
            return {k: v for k, v in existing.items() if k != "snapshot"}

        _enforce_capacity(items)
        meta = NoteMeta(
            id=nid,
            kind="复盘",
            title=title,
            ts=ts_val,
            tags=_validate_tags(["scheduled", "digest"]),
            snapshot=snapshot,
        )
        _save_content(nid, content)
        items.insert(0, _meta_to_dict(meta))
        _save_index(data)
    return _meta_to_dict(meta)


def get_scheduled_review(date: str) -> dict | None:
    """读取指定日期的定时复盘笔记（review-{date}）；不存在返回 None。"""
    nid = f"review-{date}"
    try:
        _validate_id(nid)
    except NoteError:
        return None
    if get_meta(nid) is None:
        return None
    try:
        return get_note(nid)
    except NoteError:
        return None
