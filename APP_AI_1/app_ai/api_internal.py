"""
内部接口 - 接收HTTP信号（MQ不可用时的备用方案）
"""
from fastapi import APIRouter
from app_ai.models import NewsIdSignal
from app_ai.interpret_service import interpret_service

router = APIRouter()


@router.post("/internal/newsid")
def receive_signal(signal: NewsIdSignal):
    interpret_service.process(
        news_id=signal.news_id,
        content_type=signal.content_type,
        publish_date=signal.publish_date,
        product_id=signal.product_id,
        product_name=signal.product_name,
    )
    return {"status": "accepted", "news_id": signal.news_id}