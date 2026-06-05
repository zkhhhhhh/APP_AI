"""
查询接口 - 供资讯中台查询AI解读结果
"""
from fastapi import APIRouter, HTTPException, Query
from app_ai.models import SingleResponse, SummaryResponse
from app_ai.interpret_service import interpret_service
from app_ai.summary_service import summary_service

router = APIRouter()


@router.get("/query/single", response_model=SingleResponse)
def query_single(news_id: str = Query(...)):
    result = interpret_service.get_result(news_id)
    if not result:
        raise HTTPException(404, "未找到")
    return result


@router.get("/query/summary", response_model=SummaryResponse)
def query_summary(product_id: int = Query(...), date: str = Query(...)):
    result = summary_service.get_result(product_id, date)
    if not result:
        raise HTTPException(404, "未找到")
    return result