"""
LLM服务模块 - 仅从 content 字段获取最终答案，若 content 为空则抛出异常
支持通过 API 参数禁用思考模式（enable_thinking）
"""
import time
import json
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app_ai.config import config
from app_ai.safety import process_output
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """LLM调用服务 - 只信任 content 字段"""

    def __init__(self):
        self.url = config.LLM_URL
        self.api_key = config.LLM_API_KEY
        self.model = config.LLM_MODEL
        self.temperature = config.LLM_TEMPERATURE
        self.timeout = config.LLM_TIMEOUT
        self.max_retries = config.LLM_MAX_RETRIES
        self.enable_thinking = config.LLM_ENABLE_THINKING   # 读取配置

        logger.info(f"[LLM] 初始化: {self.model} @ {self.url}, enable_thinking={self.enable_thinking}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError))
    )
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用模型生成文本，仅从 content 字段获取结果。
        若 content 为 None 或空字符串，则抛出 ValueError 异常。
        """
        headers = {
            "Content-Type": "application/json",
            "apiKey": self.api_key
        }

        # 构造 payload：chat_template_kwargs 直接放在顶层（移除 extra_body）
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": config.LLM_MAX_TOKENS,
            "chat_template_kwargs": {
                "enable_thinking": self.enable_thinking   # False 表示禁用思考模式
            }
        }

        logger.info(f"[LLM] 生成中... 字符: {len(system_prompt) + len(user_prompt)}")
        start = time.time()

        try:
            resp = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            result = resp.json()
            elapsed = time.time() - start

            # 只从 content 字段提取答案
            answer = self._extract_content_only(result)

            if not answer:   # 空字符串或 None
                logger.error(f"[LLM] content 字段为空，解读失败")
                raise ValueError("LLM 返回的 content 字段为空，无法生成解读")

            logger.info(f"[LLM] 完成 | {elapsed:.1f}秒 | {len(answer)}字")
            # 可选：记录 completion_tokens 用于监控
            usage = result.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            if completion_tokens > 2000:
                logger.warning(f"[LLM] completion_tokens 较高({completion_tokens})，思考模式可能未完全禁用")
            return process_output(answer)

        except requests.Timeout:
            elapsed = time.time() - start
            logger.error(f"[LLM] 超时 | {elapsed:.1f}秒")
            raise
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[LLM] 异常 | {elapsed:.1f}秒 | {e}")
            raise

    def _extract_content_only(self, result: dict) -> str:
        """仅从 response.choices[0].message.content 中提取文本，若无则返回空字符串"""
        try:
            choices = result.get("choices", [])
            if not choices:
                logger.warning("[LLM] 响应中没有 choices 字段")
                return ""
            message = choices[0].get("message", {})
            content = message.get("content")
            if content is None:
                logger.warning("[LLM] content 字段为 None")
                return ""
            if isinstance(content, str):
                return content.strip()
            else:
                logger.warning(f"[LLM] content 类型异常: {type(content)}")
                return ""
        except Exception as e:
            logger.error(f"[LLM] 提取 content 时出错: {e}")
            return ""

    def health_check(self) -> bool:
        """健康检查：要求 LLM 返回非空的 content"""
        try:
            headers = {
                "Content-Type": "application/json",
                "apiKey": self.api_key
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "回复OK即可"},
                    {"role": "user", "content": "ping"}
                ],
                "temperature": 0.0,
                "max_tokens": 10,
                "chat_template_kwargs": {
                    "enable_thinking": self.enable_thinking
                }
            }

            resp = requests.post(self.url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            answer = self._extract_content_only(result)
            logger.info(f"[LLM] 健康检查: '{answer[:100]}'")
            return bool(answer and ("OK" in answer or "ok" in answer.lower()))
        except Exception as e:
            logger.error(f"[LLM] 健康检查失败: {e}")
            return False


llm = LLMService()