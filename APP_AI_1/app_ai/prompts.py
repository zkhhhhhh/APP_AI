"""
Prompt模板 - 移除print，使用logging
"""
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的大宗商品市场分析师。
核心原则：
1. 只陈述事实，不预测价格，不给投资建议
2. 不补充原文没有的信息
3. 用具体数字，不用"大幅""明显"等模糊词
4. 禁止使用"建议买入""建议卖出""必然上涨"等词汇"""

PRICE_INFO = """提取价格信息：品种+规格、价格数值、涨跌幅度。禁止分析原因、禁止预测。字数80-120字。

标题：{title}
内容：{content}"""

FUNDAMENTAL_INFO = """按供应→需求→库存→进出口顺序整理基本面，有则写无则跳过。禁止推导对价格的影响。字数120-180字。

标题：{title}
内容：{content}"""

PUBLIC_NEWS = """提炼公开消息：核心内容、来源、影响品种/环节。禁止揣测政策意图。字数100-150字。

标题：{title}
内容：{content}"""

FUTURES_MARKET = """提取期货数据：合约、价格变动、持仓、成交量。禁止多空判断。字数120-180字。

标题：{title}
内容：{content}"""

PRODUCT_ANALYSIS = """提炼品种分析：供需、库存、价差、市场心态。未提及标"原文未提及"。禁止预测。字数180-250字。

标题：{title}
内容：{content}"""

INDUSTRY_ANALYSIS = """产业链视角：产业链环节、各环节变化、传导方向、受影响品种。禁止投资建议。字数200-280字。

标题：{title}
内容：{content}"""

INDUSTRY_DATA = """整合多品种数据：品种列表、关键指标变化、异常值、行业整体状态。字数150-200字。

标题：{title}
内容：{content}"""

GENERIC_PROMPT = """请根据以下内容，客观提炼核心事实信息，不添加原文未提及的内容，不预测未来，不给出投资建议。按原文顺序整理关键点。字数150-250字。

标题：{title}
内容：{content}"""

PROMPT_MAP = {
    "price_info": PRICE_INFO,
    "fundamental_info": FUNDAMENTAL_INFO,
    "public_news": PUBLIC_NEWS,
    "futures_market": FUTURES_MARKET,
    "product_analysis": PRODUCT_ANALYSIS,
    "industry_analysis": INDUSTRY_ANALYSIS,
    "industry_data_summary": INDUSTRY_DATA,
}


def get_prompt(content_type: str, title: str, content: str):
    template = PROMPT_MAP.get(content_type)
    if not template:
        logger.warning(f"未知类型 '{content_type}'，使用通用模板")
        template = GENERIC_PROMPT

    if len(content) > 5000:
        content = content[:5000] + "\n...(已截断)"

    return SYSTEM_PROMPT, template.format(title=title, content=content)


SUMMARY_PROMPT = """以下是{product_name}在{date}的多篇解读，整合为一篇日报综述。
按重要性排序，合并同类信息。字数300-500字。禁止预测。

各篇解读：
{interpretations}"""


def get_summary_prompt(product_name: str, date: str, interpretations: list):
    parts = [f"[{i+1}] {t}" for i, t in enumerate(interpretations)]
    return SYSTEM_PROMPT, SUMMARY_PROMPT.format(
        product_name=product_name, date=date,
        interpretations="\n\n".join(parts)
    )