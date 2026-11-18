"""流水线编排：生成 → 解析 → 校验 → 带问题返修 → 汇总结果。"""

from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

from .models import GeneratedContent, RowResult, Topic, ValidationIssue
from .prompt import SYSTEM_PROMPT, build_prompt, build_repair_prompt
from .providers.base import LLMProvider
from .validator import ContentRules, validate


class RateLimiter:
    """跨线程共享的最小请求间隔，避免并发把接口打爆。"""

    def __init__(self, delay: float) -> None:
        self.delay = max(delay, 0.0)
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._last + self.delay - now
            self._last = max(now, self._last + self.delay)
        if sleep_for > 0:
            time.sleep(sleep_for)


def extract_json(raw: str) -> dict:
    """从模型输出里提取 JSON，兼容 Markdown 代码块与前后废话。"""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("输出中找不到 JSON 对象")
    return json.loads(text[start : end + 1])


def to_content(data: dict) -> GeneratedContent:
    descriptions = data.get("descriptions") or []
    if isinstance(descriptions, str):
        descriptions = [descriptions]
    return GeneratedContent(
        title=str(data.get("title") or ""),
        descriptions=[str(item) for item in descriptions],
        body=str(data.get("body") or ""),
    )


class ContentPipeline:
    def __init__(
        self,
        provider: LLMProvider,
        rules: ContentRules | None = None,
        max_repair: int = 2,
        concurrency: int = 3,
        delay: float = 0.5,
    ) -> None:
        self.provider = provider
        self.rules = rules or ContentRules()
        self.max_repair = max_repair
        self.concurrency = max(concurrency, 1)
        self.limiter = RateLimiter(delay)

    def process_one(self, topic: Topic) -> RowResult:
        result = RowResult(topic=topic)
        try:
            user_prompt = build_prompt(topic, self.rules)
            raw = self._call(user_prompt)
            attempts = 1
            content, issues = self._parse_and_validate(raw, topic.keyword)

            while (not content or issues) and attempts <= self.max_repair:
                repair_prompt = build_repair_prompt(
                    topic,
                    self.rules,
                    content or GeneratedContent("", [], ""),
                    raw,
                    issues,
                )
                raw = self._call(repair_prompt)
                attempts += 1
                content, issues = self._parse_and_validate(raw, topic.keyword)

            result.attempts = attempts
            result.content = content
            result.issues = issues
            if content and not issues:
                result.status = "ok" if attempts == 1 else "repaired"
            else:
                result.status = "failed"
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
        return result

    def _call(self, user_prompt: str) -> str:
        self.limiter.wait()
        return self.provider.complete(SYSTEM_PROMPT, user_prompt)

    def _parse_and_validate(self, raw: str, keyword: str):
        try:
            content = to_content(extract_json(raw))
        except Exception as exc:
            issue = ValidationIssue("format", f"JSON 解析失败：{exc}")
            return None, [issue]
        validation = validate(content, keyword, self.rules)
        return content, validation.issues

    def run(self, topics: List[Topic]) -> List[RowResult]:
        if self.concurrency == 1:
            return [self.process_one(topic) for topic in topics]
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            return list(executor.map(self.process_one, topics))
