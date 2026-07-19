"""Tools registry compliance and hard-cut regression."""
from __future__ import annotations

import importlib
import inspect

import chat
from compliance import assert_compliant
from tools.registry import all_specs


def test_all_tool_descriptions_compliant():
    import tools  # noqa: F401 — ensure domains registered
    import tools.quote_tools as q
    import tools.market_tools as m
    import tools.funds_tools as f
    import tools.fundamentals_tools as fund
    import tools.events_tools as e
    import tools.personal_tools as p

    for mod in (q, m, f, fund, e, p):
        importlib.reload(mod)
    for spec in all_specs():
        assert_compliant(spec.description, context=spec.name)


def test_chat_no_string_hard_cap():
    src = inspect.getsource(chat)
    assert "[:_TOOL_RESULT_CAP]" not in src
    assert "json.dumps(result, ensure_ascii=False)[" not in src


def test_mcp_server_no_chat_tools_import():
    import mcp_server
    src = inspect.getsource(mcp_server)
    assert "chat.TOOLS" not in src
    assert "import chat" not in src
