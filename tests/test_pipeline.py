import json
import unittest

from src.models import Topic
from src.pipeline import ContentPipeline, extract_json
from src.providers.base import LLMProvider
from src.providers.mock import MockProvider


class SequenceProvider(LLMProvider):
    """按顺序返回预设响应，用来模拟「先不合格、返修后合格」。"""

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    def complete(self, system, user):
        index = min(self.calls, len(self.outputs) - 1)
        self.calls += 1
        return self.outputs[index]


class BrokenProvider(LLMProvider):
    def complete(self, system, user):
        raise RuntimeError("接口超时")


def bad_json():
    return json.dumps(
        {"title": "短标题", "descriptions": ["只有一条"], "body": "正文太短。"},
        ensure_ascii=False,
    )


def good_json(keyword="playwright 自动化测试"):
    return json.dumps(MockProvider._build_content(keyword), ensure_ascii=False)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.topic = Topic(row=2, keyword="playwright 自动化测试", company="示例公司")

    def test_first_try_ok(self):
        provider = SequenceProvider([good_json()])
        result = ContentPipeline(provider, delay=0).process_one(self.topic)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.attempts, 1)
        self.assertTrue(result.content.title)

    def test_repair_after_invalid(self):
        provider = SequenceProvider([bad_json(), good_json()])
        result = ContentPipeline(provider, max_repair=2, delay=0).process_one(self.topic)
        self.assertEqual(result.status, "repaired")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.issues, [])

    def test_failed_after_max_repair(self):
        provider = SequenceProvider([bad_json()])
        result = ContentPipeline(provider, max_repair=1, delay=0).process_one(self.topic)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.attempts, 2)
        self.assertTrue(result.issues)

    def test_provider_error_is_captured(self):
        result = ContentPipeline(BrokenProvider(), delay=0).process_one(self.topic)
        self.assertEqual(result.status, "failed")
        self.assertIn("接口超时", result.error)

    def test_extract_json_from_code_fence(self):
        raw = "下面是结果：\n```json\n{\"title\": \"示例\"}\n```\n请查收"
        self.assertEqual(extract_json(raw)["title"], "示例")


if __name__ == "__main__":
    unittest.main()
