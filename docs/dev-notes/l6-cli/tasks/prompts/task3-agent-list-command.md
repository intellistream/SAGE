# Task 3: 添加 agent list 命令

## 目标

在 `agent_app` 添加 `list` 命令，列出所有可用的 Agent Benchmark papers。

## 预期输出

```bash
$ sage bench agent list

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📚 Available Agent Benchmarks                              ┃
┣━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┫
┃ Paper   ┃ Description                             ┃ Status┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ paper1  │ SAGE-Bench - Agent 能力评测框架           │ ✅    │
│         │ 工具选择/任务规划/时机判断评测              │       │
├─────────┼──────────────────────────────────────────┼───────┤
│ paper2  │ SAGE-Agent - Streaming Adaptive Learning│ 🚧    │
│         │ 流式自适应学习方法                        │       │
└─────────┴──────────────────────────────────────────┴───────┘

Usage:
  sage bench agent paper1 run --quick    # 运行 Paper 1 实验
  sage bench agent paper2                # 查看 Paper 2 状态
```

## 实现代码

```python
@agent_app.command("list")
def list_agent_papers():
    """列出所有 Agent Benchmark papers"""
    table = Table(title="📚 Available Agent Benchmarks", show_header=True)
    table.add_column("Paper", style="cyan", width=10)
    table.add_column("Description", width=45)
    table.add_column("Status", style="green", width=8)

    papers = [
        ("paper1", "SAGE-Bench - Agent 能力评测框架\n工具选择/任务规划/时机判断评测", "✅ Ready"),
        ("paper2", "SAGE-Agent - Streaming Adaptive Learning\n流式自适应学习方法", "🚧 WIP"),
    ]

    for paper, desc, status in papers:
        table.add_row(paper, desc, status)

    console.print(table)
    console.print("\n[dim]Usage:[/dim]")
    console.print("  sage bench agent paper1 run --quick")
    console.print("  sage bench agent paper2")
```

## 文件位置

`/home/shuhao/SAGE/packages/sage-cli/src/sage/cli/commands/apps/bench.py`

## 验证命令

```bash
sage bench agent list
sage bench agent --help  # 应显示 list 命令
```

## 注意事项

- 使用 Rich Table 格式化输出
- Status 列用 emoji 表示状态
- 添加 Usage 示例帮助用户
