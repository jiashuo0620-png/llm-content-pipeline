import unittest

from src.models import GeneratedContent
from src.providers.mock import MockProvider
from src.validator import ContentRules, validate


def build_valid(keyword="playwright 自动化测试"):
    data = MockProvider._build_content(keyword)
    return GeneratedContent(**data)


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        self.rules = ContentRules()
        self.keyword = "playwright 自动化测试"

    def test_mock_content_passes(self):
        result = validate(build_valid(), self.keyword, self.rules)
        self.assertTrue(result.ok, [str(issue) for issue in result.issues])

    def test_short_title_rejected(self):
        content = build_valid()
        content.title = "短标题"
        result = validate(content, self.keyword, self.rules)
        self.assertFalse(result.ok)
        self.assertTrue(any(issue.field == "title" for issue in result.issues))

    def test_title_missing_keyword_rejected(self):
        content = build_valid()
        content.title = "企业自动化落地实践与常见问题解析"
        result = validate(content, self.keyword, self.rules)
        self.assertTrue(any("核心词" in issue.message for issue in result.issues))

    def test_description_count_rejected(self):
        content = build_valid()
        content.descriptions = content.descriptions[:1]
        result = validate(content, self.keyword, self.rules)
        self.assertTrue(any(issue.field == "descriptions" for issue in result.issues))

    def test_duplicate_description_rejected(self):
        content = build_valid()
        content.descriptions[1] = content.descriptions[0]
        result = validate(content, self.keyword, self.rules)
        self.assertTrue(any("重复" in issue.message for issue in result.issues))

    def test_short_body_rejected(self):
        content = build_valid()
        content.body = "太短了。"
        result = validate(content, self.keyword, self.rules)
        self.assertTrue(any(issue.field == "body" for issue in result.issues))

    def test_forbidden_word_rejected(self):
        content = build_valid()
        content.body += "我们是行业第一品牌。"
        result = validate(content, self.keyword, self.rules)
        self.assertTrue(any("违禁词" in issue.message for issue in result.issues))

    def test_placeholder_rejected(self):
        content = build_valid()
        content.body += "这里是【占位】内容。"
        result = validate(content, self.keyword, self.rules)
        self.assertTrue(any("占位符" in issue.message for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
