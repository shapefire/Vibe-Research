from __future__ import annotations

import json

from tools.registry import ToolSpec, _REGISTRY, execute, mcp_tools, openai_tools, register


def setup_function():
    _REGISTRY.clear()


def test_unknown_tool():
    assert "error" in execute("__no_such_tool__", {})


def test_surface_filter_and_execute():
    register(
        ToolSpec(
            name="t_chat",
            description="客观测试工具",
            parameters={"type": "object", "properties": {}},
            handler=lambda args, surface: {"ok": True},
            surfaces=frozenset({"chat", "mcp"}),
        )
    )
    register(
        ToolSpec(
            name="t_mcp",
            description="客观 MCP 工具",
            parameters={"type": "object", "properties": {}},
            handler=lambda args, surface: {"secret": 1},
            surfaces=frozenset({"mcp"}),
        )
    )
    assert [t["function"]["name"] for t in openai_tools("chat")] == ["t_chat"]
    assert {t["name"] for t in mcp_tools("mcp")} == {"t_chat", "t_mcp"}
    assert execute("t_chat", {}, surface="chat") == {"ok": True}
    assert "error" in execute("t_mcp", {}, surface="chat")
    assert execute("t_mcp", {}, surface="mcp") == {"secret": 1}
    assert "error" in execute("nope", {})


def test_execute_chat_applies_budget():
    big = {"data": [{"x": "z" * 100} for _ in range(200)], "meta": {"truncated": False}}
    register(
        ToolSpec(
            name="t_big",
            description="客观大数据",
            parameters={"type": "object", "properties": {}},
            handler=lambda args, surface: big,
            surfaces=frozenset({"chat", "mcp"}),
        )
    )
    out = execute("t_big", {}, surface="chat")
    assert len(json.dumps(out, ensure_ascii=False)) <= 8000
    assert out["meta"]["truncated"] is True


def test_execute_mcp_skips_budget():
    big = {"data": [{"x": "z" * 100} for _ in range(200)], "meta": {"truncated": False}}
    register(
        ToolSpec(
            name="t_big_mcp",
            description="客观大数据 MCP",
            parameters={"type": "object", "properties": {}},
            handler=lambda args, surface: big,
            surfaces=frozenset({"chat", "mcp"}),
        )
    )
    out = execute("t_big_mcp", {}, surface="mcp")
    assert len(out["data"]) == 200
    assert out["meta"]["truncated"] is False
