"""
RabbitMQ 消息队列服务
"""
import json
import time
import pika
from datetime import datetime
from app_ai.config import config
from app_ai.interpret_service import interpret_service
from app_ai.cms_service import cms
from app_ai.content_cleaner import html_to_text
import logging

logger = logging.getLogger(__name__)


class MQService:
    """RabbitMQ服务 - 每个实例独立连接，用于并发消费"""

    def __init__(self):
        self.host = config.MQ_HOST
        self.port = config.MQ_PORT
        self.username = config.MQ_USERNAME
        self.password = config.MQ_PASSWORD
        self.vhost = config.MQ_VHOST
        self.signal_queue = config.MQ_SIGNAL_QUEUE
        self.result_queue = config.MQ_RESULT_QUEUE
        self.max_retries = config.MQ_MAX_RETRIES
        self.connection = None
        self.channel = None

    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host, port=self.port, virtual_host=self.vhost,
            credentials=credentials, heartbeat=600,
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.result_queue, durable=True)
        logger.info(f"[MQ] 已连接 {self.host}:{self.port}/{self.vhost}")
        logger.info(f"[MQ] 接收: {self.signal_queue}")
        logger.info(f"[MQ] 发送: {self.result_queue}")

    def start_consuming(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=self.signal_queue,
            on_message_callback=self._handle_message,
            auto_ack=False
        )
        logger.info(f"[MQ] 开始监听: {self.signal_queue}")
        self.channel.start_consuming()

    def _handle_message(self, ch, method, properties, body):
        news_id = ""
        retry_count = 0
        try:
            message = json.loads(body)
            news_id = message.get("news_id")
            if not news_id:
                logger.warning(f"[MQ] 消息缺少 news_id，跳过")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if properties.headers and 'x-retry-count' in properties.headers:
                retry_count = properties.headers['x-retry-count']
            else:
                retry_count = 0

            if retry_count >= self.max_retries:
                logger.error(f"[MQ] news_id={news_id} 重试已达 {self.max_retries} 次，丢弃消息并记录失败")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            logger.info(f"\n[MQ] 收到 news_id: {news_id} (重试次数: {retry_count})")

            article_data = cms.get_article(str(news_id))
            info = article_data.get("info", {})
            title = info.get("title", "")
            raw_content = info.get("enhancedContent", "")
            if not raw_content:
                raise Exception("enhancedContent为空")
            content = html_to_text(raw_content)

            publish_date = info.get("pubDate", "") or info.get("publishDate", "")
            if not publish_date:
                publish_date = datetime.now().strftime("%Y-%m-%d")
                logger.warning(f"[MQ] 未获取到发布日期，使用今日日期 {publish_date}")
            else:
                publish_date = publish_date.split()[0] if " " in publish_date else publish_date

            extra_info = cms.get_news_info(int(news_id), article_data=article_data)
            if not extra_info:
                logger.warning(f"[MQ] 警告: 无法获取 news_id={news_id} 的品目信息，使用默认值")
                extra_info = {}

            product_id = extra_info.get("product_id", 0)
            product_name = extra_info.get("product_name", "")
            content_type = extra_info.get("content_type", "")

            interpret_service.process(
                news_id=str(news_id),
                content_type=content_type,
                publish_date=publish_date,
                product_id=product_id,
                product_name=product_name,
                article_info={
                    "title": title,
                    "content": content,
                }
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

            try:
                self.send_single_result(news_id, "completed")
            except Exception as e:
                logger.error(f"[MQ] 发送结果通知失败: {e}")

        except Exception as e:
            logger.error(f"[MQ] 处理失败: {news_id}, 错误: {e}")
            retry_count += 1
            headers = properties.headers if properties.headers else {}
            headers['x-retry-count'] = retry_count
            try:
                ch.basic_publish(
                    exchange='',
                    routing_key=method.routing_key,
                    body=body,
                    properties=pika.BasicProperties(headers=headers, delivery_mode=2)
                )
            except Exception as pub_err:
                logger.error(f"[MQ] 重新发布消息失败: {pub_err}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _ensure_connection(self):
        if not self._is_ready():
            logger.warning("[MQ] 连接已断开，尝试重连...")
            try:
                self.connect()
            except Exception as e:
                logger.error(f"[MQ] 重连失败: {e}")
                raise

    def send_single_result(self, news_id: str, status: str):
        max_retry = 2
        for attempt in range(max_retry):
            try:
                self._ensure_connection()
                message = json.dumps({"news_id": news_id, "status": status, "type": "single"}, ensure_ascii=False)
                self.channel.basic_publish(
                    exchange='', routing_key=self.result_queue, body=message,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                logger.info(f"[MQ] 通知: {news_id} -> {status}")
                return
            except Exception as e:
                logger.error(f"[MQ] 发送失败 (尝试 {attempt+1}/{max_retry}): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)
                    self.close()
                else:
                    logger.error(f"[MQ] 最终发送失败，放弃通知: {news_id}")

    def send_summary_result(self, product_id: int, product_name: str, date: str, status: str):
        max_retry = 2
        for attempt in range(max_retry):
            try:
                self._ensure_connection()
                message = json.dumps({
                    "product_id": product_id, "product_name": product_name,
                    "date": date, "status": status, "type": "summary"
                }, ensure_ascii=False)
                self.channel.basic_publish(
                    exchange='', routing_key=self.result_queue, body=message,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                logger.info(f"[MQ] 通知汇总: {product_name} {date} -> {status}")
                return
            except Exception as e:
                logger.error(f"[MQ] 发送汇总失败 (尝试 {attempt+1}/{max_retry}): {e}")
                if attempt < max_retry - 1:
                    time.sleep(1)
                    self.close()
                else:
                    logger.error(f"[MQ] 最终发送汇总失败，放弃通知: {product_name} {date}")

    def _is_ready(self):
        return self.channel is not None and self.connection is not None and self.connection.is_open

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("[MQ] 连接已关闭")
        self.connection = None
        self.channel = None


mq_sender = MQService()