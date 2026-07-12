"""pytest 配置：把 backend 目录加进 sys.path，注册 live 标记，隔离用户数据目录。"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# 用户数据隔离：portfolio / myreports 在 import 时按 VR_DATA_DIR / VR_REPORTS_DIR 固化路径，
# 必须赶在任何测试模块 import app 之前指到临时目录——否则持仓 CRUD 类测试会增删真实
# ~/.vibe-research/ 里的用户数据（比如把用户真实持有的 600519 合并后删掉）。
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="vr-test-data-")
os.environ["VR_DATA_DIR"] = _TEST_DATA_DIR
os.environ["VR_REPORTS_DIR"] = os.path.join(_TEST_DATA_DIR, "myreports")

# 确保 frontend/dist 存在，供 SPA fallback 测试（app import 时决定是否挂载静态文件）
_DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
os.makedirs(_DIST_DIR, exist_ok=True)
_INDEX_HTML = os.path.join(_DIST_DIR, "index.html")
if not os.path.isfile(_INDEX_HTML):
    with open(_INDEX_HTML, "w", encoding="utf-8") as f:
        f.write("<!doctype html><html><body><div id=\"root\"></div></body></html>")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: 打真实数据源的网络冒烟测（会联网、可能受上游/限流影响；默认可 -m 'not live' 跳过）",
    )


@pytest.fixture(autouse=True)
def isolated_notes_dir(tmp_path, monkeypatch):
    """隔离 notes 目录，供 notes / compare API 测试复用。"""
    import notes as notes_mod

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(notes_mod, "NOTES_DIR", str(notes_dir))
    monkeypatch.setattr(notes_mod, "INDEX_FILE", str(notes_dir / "index.json"))
    monkeypatch.setattr(notes_mod, "LEGACY_BACKUP", str(notes_dir / "notes_legacy_localStorage.json"))
    monkeypatch.setenv("VR_NOTES_MAX", "5")
    monkeypatch.setenv("VR_NOTES_MAX_CONTENT_BYTES", "102400")
