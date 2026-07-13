"""笔记对比 API 测试。"""

from __future__ import annotations

import notes
from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app)


def _add(**kwargs):
    defaults = {"kind": "问AI", "title": "测试", "content": "# 内容"}
    defaults.update(kwargs)
    return notes.add_note(**defaults)


def test_compare_success(isolated_notes_dir):
    snap_a = {"quote": {"price": 1700.0}, "valuation_pctile": {"pe_5y": 68}}
    snap_b = {"quote": {"price": 1680.0}, "valuation_pctile": {"pe_5y": 72}}
    a = _add(title="较早", ts=1000, tags=["600519"], snapshot=snap_a)
    b = _add(title="较晚", ts=2000, tags=["600519"], snapshot=snap_b)
    resp = client.post("/api/notes/compare", json={"id_a": b["id"], "id_b": a["id"]})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["comparable"] is True
    assert data["note_a"]["title"] == "较早"
    assert data["note_b"]["title"] == "较晚"
    assert data["diff"]["quote.price"]["before"] == 1700.0
    assert data["diff"]["quote.price"]["after"] == 1680.0


def test_compare_missing_snapshot(isolated_notes_dir):
    a = _add(title="有快照", snapshot={"quote": {"price": 100}})
    b = _add(title="无快照", snapshot=None)
    resp = client.post("/api/notes/compare", json={"id_a": a["id"], "id_b": b["id"]})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["comparable"] is False
    assert data["reason"] == "missing_snapshot"


def test_compare_same_id(isolated_notes_dir):
    a = _add(snapshot={"quote": {"price": 100}})
    resp = client.post("/api/notes/compare", json={"id_a": a["id"], "id_b": a["id"]})
    assert resp.status_code == 400


def test_compare_not_found(isolated_notes_dir):
    a = _add(snapshot={"quote": {"price": 100}})
    resp = client.post("/api/notes/compare", json={"id_a": a["id"], "id_b": "9999999999999-nope1"})
    assert resp.status_code == 404


def test_by_tag_filter(isolated_notes_dir):
    _add(tags=["600519"], title="A")
    _add(tags=["600519"], title="B")
    _add(tags=["000001"], title="C")
    resp = client.get("/api/notes/by-tag?tag=600519")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    assert data["tag"] == "600519"


def test_by_tag_has_snapshot(isolated_notes_dir):
    _add(tags=["600519"], snapshot={"quote": {"price": 100}})
    _add(tags=["600519"], snapshot=None)
    resp = client.get("/api/notes/by-tag?tag=600519&has_snapshot=true")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["has_snapshot"] is True


def test_by_tag_matches_snapshot_code_without_tags(isolated_notes_dir):
    """兼容仅 snapshot.code 有值、tags 为空的旧笔记。"""
    _add(tags=[], snapshot={"code": "600519", "quote": {"price": 1680.0}})
    resp = client.get("/api/notes/by-tag?tag=600519")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1


def test_by_tag_invalid(isolated_notes_dir):
    resp = client.get("/api/notes/by-tag?tag=abc")
    assert resp.status_code == 400
