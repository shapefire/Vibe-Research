"""env_loader 测试。"""
from __future__ import annotations

import os

from env_loader import load_env_file


def test_load_env_file_setdefault(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "VR_DIGEST_TIME=22:30\n# comment\nVR_JOBS=a,b\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("VR_DIGEST_TIME", raising=False)
    monkeypatch.delenv("VR_JOBS", raising=False)
    assert load_env_file(env) is True
    assert os.environ["VR_DIGEST_TIME"] == "22:30"
    assert os.environ["VR_JOBS"] == "a,b"


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("VR_DIGEST_TIME=22:30\n", encoding="utf-8")
    monkeypatch.setenv("VR_DIGEST_TIME", "18:00")
    load_env_file(env)
    assert os.environ["VR_DIGEST_TIME"] == "18:00"
