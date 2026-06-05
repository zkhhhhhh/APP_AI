"""
单篇解读服务 - 优化数据库Session管理
"""
import time
from datetime import datetime
from app_ai.database import get_db, SingleRecord
from app_ai.prompts import get_prompt
from app_ai.llm_service import llm
from app_ai.cms_service import cms
from app_ai.content_cleaner import html_to_text
import logging

logger = logging.getLogger(__name__)


class InterpretService:
    """单篇解读"""

    def process(self, news_id: str, content_type: str,
                publish_date: str, product_id: int, product_name: str,
                article_info: dict = None):
        db = get_db()
        try:
            # 查询或创建记录
            record = db.query(SingleRecord).filter(SingleRecord.news_id == news_id).first()
            if record and record.status == "completed":
                logger.info(f"[跳过] {news_id} 已完成")
                return

            if record:
                record.status = "processing"
                record.updated_at = datetime.utcnow()
            else:
                record = SingleRecord(
                    news_id=news_id, content_type=content_type,
                    product_id=product_id, product_name=product_name,
                    publish_date=publish_date, status="processing"
                )
                db.add(record)
            db.commit()

            # 获取文章详情
            if article_info:
                title = article_info.get("title", "")
                raw_content = article_info.get("content", "")
                if not raw_content:
                    raise Exception("article_info 中的 content 为空")
                content = html_to_text(raw_content)
            else:
                article = cms.get_article(news_id)
                info = article.get("info") or {}
                title = info.get("title", "")
                raw_content = info.get("enhancedContent", "")
                if not raw_content:
                    raise Exception("enhancedContent为空")
                content = html_to_text(raw_content)

            logger.info(f"[解读] {news_id} | {title[:40]} | {len(content)}字")
            sp, up = get_prompt(content_type, title, content)
            start = time.time()
            interpretation = llm.generate(sp, up)
            elapsed = time.time() - start

            record.title = title
            record.original_text = content
            record.interpretation = interpretation
            record.status = "completed"
            record.cost_time = elapsed
            record.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"[完成] {news_id} | {elapsed:.1f}秒 | {len(interpretation)}字")

        except Exception as e:
            logger.error(f"[失败] {news_id}: {e}")
            try:
                # 重新查询以确保记录存在
                record = db.query(SingleRecord).filter(SingleRecord.news_id == news_id).first()
                if record:
                    record.status = "failed"
                    record.error_msg = str(e)[:500]
                    record.updated_at = datetime.utcnow()
                    db.commit()
            except Exception as db_err:
                logger.error(f"更新失败状态出错: {db_err}")
            raise
        finally:
            db.close()

    def get_result(self, news_id: str) -> dict:
        db = get_db()
        try:
            record = db.query(SingleRecord).filter(SingleRecord.news_id == news_id).first()
            if not record:
                return None
            ai_generated_at = ""
            if record.created_at:
                ai_generated_at = record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            return {
                "news_id": record.news_id,
                "title": record.title or "",
                "interpretation": record.interpretation or "",
                "status": record.status or "",
                "error_msg": record.error_msg or "",
                "content_type": record.content_type or "",
                "product_name": record.product_name or "",
                "ai_generated_at": ai_generated_at,
            }
        finally:
            db.close()


interpret_service = InterpretService()