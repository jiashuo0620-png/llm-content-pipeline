"""OpenAI 兼容接口适配器（OpenAI / DeepSeek / 通义 / 本地 vLLM 等）。

通过环境变量配置，避免把密钥写进代码：
    LLM_BASE_URL  默认 https://api.openai.com/v1
    LLM_API_KEY   必填
    LLM_MODEL     默认 gpt-4o-mini
"""

from __future__ import annotations

import os
import time

import requests

from .base import LLMProvider


class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 120,
        max_retries: int = 3,
    ) -> None:
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        self.timeout = timeout
        self.max_retries = max_retries
        if not self.api_key:
            raise ValueError("缺少 LLM_API_KEY，请通过环境变量配置")

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:  # 网络/限流/响应结构异常统一重试
                last_error = exc
                time.sleep(2**attempt)
        raise RuntimeError(f"LLM 调用失败（已重试 {self.max_retries} 次）：{last_error}")
