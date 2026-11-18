"""数据结构定义：输入主题、生成内容、校验结果与单行处理结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Topic:
    """表格中的一行输入。row 为 Excel 行号，用于回填定位。"""

    row: int
    keyword: str
    company: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedContent:
    """LLM 生成的结构化内容。"""

    title: str
    descriptions: List[str]
    body: str


@dataclass
class ValidationIssue:
    """一条校验问题，field 对应 title / descriptions / body。"""

    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.field}] {self.message}"


@dataclass
class ValidationResult:
    ok: bool
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class RowResult:
    """单行最终结果。status: ok / repaired / failed。"""

    topic: Topic
    content: GeneratedContent | None = None
    status: str = "failed"
    attempts: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    error: str = ""
