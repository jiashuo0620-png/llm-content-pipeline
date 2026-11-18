"""Prompt 构造：约束输出结构，并在校验失败后带上问题清单要求返修。"""

from __future__ import annotations

import json

from .models import GeneratedContent, Topic, ValidationIssue
from .validator import ContentRules

SYSTEM_PROMPT = (
    "你是一名资深中文内容编辑，擅长围绕企业业务主题撰写 SEO 友好的结构化稿件。"
    "你必须只输出一个 JSON 对象，不要输出任何解释或 Markdown 代码块。"
)


def build_prompt(topic: Topic, rules: ContentRules) -> str:
    schema = {
        "title": "页面标题，字符串",
        "descriptions": ["描述1", "描述2", "描述3"],
        "body": "正文，段落之间用两个换行符分隔",
    }
    constraints = [
        f"标题长度 {rules.title_min}–{rules.title_max} 字",
        f"描述 {rules.desc_count_min}–{rules.desc_count_max} 条，每条 {rules.desc_min}–{rules.desc_max} 字",
        f"正文 {rules.body_min}–{rules.body_max} 字，分 {rules.paragraph_min}–{rules.paragraph_max} 段",
        "标题必须包含核心词",
        "不要使用占位符，不要出现违禁词",
    ]
    return "\n".join(
        [
            f"核心词：{topic.keyword}",
            f"公司/品牌：{topic.company or '未提供'}",
            "",
            "请输出如下 JSON 结构：",
            json.dumps(schema, ensure_ascii=False, indent=2),
            "",
            "硬性要求：",
            *[f"- {item}" for item in constraints],
        ]
    )


def build_repair_prompt(
    topic: Topic,
    rules: ContentRules,
    previous: GeneratedContent,
    raw_output: str,
    issues: list[ValidationIssue],
) -> str:
    issue_lines = "\n".join(f"- {issue}" for issue in issues)
    return "\n".join(
        [
            f"核心词：{topic.keyword}",
            "",
            "上一版输出未通过校验，问题如下：",
            issue_lines,
            "",
            "上一版 JSON：",
            raw_output[:4000],
            "",
            "请针对性修复以上问题，保持其余内容不变，只输出修复后的完整 JSON 对象。",
            f"仍需满足：标题 {rules.title_min}–{rules.title_max} 字；"
            f"描述 {rules.desc_count_min}–{rules.desc_count_max} 条，每条 {rules.desc_min}–{rules.desc_max} 字；"
            f"正文 {rules.body_min}–{rules.body_max} 字、{rules.paragraph_min}–{rules.paragraph_max} 段。",
        ]
    )
