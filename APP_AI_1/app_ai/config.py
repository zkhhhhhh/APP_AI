"""
配置管理
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """全局配置类"""

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    LLM_URL = os.getenv("LLM_URL", "http://192.168.6.187:8000/v1/chat/completions")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-adef135xf")
    LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen3.5-35B-A3B")
    LLM_TEMPERATURE = 0.0
    LLM_MAX_TOKENS = 24576
    LLM_TIMEOUT = 300
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
    LLM_RETRY_WAIT_MIN = 1
    LLM_RETRY_WAIT_MAX = 10

    LLM_ENABLE_THINKING = os.getenv("LLM_ENABLE_THINKING", "false").lower() == "true"

    CMS_BASE_URL = os.getenv("CMS_BASE_URL", "http://mtdservice.sci99.com/info_v2")
    CMS_INFO_API_URL = os.getenv(
        "CMS_INFO_API_URL",
        "https://oaapi.sci99.com/dmapi/ds/mtd/infoitem/search"
    )

    MAX_CONCURRENT = 3
    SUMMARY_INTERVAL_MINUTES = int(os.getenv("SUMMARY_INTERVAL_MINUTES", "60"))
    PRODUCT_CACHE_TTL = int(os.getenv("PRODUCT_CACHE_TTL", "3600"))

    MQ_HOST = os.getenv("MQ_HOST", "192.168.7.191")
    MQ_PORT = int(os.getenv("MQ_PORT", "5672"))
    MQ_USERNAME = os.getenv("MQ_USERNAME", "guest")
    MQ_PASSWORD = os.getenv("MQ_PASSWORD", "guest")
    MQ_VHOST = os.getenv("MQ_VHOST", "CMS")
    MQ_SIGNAL_QUEUE = os.getenv("MQ_SIGNAL_QUEUE", "q_sci_news_enhance_ai_summary")
    MQ_RESULT_QUEUE = os.getenv("MQ_RESULT_QUEUE", "q_sci_news_enhance_ai_summary_result")
    MQ_CONSUMER_THREADS = int(os.getenv("MQ_CONSUMER_THREADS", "3"))
    MQ_MAX_RETRIES = int(os.getenv("MQ_MAX_RETRIES", "3"))

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db?check_same_thread=False&timeout=30")

    SUMMARY_CONCURRENT_WORKERS = int(os.getenv("SUMMARY_CONCURRENT_WORKERS", "3"))

    DISCLAIMER = "\n\n---\n以上内容由AI生成，不构成投资建议。"


config = Config()