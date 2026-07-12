#!/usr/bin/env python3
"""确保 docs/feats/*.md 均含「合规」章节关键词。

排除 README.md、99-backlog.md。
运行：python scripts/check_compliance_docs.py（仓库根目录）
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATS_DIR = REPO_ROOT / "docs" / "feats"
EXCLUDED = {"README.md", "99-backlog.md"}


def main() -> int:
    if not FEATS_DIR.is_dir():
        print(f"ERROR: {FEATS_DIR} 不存在", file=sys.stderr)
        return 1

    missing: list[str] = []
    for path in sorted(FEATS_DIR.glob("*.md")):
        if path.name in EXCLUDED:
            continue
        content = path.read_text(encoding="utf-8")
        if "合规" not in content:
            missing.append(str(path.relative_to(REPO_ROOT)))

    if missing:
        print("以下 feats 文档缺少「合规」关键词：", file=sys.stderr)
        for p in missing:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"OK: 所有 feats 文档（除 {', '.join(sorted(EXCLUDED))}）均含「合规」")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
