"""命令行入口：跑通「读表 → 批量生成 → 校验返修 → Excel 回填」。"""

from __future__ import annotations

import argparse
import sys

from src.excel_io import read_topics, write_results
from src.pipeline import ContentPipeline
from src.providers.mock import MockProvider
from src.providers.openai_compat import OpenAICompatProvider
from src.validator import ContentRules


def build_provider(name: str, fixtures: str):
    if name == "mock":
        return MockProvider(fixtures)
    return OpenAICompatProvider()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM 批量内容生成流水线")
    parser.add_argument("--input", required=True, help="输入 Excel 路径")
    parser.add_argument("--output", default="outputs/result.xlsx", help="输出 Excel 路径")
    parser.add_argument("--provider", choices=["mock", "openai"], default="mock", help="LLM 提供方")
    parser.add_argument("--fixtures", default="data/fixtures.json", help="Mock 回放数据路径")
    parser.add_argument("--sheet", default=None, help="工作表名称，默认第一个")
    parser.add_argument("--max-repair", type=int, default=2, help="最大返修次数")
    parser.add_argument("--concurrency", type=int, default=3, help="并发数")
    parser.add_argument("--delay", type=float, default=0.5, help="每次请求最小间隔（秒）")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 行，0 表示全部")
    parser.add_argument("--body-min", type=int, default=2000, help="正文最少字数")
    parser.add_argument("--body-max", type=int, default=3000, help="正文最多字数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rules = ContentRules(body_min=args.body_min, body_max=args.body_max)
    topics = read_topics(args.input, args.sheet)
    if args.limit > 0:
        topics = topics[: args.limit]
    if not topics:
        print("没有读到有效数据（检查「关键词」列是否为空）")
        return 1

    pipeline = ContentPipeline(
        provider=build_provider(args.provider, args.fixtures),
        rules=rules,
        max_repair=args.max_repair,
        concurrency=args.concurrency,
        delay=args.delay,
    )
    results = pipeline.run(topics)
    output = write_results(args.input, results, args.output, args.sheet)

    counts = {"ok": 0, "repaired": 0, "failed": 0}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
        flag = "✓" if result.status in ("ok", "repaired") else "✗"
        print(
            f"{flag} 第 {result.topic.row} 行 {result.topic.keyword} "
            f"[{result.status}] 尝试 {result.attempts} 次"
        )
        for issue in result.issues:
            print(f"    - {issue}")
        if result.error:
            print(f"    - {result.error}")

    print(
        f"\n完成：通过 {counts['ok']}，修复后通过 {counts['repaired']}，失败 {counts['failed']}"
    )
    print(f"结果已写入：{output.resolve()}")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
