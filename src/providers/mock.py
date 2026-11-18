"""离线 Mock 提供方：没有 API Key 也能完整跑通流程。

支持 fixtures.json 按关键词回放预设响应，用来演示「首次不合格 → 修复后通过」
的真实闭环；没有预设的关键词则现场拼一份合规内容。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .base import LLMProvider

TITLE_SUFFIXES = [
    "实战指南：从选型到落地的完整路径",
    "实战指南与落地要点",
    "落地实践与常见问题解析",
]


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, fixtures_path: str | Path | None = None) -> None:
        self._fixtures: Dict[str, List[str]] = {}
        self._cursor: Dict[str, int] = {}
        if fixtures_path and Path(fixtures_path).exists():
            self._fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))

    def complete(self, system: str, user: str) -> str:
        keyword = self._keyword_from_prompt(user)
        queue = self._fixtures.get(keyword, [])
        index = self._cursor.get(keyword, 0)
        self._cursor[keyword] = index + 1
        if index < len(queue):
            return queue[index]
        return json.dumps(self._build_content(keyword), ensure_ascii=False)

    @staticmethod
    def _keyword_from_prompt(prompt: str) -> str:
        marker = "核心词："
        if marker in prompt:
            return prompt.split(marker, 1)[1].splitlines()[0].strip()
        return "示例主题"

    @classmethod
    def _build_content(cls, keyword: str) -> dict:
        return {
            "title": cls._build_title(keyword),
            "descriptions": cls._build_descriptions(keyword),
            "body": cls._build_body(keyword),
        }

    @staticmethod
    def _build_title(keyword: str) -> str:
        title = keyword
        for suffix in TITLE_SUFFIXES:
            candidate = keyword + suffix
            if len(candidate) <= 30:
                title = candidate
                break
        if len(title) < 15:
            title += "实战指南与落地实践"
        return title[:30]

    @staticmethod
    def _fit_description(parts: List[str], min_len: int = 80, max_len: int = 120) -> str:
        text = ""
        for part in parts:
            candidate = text + part
            if len(candidate) > max_len:
                break
            text = candidate
            if len(text) >= min_len:
                break
        return text

    @classmethod
    def _build_descriptions(cls, keyword: str) -> List[str]:
        aspects = ["需求拆解", "方案选型", "执行与复盘"]
        addons = [
            "内容偏实操，适合正在推进相关工作的团队参考。",
            "文中给出可复用的判断标准，帮助减少试错成本。",
            "从目标到落地逐层展开，便于直接对照执行。",
        ]
        descriptions = []
        for aspect, addon in zip(aspects, addons):
            parts = [
                f"围绕{keyword}展开系统梳理，先从{aspect}切入，说明团队在真实项目中如何判断优先级、"
                f"控制投入并保证交付质量，文中给出可执行的检查清单。",
                addon,
            ]
            descriptions.append(cls._fit_description(parts))
        return descriptions

    @staticmethod
    def _build_body(keyword: str) -> str:
        pools = [
            [
                f"很多团队推进{keyword}时，习惯先买工具、先上系统，却忽略了目标本身是否清晰。",
                "更稳妥的做法是先拆解业务链路：哪些环节重复度高、哪些判断依赖人工经验、哪些数据可以沉淀复用。",
                "把这些问题列清楚之后再讨论技术方案，往往能少走很多弯路，也更容易向管理者说明投入产出。",
                "拆解时建议把每一步的输入、输出和判定标准写下来，避免执行过程中反复确认。",
            ],
            [
                f"选型阶段建议同时看三件事：能力边界、接入成本和后续维护。围绕{keyword}的方案可能很多，"
                f"但真正适合团队的通常只有一两种。",
                "可以先做一个最小可行版本，用真实数据跑通闭环，再根据暴露出来的问题决定是否扩大投入。",
                "对比方案时不要只看功能列表，还要看异常处理、日志记录和权限控制是否完整。",
                "如果团队缺少维护人力，优先选择依赖少、文档全、社区活跃的方案。",
            ],
            [
                "执行阶段最重要的不是一次性做全，而是把流程拆成可验证的小步骤。",
                f"每一步都设置明确的输入、输出和判定标准，异常时能快速定位问题。{keyword}相关的任务尤其如此。",
                "先保证单点可靠，再考虑并发和规模，否则问题会被放大，排查成本也会成倍增加。",
                "建议为关键步骤加断言和日志，让每次运行都能留下可追溯的记录。",
            ],
            [
                "最后是复盘。建议记录每次运行的成功率、返工原因和人工介入次数，用数据判断改进方向。",
                f"当{keyword}的流程能够稳定复用时，再把经验沉淀成文档和脚本，降低对个人的依赖。",
                "复盘不需要很长，但要有结论：哪些做法保留、哪些环节替换、下一轮优先解决什么问题。",
                "长期来看，持续的小幅改进比一次性的大改造更容易落地，也更容易被团队接受。",
            ],
        ]
        paragraphs = []
        for pool in pools:
            text = ""
            index = 0
            while len(text) < 560:
                text += pool[index % len(pool)]
                index += 1
            paragraphs.append(text)
        return "\n\n".join(paragraphs)
