"""
数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class NewsIdSignal(BaseModel):
    news_id: str = Field(..., description="资讯ID")
    content_type: str = Field(..., description="内容类型")
    publish_date: str = Field(..., description="发布日期")
    product_id: int = Field(..., description="品目ID")
    product_name: str = Field(default="", description="品目名称")


class SingleResponse(BaseModel):
    news_id: str = ""
    title: str = ""
    interpretation: str = ""
    status: str = ""
    error_msg: str = ""
    content_type: str = ""
    product_name: str = ""
    ai_generated_at: Optional[str] = ""


class SummaryResponse(BaseModel):
    product_id: int = 0
    product_name: str = ""
    date: str = ""
    summary_text: str = ""
    article_count: int = 0
    status: str = ""
    ai_generated_at: Optional[str] = ""