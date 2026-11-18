"""结构化校验：把「写得像不像能用的稿子」变成可执行的硬规则。

LLM 的输出不稳定，靠人眼验收不可规模复制，所以这里把验收标准
（标题长度、描述条数、正文篇幅、段落数、违禁词等）固化成规则，
不通过就带着问题清单回炉重写。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .models import GeneratedContent, ValidationIssue, ValidationResult


@dataclass
class ContentRules:
    title_min: int = 15
    title_max: int = 30
    desc_count_min: int = 3
    desc_count_max: int = 4
    desc_min: int = 80
    desc_max: int = 120
    body_min: int = 2000
    body_max: int = 3000
    paragraph_min: int = 4
    paragraph_max: int = 5
    must_contain_keyword: bool = True
    forbidden_words: List[str] = field(
        default_factory=lambda: ["绝对", "第一品牌", "国家级", "100%", "包治百病"]
    )


def _visible_len(text: str) -> int:
    """统计字符数，忽略空白，避免换行和缩进影响篇幅判断。"""
    return len(re.sub(r"\s", "", text or ""))


def _paragraphs(body: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]


def validate(
    content: GeneratedContent,
    keyword: str,
    rules: ContentRules | None = None,
) -> ValidationResult:
    rules = rules or ContentRules()
    issues: List[ValidationIssue] = []

    title = (content.title or "").strip()
    title_len = _visible_len(title)
    if not title:
        issues.append(ValidationIssue("title", "标题为空"))
    else:
        if title_len < rules.title_min:
            issues.append(
                ValidationIssue("title", f"标题 {title_len} 字，少于 {rules.title_min} 字")
            )
        if title_len > rules.title_max:
            issues.append(
                ValidationIssue("title", f"标题 {title_len} 字，超过 {rules.title_max} 字")
            )
        if rules.must_contain_keyword and keyword not in title:
            issues.append(ValidationIssue("title", f"标题未包含核心词「{keyword}」"))

    descs = [d.strip() for d in (content.descriptions or []) if d.strip()]
    if len(descs) < rules.desc_count_min or len(descs) > rules.desc_count_max:
        issues.append(
            ValidationIssue(
                "descriptions",
                f"描述 {len(descs)} 条，应为 {rules.desc_count_min}–{rules.desc_count_max} 条",
            )
        )
    for index, desc in enumerate(descs, start=1):
        length = _visible_len(desc)
        if length < rules.desc_min:
            issues.append(
                ValidationIssue("descriptions", f"第 {index} 条描述 {length} 字，少于 {rules.desc_min} 字")
            )
        if length > rules.desc_max:
            issues.append(
                ValidationIssue("descriptions", f"第 {index} 条描述 {length} 字，超过 {rules.desc_max} 字")
            )
    seen = set()
    for index, desc in enumerate(descs, start=1):
        if desc in seen:
            issues.append(ValidationIssue("descriptions", f"第 {index} 条描述与前面重复"))
        seen.add(desc)

    body = (content.body or "").strip()
    body_len = _visible_len(body)
    if not body:
        issues.append(ValidationIssue("body", "正文为空"))
    else:
        if body_len < rules.body_min:
            issues.append(ValidationIssue("body", f"正文 {body_len} 字，少于 {rules.body_min} 字"))
        if body_len > rules.body_max:
            issues.append(ValidationIssue("body", f"正文 {body_len} 字，超过 {rules.body_max} 字"))
        paragraphs = _paragraphs(body)
        if len(paragraphs) < rules.paragraph_min or len(paragraphs) > rules.paragraph_max:
            issues.append(
                ValidationIssue(
                    "body",
                    f"正文 {len(paragraphs)} 段，应为 {rules.paragraph_min}–{rules.paragraph_max} 段",
                )
            )

    text = "\n".join([title, *descs, body])
    for word in rules.forbidden_words:
        if word and word in text:
            issues.append(ValidationIssue("text", f"出现违禁词「{word}」"))

    if "【" in text or "】" in text:
        issues.append(ValidationIssue("text", "出现未替换的占位符【】"))

    return ValidationResult(ok=not issues, issues=issues)
