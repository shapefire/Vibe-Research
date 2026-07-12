"""Snapshot diff 算法 —— 递归对比两条笔记的客观数据快照，返回 delta 树。

纯函数模块，无副作用；不含主观评级文案。
"""

from __future__ import annotations

SKIP_KEYS = frozenset({"captured_at", "code"})


def diff_snapshots(
    a: dict | None,
    b: dict | None,
    *,
    max_depth: int = 10,
    _depth: int = 0,
) -> dict:
    """递归对比两个 snapshot，返回 delta 树。"""
    if a is None:
        a = {}
    if b is None:
        b = {}

    if _depth > max_depth:
        return {"before": a, "after": b, "type": "truncated"}

    result: dict = {}
    all_keys = set(a.keys()) | set(b.keys())

    for key in all_keys:
        if _depth == 0 and key in SKIP_KEYS:
            continue

        va, vb = a.get(key), b.get(key)

        if key not in a:
            result[key] = {"missing_in": "a", "after": vb}
        elif key not in b:
            result[key] = {"missing_in": "b", "before": va}
        elif isinstance(va, dict) and isinstance(vb, dict):
            result[key] = diff_snapshots(va, vb, max_depth=max_depth, _depth=_depth + 1)
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            delta = vb - va
            delta_pct = round(delta / va * 100, 2) if va != 0 else None
            result[key] = {
                "before": va,
                "after": vb,
                "delta": delta,
                "delta_pct": delta_pct,
                "type": "numeric",
            }
        else:
            result[key] = {"before": va, "after": vb, "type": "scalar"}

    return result


def flatten_diff(tree: dict, prefix: str = "") -> dict[str, dict]:
    """将嵌套 diff 树扁平化为 dot-path 键。"""
    flat: dict[str, dict] = {}
    for k, v in tree.items():
        path = f"{prefix}.{k}" if prefix else k
        if not isinstance(v, dict):
            continue
        if "before" in v or "missing_in" in v or v.get("type") in ("numeric", "scalar", "truncated"):
            flat[path] = v
        else:
            flat.update(flatten_diff(v, path))
    return flat


def swap_before_after(flat: dict[str, dict]) -> dict[str, dict]:
    """交换 before/after 并翻转 delta，用于保证 note_a 为较早条目。"""
    swapped: dict[str, dict] = {}
    for path, entry in flat.items():
        new_entry = dict(entry)
        if "before" in new_entry and "after" in new_entry:
            new_entry["before"], new_entry["after"] = new_entry["after"], new_entry["before"]
        if "delta" in new_entry and isinstance(new_entry["delta"], (int, float)):
            new_entry["delta"] = -new_entry["delta"]
            if new_entry.get("delta_pct") is not None:
                new_entry["delta_pct"] = -new_entry["delta_pct"]
        if new_entry.get("missing_in") == "a":
            new_entry["missing_in"] = "b"
            new_entry.pop("before", None)
            if "after" in new_entry:
                new_entry["before"] = new_entry.pop("after")
        elif new_entry.get("missing_in") == "b":
            new_entry["missing_in"] = "a"
            new_entry.pop("after", None)
            if "before" in new_entry:
                new_entry["after"] = new_entry.pop("before")
        swapped[path] = new_entry
    return swapped
