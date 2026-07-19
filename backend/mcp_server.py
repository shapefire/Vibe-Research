"""Vibe-Research MCP server —— 把 A股数据工具暴露给 Claude Code 等 agent。

零第三方依赖（纯标准库 JSON-RPC over stdio），复用 tools 注册表 +
astock 数据层。给「订阅接入 / 高手」通道用：agent 用自己的
订阅额度直接调数据、多步分析，不占本产品成本。

挂进 Claude Code：
    claude mcp add vibe-research -- /路径/backend/.venv/bin/python /路径/backend/mcp_server.py

合规：工具只返回客观数据，不含建议；判断由调用方 agent 给出。
"""

from __future__ import annotations

import json
import sys

import tools as tools_mod

SERVER_INFO = {"name": "vibe-research", "version": "0.2.0"}
DEFAULT_PROTOCOL = "2024-11-05"


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _result(rid, result) -> None:
    _send({"jsonrpc": "2.0", "id": rid, "result": result})


def _error(rid, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


def _handle(msg: dict) -> None:
    method = msg.get("method")
    rid = msg.get("id")

    # 通知（无 id）不回响应
    if method == "notifications/initialized":
        return

    if method == "initialize":
        params = msg.get("params") or {}
        proto = params.get("protocolVersion", DEFAULT_PROTOCOL)
        _result(rid, {
            "protocolVersion": proto,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
        return

    if method == "ping":
        _result(rid, {})
        return

    if method == "tools/list":
        _result(rid, {"tools": tools_mod.mcp_tools("mcp")})
        return

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        data = tools_mod.execute(name, args, surface="mcp")
        is_error = isinstance(data, dict) and "error" in data
        _result(rid, {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
            "isError": is_error,
        })
        return

    if rid is not None:
        _error(rid, -32601, f"未知方法：{method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            _handle(msg)
        except Exception as e:  # noqa: BLE001 — 单条消息出错不拖垮 server
            if msg.get("id") is not None:
                _error(msg["id"], -32603, f"内部错误：{e}")


if __name__ == "__main__":
    main()
