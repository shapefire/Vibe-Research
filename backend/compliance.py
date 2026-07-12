"""合规检测 —— 违禁短语扫描与 Prompt 完整性校验。

供 pytest 回归、未来 digest/notify 文案生成时调用。
不 import 业务模块（chat 等由测试侧 import）。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 必要 Prompt 句段（与 chat.py SYSTEM_PROMPT L51 对齐）
# ---------------------------------------------------------------------------
REQUIRED_PROMPT_FRAGMENTS: list[str] = [
    "不推荐",
    "不预测",
    "不给买卖时机",
    "不承诺收益",
    "不打分排名",
]

# ---------------------------------------------------------------------------
# 违禁正则表 —— 按类别分组，模块级编译一次
# ---------------------------------------------------------------------------
_RAW_BANNED_PATTERNS: list[tuple[str, str]] = [
    # 买卖建议
    ("buy_advice", r"建议.{0,4}买入"),
    ("buy_advice", r"建议.{0,4}卖出"),
    ("buy_advice", r"建议买入"),
    ("buy_advice", r"建议卖出"),
    ("buy_advice", r"立即建仓"),
    ("buy_advice", r"清仓离场"),
    ("buy_advice", r"建议加仓"),
    ("buy_advice", r"建议减仓"),
    # 价格预测（须含数字或金额，避免误杀「不做目标价建议」等合规表述）
    ("price_prediction", r"目标价\s*[\d]"),
    ("price_prediction", r"目标价.{0,4}元"),
    ("price_prediction", r"看涨至"),
    ("price_prediction", r"看跌至"),
    ("price_prediction", r"必涨到"),
    ("price_prediction", r"必跌到"),
    # 收益承诺
    ("return_promise", r"稳赚"),
    ("return_promise", r"保本"),
    ("return_promise", r"翻倍"),
    ("return_promise", r"必赚"),
    # 主观评级
    ("subjective_rating", r"强烈推荐"),
    ("subjective_rating", r"买入评级"),
    ("subjective_rating", r"卖出评级"),
    ("subjective_rating", r"五星推荐"),
    # 时机建议
    ("timing_advice", r"现在买"),
    ("timing_advice", r"马上卖"),
    ("timing_advice", r"最佳买点"),
    ("timing_advice", r"抄底时机"),
]

BANNED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pat) for _, pat in _RAW_BANNED_PATTERNS
]

_PATTERN_NAMES: list[str] = [name for name, _ in _RAW_BANNED_PATTERNS]

# 06/07 预埋常量
DIGEST_FOOTER = "*纯数据摘要，不构成投资建议*"
PUSH_FOOTER = "*纯数据摘要，不构成投资建议*"


class ComplianceViolation(Exception):
    """文本命中违禁模式。"""

    def __init__(self, matches: list[dict], *, context: str = "") -> None:
        self.matches = matches
        self.context = context
        parts = [
            f"matched '{m['match']}' (pattern={m['pattern']})" for m in matches
        ]
        prefix = f"[context={context}] " if context else ""
        super().__init__(f"ComplianceViolation: {prefix}{'; '.join(parts)}")


def scan_text(text: str) -> list[dict]:
    """扫描文本，返回 [{pattern, match, span}] 命中列表。"""
    hits: list[dict] = []
    for name, compiled in zip(_PATTERN_NAMES, BANNED_PATTERNS):
        for m in compiled.finditer(text):
            hits.append({
                "pattern": name,
                "match": m.group(),
                "span": m.span(),
            })
    return hits


def assert_compliant(text: str, *, context: str = "") -> None:
    """无命中则通过；有命中则抛 ComplianceViolation。"""
    matches = scan_text(text)
    if matches:
        raise ComplianceViolation(matches, context=context)


def validate_system_prompt(prompt: str) -> list[str]:
    """检查 prompt 是否包含必要合规句段，返回缺失项列表。"""
    return [frag for frag in REQUIRED_PROMPT_FRAGMENTS if frag not in prompt]
