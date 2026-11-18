import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

from src.excel_io import read_topics, write_results
from src.pipeline import ContentPipeline
from src.providers.mock import MockProvider


class ExcelRoundTripTest(unittest.TestCase):
    def test_read_generate_and_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "topics.xlsx"
            output_path = Path(tmp) / "result.xlsx"

            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["关键词", "公司"])
            sheet.append(["playwright 自动化测试", "示例公司"])
            sheet.append(["SEO 内容优化", "另一家公司"])
            sheet.append([None, "空行应被跳过"])
            workbook.save(input_path)

            topics = read_topics(input_path)
            self.assertEqual([topic.row for topic in topics], [2, 3])
            self.assertEqual(topics[0].company, "示例公司")

            pipeline = ContentPipeline(MockProvider(), delay=0, concurrency=1)
            results = pipeline.run(topics)
            write_results(input_path, results, output_path)

            output = load_workbook(output_path)
            ws = output.active
            headers = [cell.value for cell in ws[1]]
            self.assertIn("状态", headers)
            status_col = headers.index("状态") + 1
            title_col = headers.index("标题") + 1
            body_col = headers.index("正文") + 1

            self.assertEqual(ws.cell(row=2, column=status_col).value, "ok")
            self.assertIn("playwright", ws.cell(row=2, column=title_col).value)
            self.assertGreater(len(ws.cell(row=2, column=body_col).value), 2000)
            self.assertEqual(ws.cell(row=3, column=status_col).value, "ok")
            self.assertEqual(ws.cell(row=4, column=status_col).value, None)
            output.close()


if __name__ == "__main__":
    unittest.main()
