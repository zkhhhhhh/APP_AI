"""
资讯中台接口服务
"""
import requests
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from app_ai.config import config
import logging

logger = logging.getLogger(__name__)


class CMSService:
    """资讯中台API"""

    def __init__(self):
        self.base_url = config.CMS_BASE_URL
        self.info_api_url = config.CMS_INFO_API_URL
        self.timeout = 30

        # InfoTemplate 中文到内部 content_type 的完整映射
        self.content_type_map = {
            "价格信息": "price_info",
            "基本面信息": "fundamental_info",
            "公开消息": "public_news",
            "期货市场": "futures_market",
            "品目级-分析文章": "product_analysis",
            "产业链/行业级-分析文章": "industry_analysis",
            "产业链/行业级-数据汇总": "industry_data_summary",
            "广告服务": "public_news",  # 广告服务归为公开消息
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def get_article(self, news_id: str) -> dict:
        """接口1: GET /info/detail - 获取文章详情（标题、正文、发布日期、infoItemId）"""
        url = f"{self.base_url}/info/detail"
        params = {"news_id": news_id, "tag_name": "App"}
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        info = data.get("info") or {}
        logger.info(f"[CMS] 文章: {news_id}, 标题: {info.get('title', '')[:50]}")
        return data

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def get_all_products(self) -> list:
        """接口2: GET /product/product-list - 获取所有品目"""
        url = f"{self.base_url}/product/product-list"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            products = data
        elif isinstance(data, dict):
            products = data.get("data", data.get("info", []))
        else:
            products = []
        logger.info(f"[CMS] 品目: {len(products)}个")
        return products

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def get_news_ids(self, product_id: int, query_date: str) -> list:
        """接口3: GET /info/newsid - 获取某品目某日期的所有news_id"""
        url = f"{self.base_url}/info/newsid"
        params = {"product_id": product_id, "query_date": query_date}
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "0":
            news_ids = data.get("info", [])
            logger.info(f"[CMS] news_id: {len(news_ids)}条")
            return news_ids
        logger.warning(f"[CMS] 失败: {data.get('msg')}")
        return []

    def get_news_info(self, news_id: int, article_data: dict = None) -> dict:
        """
        根据 news_id 获取资讯的 product_id, product_name, content_type

        流程：
        1. 如果提供了 article_data，则直接从中提取 infoItemId
        2. 否则调用 /info/detail 接口获取 infoItemId
        3. 用 infoItemId 调用 infoitem/search 接口获取 InfoTemplate
        4. 如果获取不到 infoItemId，则回退到原来的直接查询方式
        """
        info_item_id = None
        # 优先使用传入的文章数据
        if article_data:
            info = article_data.get("info", {})
            info_item_id = info.get("infoItemId") or info.get("InfoItemId") or info.get("itemId")
            if info_item_id:
                logger.debug(f"[CMS] 从已有数据获取 infoItemId: {info_item_id}")

        # 如果没有传入或无 infoItemId，则调用接口
        if not info_item_id:
            try:
                article_data = self.get_article(str(news_id))
                info = article_data.get("info", {})
                info_item_id = info.get("infoItemId") or info.get("InfoItemId") or info.get("itemId")
                if info_item_id:
                    logger.info(f"[CMS] 获取到 infoItemId: {info_item_id}")
                else:
                    logger.warning(f"[CMS] 未获取到 infoItemId，将使用原始 news_id 查询")
            except Exception as e:
                logger.warning(f"[CMS] 获取 infoItemId 失败: {e}")

        query_id = info_item_id if info_item_id else news_id
        for id_value in [query_id, str(query_id)]:
            payload = {"id": [id_value]}
            try:
                resp = requests.post(self.info_api_url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                logger.debug(f"[CMS] 请求参数: {payload}, 响应: {data}")
                if data.get("status") == 200:
                    items = data.get("data", [])
                    if items:
                        item = items[0]
                        product_id = item.get("ProductID", 0)
                        product_name = item.get("Product", "")
                        info_template = item.get("InfoTemplate", "")
                        content_type = self.content_type_map.get(info_template, "")
                        if not content_type:
                            logger.warning(f"[CMS] 未知的 InfoTemplate: {info_template}, content_type 将为空")
                        return {
                            "product_id": product_id,
                            "product_name": product_name,
                            "content_type": content_type,
                        }
                    else:
                        logger.warning(f"[CMS] data 为空，尝试 id 类型: {type(id_value)}")
                else:
                    logger.warning(f"[CMS] 状态码非200: {data}")
            except Exception as e:
                logger.warning(f"[CMS] 请求异常 (id={id_value}): {e}")

        logger.error(f"[CMS] 最终无法获取 news_id={news_id} 的信息")
        return {}


cms = CMSService()