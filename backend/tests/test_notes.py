"""研究记录数据层与 API 测试。"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

import app as app_module
import notes

client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def isolated_notes_dir(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(notes, "NOTES_DIR", str(notes_dir))
    monkeypatch.setattr(notes, "INDEX_FILE", str(notes_dir / "index.json"))
    monkeypatch.setattr(notes, "LEGACY_BACKUP", str(notes_dir / "notes_legacy_localStorage.json"))
    monkeypatch.setenv("VR_NOTES_MAX", "5")
    monkeypatch.setenv("VR_NOTES_MAX_CONTENT_BYTES", "102400")


def _add(kind="复盘", title="测试", content="# 内容", **kwargs):
    return notes.add_note(kind=kind, title=title, content=content, **kwargs)


# ---- 数据层 ----

def test_add_note_creates_index_and_md():
    meta = _add(title="每日复盘")
    assert meta["id"]
    assert os.path.exists(notes.INDEX_FILE)
    assert os.path.exists(os.path.join(notes.NOTES_DIR, f"{meta['id']}.md"))
    full = notes.get_note(meta["id"])
    assert full["content"] == "# 内容"


def test_list_notes_sorted_by_ts_desc():
    _add(title="旧", ts=1000)
    _add(title="新", ts=2000)
    result = notes.list_notes()
    assert result["total"] == 2
    assert result["items"][0]["title"] == "新"


def test_list_notes_filter_kind():
    _add(kind="问AI", title="AI")
    _add(kind="复盘", title="复盘")
    result = notes.list_notes(kind="问AI")
    assert result["total"] == 1
    assert result["items"][0]["kind"] == "问AI"


def test_list_notes_filter_q():
    _add(title="600519 茅台")
    _add(title="其他")
    result = notes.list_notes(q="600519")
    assert result["total"] == 1


def test_get_note_with_snapshot():
    snap = {"code": "600519", "quote": {"price": 1680.0}}
    meta = _add(kind="问AI", snapshot=snap, tags=["600519"])
    full = notes.get_note(meta["id"])
    assert full["snapshot"] == snap
    assert full["tags"] == ["600519"]


def test_get_note_not_found():
    with pytest.raises(notes.NoteError, match="不存在"):
        notes.get_note("9999999999999-nope1")


def test_delete_note_removes_index_and_md():
    meta = _add()
    assert notes.delete_note(meta["id"]) is True
    assert notes.list_notes()["total"] == 0
    assert not os.path.exists(os.path.join(notes.NOTES_DIR, f"{meta['id']}.md"))


def test_migrate_notes_imports_new():
    payload = [{
        "id": "1719000000000-test1",
        "kind": "复盘",
        "title": "迁移测试",
        "content": "## 测试",
        "ts": 1719000000000,
    }]
    result = notes.migrate_notes(payload)
    assert result["imported"] == 1
    assert result["skipped"] == 0
    assert notes.list_notes()["total"] == 1
    assert os.path.exists(notes.LEGACY_BACKUP)


def test_migrate_notes_skips_duplicate_id():
    _add(note_id="1719000000000-dup01", title="已有", ts=1719000000000)
    payload = [{
        "id": "1719000000000-dup01",
        "kind": "复盘",
        "title": "重复",
        "content": "x",
        "ts": 1719000000000,
    }]
    result = notes.migrate_notes(payload)
    assert result["imported"] == 0
    assert result["skipped"] == 1


def test_capacity_exceeded():
    for i in range(5):
        _add(title=f"笔记{i}")
    with pytest.raises(notes.CapacityExceeded):
        _add(title="超限")


def test_content_too_large():
    big = "x" * (102401)
    with pytest.raises(notes.NoteError, match="content"):
        _add(content=big)


def test_invalid_id_rejected():
    with pytest.raises(notes.NoteError):
        notes.get_note("../etc")
    with pytest.raises(notes.NoteError):
        _add(note_id="bad/id")


def test_empty_index_initial():
    result = notes.list_notes()
    assert result == {"items": [], "total": 0}


def test_delete_all_notes():
    _add(title="a")
    _add(title="b")
    result = notes.delete_all_notes()
    assert result["ok"] is True
    assert result["count"] == 2
    assert notes.list_notes()["total"] == 0


def test_atomic_index_on_corrupt(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes2"
    notes_dir.mkdir()
    index = notes_dir / "index.json"
    index.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(notes, "NOTES_DIR", str(notes_dir))
    monkeypatch.setattr(notes, "INDEX_FILE", str(index))
    result = notes.list_notes()
    assert result["total"] == 0


# ---- 路由 ----

def test_route_list_notes():
    r = client.get("/api/notes")
    assert r.status_code == 200
    assert "items" in r.json()["data"]


def test_route_create_missing_kind():
    r = client.post("/api/notes", json={"kind": "", "title": "t", "content": "c"})
    assert r.status_code == 400


def test_route_migrate():
    r = client.post("/api/notes/migrate", json={"notes": [{
        "id": "1719000000000-api01",
        "kind": "复盘",
        "title": "API迁移",
        "content": "body",
        "ts": 1719000000000,
    }]})
    assert r.status_code == 200
    assert r.json()["data"]["imported"] == 1


def test_route_delete_not_found():
    r = client.delete("/api/notes/nonexist-id99")
    assert r.status_code == 404


def test_route_capacity_409():
    for i in range(5):
        client.post("/api/notes", json={"kind": "复盘", "title": f"n{i}", "content": "c"})
    r = client.post("/api/notes", json={"kind": "复盘", "title": "满", "content": "c"})
    assert r.status_code == 409


def test_route_delete_all():
    client.post("/api/notes", json={"kind": "复盘", "title": "x", "content": "c"})
    r = client.delete("/api/notes")
    assert r.status_code == 200
    assert r.json()["data"]["count"] >= 1
