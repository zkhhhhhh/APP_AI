"""
AI解读服务 - 主入口
"""
from fastapi import FastAPI
from app_ai.database import init_db
from app_ai.api_internal import router as internal_router
from app_ai.api_query import router as query_router
from app_ai.worker import start_all_workers, stop_all_workers
from app_ai.logging_config import setup_logging
from app_ai.llm_service import llm
from app_ai.database import get_db
import logging

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="AI解读服务", version="1.0.0")
app.include_router(internal_router, tags=["内部接口"])
app.include_router(query_router, tags=["查询接口"])


@app.on_event("startup")
def startup():
    logger.info("=" * 50)
    logger.info("AI解读服务启动中...")
    init_db()
    start_all_workers()
    logger.info("服务就绪")
    logger.info("=" * 50)


@app.on_event("shutdown")
def shutdown():
    logger.info("=" * 50)
    logger.info("正在关闭服务...")
    stop_all_workers()
    logger.info("服务已关闭")
    logger.info("=" * 50)


@app.get("/")
def root():
    return {"service": "AI解读服务", "status": "running"}


@app.get("/health")
def health_check():
    """健康检查端点：检查 LLM 和数据库连接"""
    llm_ok = llm.health_check()
    db_ok = False
    try:
        db = get_db()
        db.execute("SELECT 1")
        db.close()
        db_ok = True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
    status = "healthy" if (llm_ok and db_ok) else "unhealthy"
    return {
        "status": status,
        "llm": llm_ok,
        "database": db_ok,
    }