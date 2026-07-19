from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from tools.params import CHAT_TOOL_JSON_BUDGET
from tools import trim

Handler = Callable[[dict, str], Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Handler
    surfaces: frozenset[str]


_REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    if not spec.surfaces:
        raise ValueError(f"{spec.name}: surfaces empty")
    _REGISTRY[spec.name] = spec


def all_specs() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def openai_tools(surface: str) -> list[dict]:
    out = []
    for spec in _REGISTRY.values():
        if surface in spec.surfaces:
            out.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            })
    return sorted(out, key=lambda t: t["function"]["name"])


def mcp_tools(surface: str) -> list[dict]:
    out = []
    for spec in _REGISTRY.values():
        if surface in spec.surfaces:
            out.append({
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.parameters,
            })
    return sorted(out, key=lambda t: t["name"])


def execute(name: str, args: dict | None = None, *, surface: str | None = None) -> Any:
    args = args or {}
    spec = _REGISTRY.get(name)
    if spec is None:
        return {"error": f"未知工具 {name}"}
    if surface is not None and surface not in spec.surfaces:
        return {"error": f"工具 {name} 不可用于 {surface} 面"}
    try:
        result = spec.handler(args if isinstance(args, dict) else {}, surface or "mcp")
        result = trim.json_safe(result)
        if surface == "chat":
            result = trim.fit_json_budget(result, CHAT_TOOL_JSON_BUDGET)
        return result
    except Exception as e:  # noqa: BLE001
        return {"error": f"{name} 执行失败：{e}"}
