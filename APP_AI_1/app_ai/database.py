"""
数据库模型和连接 - 支持 SQLite 和 PostgreSQL
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app_ai.config import config

Base = declarative_base()


class SingleRecord(Base):
    """单篇解读存储表"""
    __tablename__ = "single_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(String(32), unique=True, nullable=False)
    title = Column(String(200))
    content_type = Column(String(50))
    original_text = Column(Text)
    interpretation = Column(Text)
    product_id = Column(Integer)
    product_name = Column(String(100))
    publish_date = Column(String(20))
    status = Column(String(20), default="pending")
    error_msg = Column(String(500))
    cost_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SummaryRecord(Base):
    """每日汇总存储表"""
    __tablename__ = "summary_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(100), nullable=False)
    summary_date = Column(String(20), nullable=False)
    summary_text = Column(Text)
    article_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    cost_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 创建引擎，SQLite 下已配置 timeout 和 check_same_thread
engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,           # 自动重连
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    # 使用 logging 代替 print
    import logging
    logging.info("[数据库] 初始化完成")


def get_db():
    return SessionLocal()