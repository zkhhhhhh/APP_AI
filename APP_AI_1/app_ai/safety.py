"""
内容安全过滤 - 增强正则匹配（支持英文常见违规词汇）
"""
import re
from app_ai.config import config

BLOCKED_PATTERNS = [
    # 中文模式
    r'建议(买入|卖出|做多|做空|持有|操作|关注|观望)',
    r'(强烈)?推荐(买入|卖出|关注)',
    r'(必然|势必|肯定|绝对|一定)(上涨|下跌|突破|反弹|回调)',
    r'抄底(时机|机会)?',
    r'逃顶',
    r'目标价[到至看]\d+',
    r'看[到至]\d+元',
    r'(稳|必|包)赚',
    r'(赶紧|赶快|马上|立刻)[买卖出入]',
    r'最后(机会|时机)',
    r'无风险(套利|收益)',
    r'(保证|确保|承诺)收益',
    r'坐等(拉升|上涨|赚钱)',
    r'(必定|肯定|绝对)(暴涨|暴跌|翻倍)',
    # 英文模式（忽略大小写）
    r'(?i)\b(buy|sell|long|short|hold|trade)\b.*?(suggest|recommend|advice)',
    r'(?i)\b(target price|price target)\s*[:=]\s*\d+',
    r'(?i)\b(guaranteed profit|risk-free)\b',
]

COMPILED_PATTERNS = [re.compile(p) for p in BLOCKED_PATTERNS]


def filter_text(text: str) -> str:
    if not text:
        return text
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            import logging
            logging.getLogger(__name__).warning(f"[安全] 过滤: {match.group()}")
            text = pattern.sub("【AI解读】", text)
    return text


def add_disclaimer(text: str) -> str:
    if not text:
        return text
    disclaimer = config.DISCLAIMER
    if not text.rstrip().endswith(disclaimer.strip()):
        text = text.rstrip() + disclaimer
    return text


def process_output(text: str) -> str:
    text = filter_text(text)
    text = add_disclaimer(text)
    return text