# LLM Content Pipeline

> 批量把关键词变成可用稿件：LLM 生成 → 硬规则校验 → 自动返修 → Excel 回填。

## 背景

用大模型批量写稿，最麻烦的不是「生成」，而是「验收」：标题超长、描述条数不够、正文篇幅忽长忽短、偶尔冒出违禁词，几十条内容靠人眼逐条检查，比手写还累。

这个工具把验收标准固化成可执行的规则，生成结果不合格就带着问题清单让模型返修，仍然不合格就标记失败——人能拿到一张可以直接看的 Excel，而不是一堆需要重读的文本。

## 功能

- **批量处理**：读取 Excel 主题表，一次跑完整批
- **结构化输出**：强制模型返回 `title / descriptions / body` 的 JSON，兼容代码块与前后废话
- **硬规则校验**：标题长度、描述条数与字数、正文篇幅与段落数、核心词、违禁词、占位符、重复描述
- **自动返修**：校验不通过时把问题清单回传模型重写，可配置最大次数
- **失败隔离**：单行异常不影响整批，失败原因写入结果表
- **并发 + 限速**：线程池提速度，跨线程最小间隔控制请求频率
- **Excel 回填**：保留原表所有列，追加状态、标题、描述、正文、校验问题
- **离线可跑**：内置 Mock 提供方与回放数据，没有 API Key 也能演示完整流程
- **可插拔模型**：OpenAI 兼容接口，换 DeepSeek / 通义 / 本地 vLLM 只改环境变量

## 技术栈

Python 3.9+ / requests / openpyxl / concurrent.futures / unittest

## 快速开始

```bash
pip install -r requirements.txt

# 离线演示：无需联网，第 1 行会故意返回不合格内容，演示「校验 → 返修 → 通过」
python main.py --input data/topics.example.xlsx --provider mock --output outputs/result.xlsx

# 接入真实模型（任意 OpenAI 兼容端点）
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_API_KEY=sk-xxx
export LLM_MODEL=deepseek-chat
python main.py --input data/topics.example.xlsx --provider openai --output outputs/result.xlsx
```

## 输入格式

`data/topics.example.xlsx`（首个工作表，第 1 行为表头）：

| 关键词 | 公司 |
|---|---|
| playwright 自动化测试 | 示例科技 |
| SEO 内容优化 | 示例科技 |

「关键词」列必填，「公司」列可选；空行自动跳过。

## 输出示例

原表基础上追加以下列：

| 状态 | 尝试次数 | 标题 | 描述 | 正文 | 校验问题 |
|---|---|---|---|---|---|
| repaired | 2 | playwright 自动化测试实战指南… | 围绕…（3 条，换行分隔） | 4 段正文 | |
| failed | 3 | | | | [body] 正文 1200 字，少于 2000 字 |

状态含义：`ok` 一次通过，`repaired` 返修后通过，`failed` 达到最大返修次数仍未通过。

## 命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--input` | 输入 Excel 路径 | 必填 |
| `--output` | 输出 Excel 路径 | `outputs/result.xlsx` |
| `--provider` | 模型提供方：`mock` / `openai` | `mock` |
| `--fixtures` | Mock 回放数据路径 | `data/fixtures.json` |
| `--sheet` | 工作表名称 | 第一个工作表 |
| `--max-repair` | 最大返修次数 | 2 |
| `--concurrency` | 并发数 | 3 |
| `--delay` | 每次请求最小间隔（秒） | 0.5 |
| `--limit` | 只处理前 N 行 | 0（全部） |
| `--body-min` / `--body-max` | 正文篇幅范围 | 2000 / 3000 |

## 测试

```bash
python -m unittest discover -s tests -v
```

14 个用例覆盖：规则校验（标题/描述/正文/违禁词/占位符/重复）、JSON 提取、返修闭环、失败上限、接口异常、Excel 读写回填。

## 设计要点

1. **验收规则与生成解耦**：`ContentRules` 是一组可调参数，换业务只改规则，不动流水线
2. **返修带证据**：回炉时把「上一版 JSON + 具体问题清单」一起给模型，而不是简单重试
3. **失败可解释**：每一行都记录状态、尝试次数和未通过的问题，方便人工接手
4. **Mock 也是测试夹具**：`fixtures.json` 按关键词回放预设响应，让返修路径可以离线复现
5. **线程安全限速**：锁内只计算等待时长，锁外 sleep，避免并发退化成串行

## 目录结构

```
.
├── data/
│   ├── topics.example.xlsx   # 示例输入
│   └── fixtures.json         # Mock 回放数据（含一次不合格响应）
├── src/
│   ├── excel_io.py           # 读主题、回填结果
│   ├── models.py             # 数据结构
│   ├── pipeline.py           # 生成 → 校验 → 返修编排
│   ├── prompt.py             # Prompt 与返修模板
│   ├── validator.py          # 硬规则校验
│   └── providers/            # Mock / OpenAI 兼容适配器
├── tests/
└── main.py
```

## 说明

- `mock` 模式完全离线，克隆即可运行
- 使用真实模型时请控制并发与频率，遵守服务商的使用条款
- 密钥通过环境变量传入，不要写进代码或提交到仓库
