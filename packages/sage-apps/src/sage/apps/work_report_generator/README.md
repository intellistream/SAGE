# Work Report Generator

基于 SAGE 框架的周报/日报自动生成器。

## 功能特性

- **GitHub 数据获取**: 自动获取指定仓库和分支的 commits 和 Pull Requests
- **子模块支持**: 默认收集 SAGE 主仓库及所有子模块的贡献
- **贡献者统计**: 按贡献者聚合统计数据
- **AI 摘要生成**: 使用 LLM 生成智能工作总结
- **多种输出格式**: 支持 Markdown、JSON、Console 输出
- **日记集成**: 可选集成个人工作日志
- **CI/CD 集成**: 支持自动化定时生成（每周一 17:00 北京时间）

## 快速开始

### 安装

```bash
# 安装 sage-apps
pip install -e packages/sage-apps
```

### 基本使用

```python
from sage.apps.work_report_generator import run_work_report_pipeline

# 生成默认报告（所有 SAGE 仓库，main-dev 分支，过去7天）
run_work_report_pipeline()

# 自定义配置
run_work_report_pipeline(
    repos=["intellistream/SAGE", "intellistream/sageLLM"],
    branch="main-dev",  # 指定分支
    days=14,
    output_format="markdown",
    output_path="reports/biweekly_report.md",
    language="zh",  # 中文报告
    include_submodules=False,  # 仅指定仓库，不包含子模块
)
```

### 命令行使用

```bash
# 基本使用（收集所有 SAGE 仓库 main-dev 分支的贡献）
python -m sage.apps.work_report_generator.pipeline

# 仅主仓库，不包含子模块
python -m sage.apps.work_report_generator.pipeline --no-submodules

# 指定分支（如 main 而非 main-dev）
python -m sage.apps.work_report_generator.pipeline --branch main

# 指定仓库和时间范围
python -m sage.apps.work_report_generator.pipeline \
    --repos intellistream/SAGE,intellistream/sageLLM \
    --days 14

# JSON 格式输出
python -m sage.apps.work_report_generator.pipeline \
    --format json \
    --output reports/weekly.json

# 英文报告，不使用 LLM
python -m sage.apps.work_report_generator.pipeline \
    --language en \
    --no-llm
```

### 示例脚本

```bash
python examples/apps/run_work_report.py --help
python examples/apps/run_work_report.py --days 7
```

## 默认仓库列表

当不指定 `repos` 参数时，pipeline 默认收集以下所有仓库的贡献：

| 仓库                     | 说明               |
| ------------------------ | ------------------ |
| `intellistream/SAGE`     | 主仓库             |
| `intellistream/SAGE-Pub` | 文档 (docs-public) |
| `intellistream/sageData` | Benchmark 数据     |
| `intellistream/sageLLM`  | LLM 调度模块       |
| `intellistream/LibAMM`   | 近似矩阵乘法库     |
| `intellistream/sageDB`   | 数据库中间件       |
| `intellistream/sageFlow` | 流处理引擎         |
| `intellistream/neuromem` | 内存管理模块       |
| `intellistream/sageTSDB` | 时序数据库         |

## 配置选项

| 参数                 | 类型      | 默认值     | 说明                                     |
| -------------------- | --------- | ---------- | ---------------------------------------- |
| `repos`              | list[str] | None       | GitHub 仓库列表，None 表示所有 SAGE 仓库 |
| `branch`             | str       | "main-dev" | 目标分支名称                             |
| `days`               | int       | 7          | 统计天数                                 |
| `output_format`      | str       | "markdown" | 输出格式 (console/markdown/json)         |
| `output_path`        | str       | None       | 输出文件路径                             |
| `diary_path`         | str       | None       | 日记文件/目录路径                        |
| `language`           | str       | "zh"       | 报告语言 (zh/en)                         |
| `github_token`       | str       | None       | GitHub Token (可用环境变量)              |
| `use_llm`            | bool      | True       | 是否使用 LLM 生成摘要                    |
| `include_submodules` | bool      | True       | 是否包含子模块仓库                       |

## 环境变量

```bash
# GitHub Token (必需，用于 API 访问)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# 或使用 GIT_TOKEN
export GIT_TOKEN=ghp_xxxxxxxxxxxx
```

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     Work Report Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│  GitHubDataSource ──┬──► ContributorAggregator                  │
│  (main-dev branch)  │              │                             │
│  - SAGE             │              ▼                             │
│  - sageLLM          │     LLMReportGenerator                    │
│  - sageDB           │              │                             │
│  - sageFlow         │              ▼                             │
│  - neuromem         │        ReportSink                         │
│  - sageTSDB         │     (md/json/console)                     │
│  - SAGE-docs        │                                           │
│  - SAGE-data        │                                           │
│  - libamm           │                                           │
└─────────────────────────────────────────────────────────────────┘
```

│ DiaryEntrySource ──┘ ▼ │ │ LLMReportGenerator (Optional) │ │ │ │ │ ▼ │ │ ReportSink │ │ (Console /
Markdown / JSON) │ └─────────────────────────────────────────────────────────────────┘

````

### 核心组件

| 组件 | 类型 | 功能 |
|------|------|------|
| `GitHubDataSource` | BatchFunction | 从 GitHub 获取 commits 和 PRs |
| `DiaryEntrySource` | BatchFunction | 加载本地日记文件 |
| `ContributorAggregator` | MapFunction | 按贡献者聚合数据 |
| `LLMReportGenerator` | MapFunction | 使用 LLM 生成摘要 |
| `ReportSink` | SinkFunction | 输出最终报告 |

## 输出示例

### Markdown 格式

```markdown
# Weekly Work Report

**Period:** 2024-01-08 ~ 2024-01-15
**Repositories:** intellistream/SAGE

## Summary

- Total Commits: 42
- Total PRs: 8 (6 merged)

## Contributors

### developer1

- **Commits:** 15
- **PRs:** 3 (merged: 2)
- **Lines Changed:** +1500 / -300

**AI Summary:**
> developer1 本周主要完成了周报生成器的核心功能实现...
````

### JSON 格式

```json
{
  "start_date": "2024-01-08",
  "end_date": "2024-01-15",
  "repos": ["intellistream/SAGE"],
  "summary": {
    "total_commits": 42,
    "total_prs": 8,
    "total_merged_prs": 6
  },
  "contributors": [
    {
      "username": "developer1",
      "stats": {
        "commits": 15,
        "prs": 3,
        "merged_prs": 2
      },
      "llm_summary": "..."
    }
  ]
}
```

## CI/CD 集成

### GitHub Actions (Weekly Schedule)

参见 `.github/workflows/weekly-report.yml`:

```yaml
name: Weekly Report Generator
on:
  schedule:
    - cron: '0 9 * * 1'  # 每周一 9:00 UTC
  workflow_dispatch:

jobs:
  generate-report:
    runs-on: [self-hosted, A6000]
    steps:
      - uses: actions/checkout@v4
      - name: Generate Report
        run: |
          python -m sage.apps.work_report_generator.pipeline \
            --repos intellistream/SAGE \
            --days 7 \
            --format markdown \
            --output reports/weekly_$(date +%Y%m%d).md
        env:
          GITHUB_TOKEN: ${{ secrets.GIT_TOKEN }}
```

## 日记格式

### JSON 格式

```json
[
  {
    "date": "2024-01-15",
    "author": "developer1",
    "content": "今天完成了周报生成器的开发...",
    "tags": ["development", "feature"],
    "category": "work"
  }
]
```

### Markdown 格式

文件名格式: `YYYY-MM-DD.md`

```markdown
# 2024-01-15 工作日志

今天主要完成了以下工作：
- 实现了 GitHub 数据获取模块
- 添加了 LLM 摘要生成功能
```

## 开发

### 运行测试

```bash
pytest packages/sage-apps/tests/unit/test_work_report_generator/ -v
```

### 代码结构

```
packages/sage-apps/src/sage/apps/work_report_generator/
├── __init__.py          # 模块入口
├── models.py            # 数据模型
├── operators.py         # SAGE 算子
├── pipeline.py          # 管道实现
└── README.md            # 文档
```

## 许可证

Apache License 2.0
