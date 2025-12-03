# Task 4: 添加 Paper 2 占位

## 目标

创建 `paper2_app` 作为 Paper 2 (SAGE-Agent) 的预留入口。

## 实现代码

```python
# Paper 2: SAGE-Agent 方法 (Coming Soon)
paper2_app = typer.Typer(
    name="paper2",
    help="📝 Paper 2: SAGE-Agent - Streaming Adaptive Learning",
    no_args_is_help=False,  # 允许无子命令调用
)


@paper2_app.callback(invoke_without_command=True)
def paper2_info(ctx: typer.Context):
    """显示 Paper 2 信息"""
    if ctx.invoked_subcommand is None:
        console.print("\n[bold cyan]📝 Paper 2: SAGE-Agent[/bold cyan]")
        console.print("[dim]Streaming Adaptive Learning for Agent Tool Selection[/dim]\n")

        console.print("[yellow]🚧 Status: Work in Progress[/yellow]\n")

        console.print("[bold]Paper 2 将包含:[/bold]")
        console.print("  • SIAS (Streaming Incremental Adaptive Selection) 方法")
        console.print("  • 在线学习与增量更新策略")
        console.print("  • 与 Paper 1 Benchmark 的对比实验")
        console.print()

        console.print("[dim]Related code location:[/dim]")
        console.print("  packages/sage-libs/src/sage/libs/sias/")
        console.print("  packages/sage-benchmark/src/sage/benchmark/benchmark_agent/")
        console.print()

        console.print("[dim]Stay tuned for updates...[/dim]")


# 预留一些基本命令
@paper2_app.command("status")
def paper2_status():
    """查看 Paper 2 实现状态"""
    console.print("\n[bold]Paper 2 Implementation Status[/bold]\n")

    components = [
        ("SIAS Core Algorithm", "🚧 In Progress", "sage.libs.sias"),
        ("Streaming Data Handler", "✅ Done", "sage.libs.sias.streaming"),
        ("Benchmark Integration", "📋 Planned", "sage.benchmark.benchmark_agent"),
        ("CLI Commands", "📋 Planned", "sage.cli.commands.apps.bench"),
    ]

    table = Table(show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Location", style="dim")

    for comp, status, loc in components:
        table.add_row(comp, status, loc)

    console.print(table)
```

## 注册到 agent_app

```python
agent_app.add_typer(paper2_app, name="paper2")
```

## 文件位置

`/home/shuhao/SAGE/packages/sage-cli/src/sage/cli/commands/apps/bench.py`

## 验证命令

```bash
sage bench agent paper2
sage bench agent paper2 status
sage bench agent paper2 --help
```

## 预期输出

```
$ sage bench agent paper2

📝 Paper 2: SAGE-Agent
Streaming Adaptive Learning for Agent Tool Selection

🚧 Status: Work in Progress

Paper 2 将包含:
  • SIAS (Streaming Incremental Adaptive Selection) 方法
  • 在线学习与增量更新策略
  • 与 Paper 1 Benchmark 的对比实验

Related code location:
  packages/sage-libs/src/sage/libs/sias/
  packages/sage-benchmark/src/sage/benchmark/benchmark_agent/

Stay tuned for updates...
```

## 注意事项

- 使用 `invoke_without_command=True` 允许直接调用 `sage bench agent paper2`
- 提供有意义的信息而不是简单的 "Coming Soon"
- 预留 `status` 命令查看实现进度
