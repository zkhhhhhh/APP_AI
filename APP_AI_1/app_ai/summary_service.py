"""
多篇汇总服务 - 合并数据库Session
"""
import time
from datetime import datetime
from app_ai.database import get_db, SingleRecord, SummaryRecord
from app_ai.prompts import get_summary_prompt
from app_ai.llm_service import llm
from app_ai.cms_service import cms
from app_ai.mq_service import mq_sender
import logging

logger = logging.getLogger(__name__)


class SummaryService:

    def generate(self, product_id: int, product_name: str, date: str):
        logger.info(f"[汇总] {product_name}(ID={product_id}) {date}")

        try:
            news_ids = cms.get_news_ids(product_id, date)
        except Exception as e:
            logger.error(f"[汇总] 获取news_id失败: {e}")
            return

        if not news_ids:
            logger.info(f"[汇总] {product_name} {date} 无文章，跳过")
            return

        db = get_db()
        try:
            str_ids = [str(nid) for nid in news_ids]
            records = db.query(SingleRecord).filter(
                SingleRecord.news_id.in_(str_ids),
                SingleRecord.status == "completed"
            ).all()
            interpretations = [r.interpretation for r in records if r.interpretation]

            if not interpretations:
                logger.info(f"[汇总] {product_name} {date} 无已完成解读，跳过")
                return

            # 检查是否已有汇总且无新增
            existing = db.query(SummaryRecord).filter(
                SummaryRecord.product_id == product_id,
                SummaryRecord.summary_date == date
            ).first()

            if existing and existing.status == "completed" and existing.article_count >= len(interpretations):
                logger.info(f"[汇总] {product_name} {date} 已汇总({existing.article_count}篇)，无新增，跳过")
                return

            if existing:
                logger.info(f"[汇总] {product_name} {date} 新增: {existing.article_count}→{len(interpretations)}篇")

            # 调用LLM
            sp, up = get_summary_prompt(product_name, date, interpretations)
            start = time.time()
            summary_text = llm.generate(sp, up)
            elapsed = time.time() - start

            # 存储汇总结果
            if existing:
                existing.summary_text = summary_text
                existing.article_count = len(interpretations)
                existing.status = "completed"
                existing.cost_time = elapsed
                existing.updated_at = datetime.utcnow()
            else:
                record = SummaryRecord(
                    product_id=product_id, product_name=product_name,
                    summary_date=date, summary_text=summary_text,
                    article_count=len(interpretations), status="completed", cost_time=elapsed
                )
                db.add(record)
            db.commit()
            logger.info(f"[汇总] 完成: {product_name} {date} | {len(interpretations)}篇 | {elapsed:.1f}秒")

        except Exception as e:
            logger.error(f"[汇总] 存储失败: {e}")
            db.rollback()
            raise
        finally:
            db.close()

        # 发送通知
        try:
            mq_sender.send_summary_result(product_id, product_name, date, "completed")
        except Exception as e:
            logger.error(f"[汇总] 通知失败: {e}")

    def get_result(self, product_id: int, date: str) -> dict:
        db = get_db()
        try:
            record = db.query(SummaryRecord).filter(
                SummaryRecord.product_id == product_id,
                SummaryRecord.summary_date == date
            ).first()
            if not record:
                return None
            ai_generated_at = ""
            if record.created_at:
                ai_generated_at = record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            return {
                "product_id": record.product_id,
                "product_name": record.product_name,
                "date": record.summary_date,
                "summary_text": record.summary_text or "",
                "article_count": record.article_count or 0,
                "status": record.status or "",
                "ai_generated_at": ai_generated_at,
            }
        finally:
            db.close()


summary_service = SummaryService()