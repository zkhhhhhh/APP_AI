"""
后台Worker - 支持多线程并发MQ消费，带品目列表缓存，汇总支持并发
"""
import threading
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app_ai.config import config
from app_ai.mq_service import MQService, mq_sender
from app_ai.summary_service import summary_service
from app_ai.cms_service import cms
import logging

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_consumer_threads = []
_consumer_services = []

_product_cache = []
_product_cache_time = 0


def get_cached_products():
    global _product_cache, _product_cache_time
    now = time.time()
    if not _product_cache or (now - _product_cache_time) > config.PRODUCT_CACHE_TTL:
        logger.info("[Worker] 刷新品目列表缓存")
        _product_cache = cms.get_all_products()
        _product_cache_time = now
    return _product_cache


def mq_worker(mq_service: MQService):
    logger.info(f"[Worker] MQ Worker (线程{threading.current_thread().name}) 启动")
    while not _stop_event.is_set():
        try:
            mq_service.connect()
            mq_service.start_consuming()
        except Exception as e:
            logger.error(f"[Worker] MQ 连接异常: {e}")
            if not _stop_event.is_set():
                time.sleep(5)
        finally:
            try:
                mq_service.close()
            except:
                pass
    logger.info(f"[Worker] MQ Worker (线程{threading.current_thread().name}) 已停止")


def process_one_product(product: dict, date_str: str):
    pid = product.get("product_id")
    pname = product.get("product_name", str(pid))
    try:
        summary_service.generate(pid, pname, date_str)
    except Exception as e:
        logger.error(f"[汇总Worker] {pname} 异常: {e}")


def summary_worker():
    interval = config.SUMMARY_INTERVAL_MINUTES
    concurrent_workers = config.SUMMARY_CONCURRENT_WORKERS
    logger.info(f"[Worker] 汇总Worker启动（每{interval}分钟，并发数={concurrent_workers}）")

    while not _stop_event.is_set():
        try:
            now = datetime.now()
            current_minutes = now.hour * 60 + now.minute
            next_minutes = ((current_minutes // interval) + 1) * interval
            next_hour = next_minutes // 60
            next_min = next_minutes % 60
            next_time = now.replace(hour=next_hour % 24, minute=next_min, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)

            wait_seconds = (next_time - now).total_seconds()
            _stop_event.wait(timeout=wait_seconds)
            if _stop_event.is_set():
                break

            date_str = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"\n[汇总Worker] ===== {date_str} 汇总（并发模式） =====")

            products = get_cached_products()
            if not products:
                logger.warning("[汇总Worker] 未获取到品目列表，跳过本次汇总")
                _stop_event.wait(timeout=60)
                continue

            with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
                futures = {executor.submit(process_one_product, p, date_str): p for p in products}
                for future in as_completed(futures):
                    if _stop_event.is_set():
                        for f in futures:
                            f.cancel()
                        break
                    try:
                        future.result()
                    except Exception:
                        pass

            logger.info(f"[汇总Worker] ===== 完成 =====")

        except Exception as e:
            logger.error(f"[汇总Worker] 异常: {e}")
            _stop_event.wait(timeout=60)

    logger.info("[Worker] 汇总Worker已停止")


def start_all_workers():
    global _consumer_threads, _consumer_services

    try:
        mq_sender.connect()
        logger.info("[Worker] 全局MQ发送器已连接")
    except Exception as e:
        logger.warning(f"[Worker] 全局MQ发送器连接失败（不影响消费）: {e}")

    thread_count = config.MQ_CONSUMER_THREADS
    logger.info(f"[Worker] 启动 {thread_count} 个MQ消费线程")
    for i in range(thread_count):
        mq_service = MQService()
        t = threading.Thread(target=mq_worker, args=(mq_service,),
                             name=f"mq-consumer-{i}", daemon=False)
        t.start()
        _consumer_threads.append(t)
        _consumer_services.append(mq_service)

    t = threading.Thread(target=summary_worker, name="summary", daemon=False)
    t.start()
    _consumer_threads.append(t)
    _consumer_services.append(None)

    logger.info("[Worker] 全部后台线程已启动")


def stop_all_workers():
    global _stop_event
    _stop_event.set()

    for svc in _consumer_services:
        if svc:
            try:
                svc.close()
            except:
                pass

    try:
        mq_sender.close()
    except:
        pass

    for t in _consumer_threads:
        if t and t.is_alive():
            t.join(timeout=5)

    logger.info("[Worker] 已停止所有后台线程")