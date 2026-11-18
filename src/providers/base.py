"""LLM 提供方抽象：换模型/换厂商只需实现一个方法。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """返回模型原始文本输出。"""
        raise NotImplementedError
