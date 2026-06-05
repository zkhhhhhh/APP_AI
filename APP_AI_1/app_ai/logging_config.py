"""
日志配置
"""
import logging
import sys

def setup_logging():
    """配置日志格式和级别"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # 设置第三方库的日志级别
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)