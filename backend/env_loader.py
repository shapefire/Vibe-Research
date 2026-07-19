"""加载 backend/.env 到 os.environ（不覆盖已存在的系统环境变量）。"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_LOADED = False


def load_env_file(path: Path | None = None) -> bool:
    """解析 .env 键值对；返回是否成功读取文件。"""
    global _ENV_LOADED
    env_path = path or (Path(__file__).resolve().parent / ".env")
    if not env_path.is_file():
        return False
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        inline_comment = _strip_inline_comment(val)
        os.environ.setdefault(key, inline_comment)
    _ENV_LOADED = True
    return True


def _strip_inline_comment(val: str) -> str:
    """保留引号内 #；无引号时截断行内注释。"""
    if not val or val[0] in ("'", '"'):
        return val
    for i, ch in enumerate(val):
        if ch == "#" and (i == 0 or val[i - 1].isspace()):
            return val[:i].rstrip()
    return val
