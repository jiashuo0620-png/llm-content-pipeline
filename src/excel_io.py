"""Excel 读写：按表头定位输入列，处理结果回填到原表副本。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .models import RowResult, Topic

KEYWORD_ALIASES = ("关键词", "核心词", "keyword")
COMPANY_ALIASES = ("公司", "公司名称", "品牌", "company")
OUTPUT_HEADERS = ("状态", "尝试次数", "标题", "描述", "正文", "校验问题")


def _normalize(value: object) -> str:
    return str(value or "").strip().lower()


def _find_column(headers: Sequence[str], aliases: Sequence[str], required: bool, name: str) -> int:
    lowered = [_normalize(item) for item in headers]
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered.index(alias.lower())
    if required:
        raise ValueError(f"表头中找不到「{name}」列，当前表头：{list(headers)}")
    return -1


def read_topics(path: str | Path, sheet: str | None = None) -> List[Topic]:
    workbook = load_workbook(path, data_only=True)
    worksheet = workbook[sheet] if sheet else workbook.active
    headers = [cell.value for cell in worksheet[1]]
    keyword_col = _find_column(headers, KEYWORD_ALIASES, True, "关键词")
    company_col = _find_column(headers, COMPANY_ALIASES, False, "公司")

    topics: List[Topic] = []
    for row_index, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
        keyword = str(row[keyword_col] or "").strip() if keyword_col < len(row) else ""
        if not keyword:
            continue
        company = ""
        if company_col >= 0 and company_col < len(row):
            company = str(row[company_col] or "").strip()
        topics.append(Topic(row=row_index, keyword=keyword, company=company))
    workbook.close()
    return topics


def write_results(
    input_path: str | Path,
    results: List[RowResult],
    output_path: str | Path,
    sheet: str | None = None,
) -> Path:
    workbook = load_workbook(input_path)
    worksheet = workbook[sheet] if sheet else workbook.active

    headers = [cell.value for cell in worksheet[1]]
    column_index: Dict[str, int] = {}
    for name in OUTPUT_HEADERS:
        if name in headers:
            column_index[name] = headers.index(name) + 1
        else:
            column_index[name] = worksheet.max_column + 1
            worksheet.cell(row=1, column=column_index[name], value=name)
            headers.append(name)

    header_font = Font(bold=True)
    for name in OUTPUT_HEADERS:
        worksheet.cell(row=1, column=column_index[name]).font = header_font

    for result in results:
        row = result.topic.row
        content = result.content
        values = {
            "状态": result.status,
            "尝试次数": result.attempts,
            "标题": content.title if content else "",
            "描述": "\n".join(content.descriptions) if content else "",
            "正文": content.body if content else "",
            "校验问题": result.error or "\n".join(str(issue) for issue in result.issues),
        }
        for name, value in values.items():
            cell = worksheet.cell(row=row, column=column_index[name], value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    widths = {"标题": 32, "描述": 48, "正文": 70, "校验问题": 40}
    for name, width in widths.items():
        worksheet.column_dimensions[get_column_letter(column_index[name])].width = width

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    workbook.close()
    return output
