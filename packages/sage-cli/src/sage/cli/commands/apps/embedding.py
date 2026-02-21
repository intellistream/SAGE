"""
Embedding CLI 命令

提供命令行工具来管理和测试 embedding 方法。
"""

import subprocess
import sys
from importlib.util import find_spec

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sage.common.components.sage_embedding import (
    check_model_availability,
    get_embedding_model,
    list_embedding_models,
)
from sage.common.config.ports import SagePorts

console = Console()
app = typer.Typer(name="embedding", help="🎯 Embedding 方法管理")


@app.command(name="list")
def list_methods(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="输出格式 (table/json/simple)",
    ),
    api_key_only: bool = typer.Option(
        False,
        "--api-key-only",
        help="仅显示需要 API Key 的方法",
    ),
    no_api_key: bool = typer.Option(
        False,
        "--no-api-key",
        help="仅显示不需要 API Key 的方法",
    ),
):
    """列出所有可用的 embedding 方法"""
    models = list_embedding_models()

    # 过滤
    if api_key_only:
        models = {k: v for k, v in models.items() if v["requires_api_key"]}
    elif no_api_key:
        models = {k: v for k, v in models.items() if not v["requires_api_key"]}

    if format == "json":
        import json

        console.print_json(json.dumps(models, indent=2, ensure_ascii=False))
        return

    if format == "simple":
        for method in models.keys():
            console.print(method)
        return

    # Table 格式
    table = Table(
        title="🎯 SAGE Embedding 方法",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("方法", style="green", width=18)
    table.add_column("显示名称", style="cyan", width=25)
    table.add_column("状态", width=15)
    table.add_column("默认维度", justify="right", width=10)
    table.add_column("示例模型", style="dim", width=40)

    for method, info in sorted(models.items()):
        # 状态标签
        status_parts = []
        if info["requires_api_key"]:
            status_parts.append("🔑 API Key")
        else:
            status_parts.append("🔓 免费")

        if info["requires_download"]:
            status_parts.append("📥 下载")
        else:
            status_parts.append("☁️ 云端")

        status = "\n".join(status_parts)

        # 示例模型
        examples = info.get("examples", [])
        example_str = "\n".join(examples[:2]) if examples else "N/A"

        # 默认维度
        dim = str(info.get("default_dimension", "动态"))

        table.add_row(
            method,
            info["display_name"],
            status,
            dim,
            example_str,
        )

    console.print(table)
    console.print(f"\n💡 总计: {len(models)} 个方法")


@app.command(name="check")
def check_method(
    method: str = typer.Argument(..., help="Embedding 方法名称"),
    model: str | None = typer.Option(None, "--model", "-m", help="模型名称（如果需要）"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """检查特定 embedding 方法的可用性"""
    kwargs: dict[str, object] = {}
    if model:
        kwargs["model"] = model

    result = check_model_availability(method, **kwargs)

    # 状态图标
    status_icons = {
        "available": "✅",
        "cached": "✅",
        "needs_api_key": "⚠️",
        "needs_download": "⚠️",
        "unavailable": "❌",
    }
    icon = status_icons.get(result["status"], "❓")

    # 构建面板内容
    content = f"{icon} **状态:** {result['status']}\n\n"
    content += f"📝 **消息:** {result['message']}\n\n"
    content += f"💡 **操作:** {result['action']}"

    if verbose:
        # 添加更多信息
        models = list_embedding_models()
        if method in models:
            info = models[method]
            content += "\n\n---\n\n"
            content += f"📦 **显示名称:** {info['display_name']}\n\n"
            content += f"📄 **描述:** {info['description']}\n\n"
            if info.get("examples"):
                content += "📋 **示例模型:**\n"
                for ex in info["examples"][:3]:
                    content += f"  - {ex}\n"

    panel = Panel(
        content,
        title=f"[bold cyan]{method}[/bold cyan] 可用性检查",
        border_style="cyan",
        padding=(1, 2),
    )

    console.print(panel)


@app.command(name="test")
def test_method(
    method: str = typer.Argument(..., help="Embedding 方法名称"),
    text: str = typer.Option("Hello, world!", "--text", "-t", help="测试文本"),
    model: str | None = typer.Option(None, "--model", "-m", help="模型名称"),
    api_key: str | None = typer.Option(None, "--api-key", "-k", help="API 密钥"),
    show_vector: bool = typer.Option(False, "--show-vector", "-s", help="显示向量内容"),
    dimension: int | None = typer.Option(
        None, "--dimension", "--dim", "-d", help="向量维度（部分方法支持）"
    ),
):
    """测试 embedding 方法"""
    console.print(f"[cyan]测试方法:[/cyan] {method}")
    console.print(f"[cyan]测试文本:[/cyan] {text}\n")

    # 构建参数
    kwargs: dict[str, object] = {}
    if model:
        kwargs["model"] = model
    if api_key:
        kwargs["api_key"] = api_key
    if dimension:
        kwargs["dim"] = dimension
        kwargs["dimensions"] = dimension  # Jina 使用 dimensions

    try:
        with console.status("[bold green]生成 embedding...", spinner="dots"):
            emb = get_embedding_model(method, **kwargs)
            vec = emb.embed(text)

        # 显示结果
        console.print("[green]✅ 成功![/green]\n")

        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("属性", style="cyan", width=15)
        table.add_column("值", style="green")

        table.add_row("Wrapper", str(emb))
        table.add_row("向量维度", str(len(vec)))
        table.add_row("向量范数", f"{sum(x * x for x in vec) ** 0.5:.6f}")

        if show_vector:
            vec_preview = str(vec[:10])[:-1] + ", ...]" if len(vec) > 10 else str(vec)
            table.add_row("向量内容", vec_preview)

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ 错误:[/red] {e}")
        if "API Key" in str(e):
            console.print("\n[yellow]💡 提示:[/yellow] 使用 --api-key 参数提供 API 密钥")


@app.command(name="start")
def start_server(
    model: str = typer.Option(
        "BAAI/bge-m3",
        "--model",
        "-m",
        help="HuggingFace 模型名称",
    ),
    port: int = typer.Option(
        SagePorts.EMBEDDING_DEFAULT,
        "--port",
        "-p",
        help=f"服务器端口 (默认 {SagePorts.EMBEDDING_DEFAULT})",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="服务器地址",
    ),
    device: str = typer.Option(
        "auto",
        "--device",
        "-d",
        help="设备类型 (cuda/cpu/auto)",
    ),
    gpu: int | None = typer.Option(
        None,
        "--gpu",
        "-g",
        help="指定 GPU ID (例如: 0, 1, 2)",
    ),
    workers: int = typer.Option(
        1,
        "--workers",
        "-w",
        help="Worker 数量",
    ),
):
    """启动 Embedding 服务器 (OpenAI 兼容 API)

    启动一个 OpenAI 兼容的 Embedding 服务器，提供以下端点：

    - GET  /health              - 健康检查
    - GET  /v1/models           - 列出模型
    - POST /v1/embeddings       - 生成 embeddings

    示例：

        # 启动默认服务器 (BGE-M3, 端口 8090)
        sage embedding start

        # 使用自定义模型和端口
        sage embedding start --model BAAI/bge-small-zh-v1.5 --port 8080

        # 使用 CPU
        sage embedding start --device cpu

        # 使用特定 GPU
        sage embedding start --gpu 0

    测试命令：

        curl -X POST http://localhost:8090/v1/embeddings \\
          -H "Content-Type: application/json" \\
          -d '{"input": "Hello world", "model": "BAAI/bge-m3"}'
    """
    if find_spec("sage.common.components.sage_embedding.embedding_server") is None:
        console.print("[red]❌ 未找到 embedding_server 模块[/red]")
        console.print("   请确认 isage-common 安装正常")
        raise typer.Exit(1)

    # 构建启动命令（模块方式，兼容打包环境）
    cmd = [
        sys.executable,
        "-m",
        "sage.common.components.sage_embedding.embedding_server",
        "--model",
        model,
        "--port",
        str(port),
        "--host",
        host,
        "--device",
        device,
        "--workers",
        str(workers),
    ]

    if gpu is not None:
        cmd.extend(["--gpu", str(gpu)])

    # 显示启动信息
    panel = Panel(
        f"""[bold cyan]Embedding 服务器配置[/bold cyan]

📦 [cyan]模型:[/cyan] {model}
🌐 [cyan]地址:[/cyan] http://{host}:{port}
🖥️  [cyan]设备:[/cyan] {device}{f" (GPU {gpu})" if gpu is not None else ""}
👷 [cyan]Workers:[/cyan] {workers}

[dim]API 端点:[/dim]
  • [green]GET[/green]  http://localhost:{port}/health
  • [green]GET[/green]  http://localhost:{port}/v1/models
  • [green]POST[/green] http://localhost:{port}/v1/embeddings

[yellow]按 Ctrl+C 停止服务器[/yellow]
""",
        title="🚀 启动 Embedding 服务器",
        border_style="green",
        padding=(1, 2),
    )

    console.print(panel)
    console.print()

    try:
        # 启动服务器（阻塞模式）
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  服务器已停止[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]❌ 服务器启动失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="benchmark")
def benchmark_methods(
    methods: list[str] = typer.Argument(None, help="要测试的方法列表"),
    text: str = typer.Option("Hello, world!", "--text", "-t", help="测试文本"),
    count: int = typer.Option(10, "--count", "-c", help="重复次数"),
):
    """对比多个 embedding 方法的性能"""
    import time

    if not methods:
        methods = ["hash", "mockembedder"]
        console.print("[yellow]未指定方法，使用默认方法: hash, mockembedder[/yellow]\n")

    console.print(f"[cyan]测试文本:[/cyan] {text}")
    console.print(f"[cyan]重复次数:[/cyan] {count}\n")

    results = []

    for method in methods:
        try:
            emb = get_embedding_model(method, dim=384)

            # 预热
            emb.embed(text)

            # 计时
            start = time.time()
            for _ in range(count):
                emb.embed(text)
            elapsed = time.time() - start

            avg_time = elapsed / count * 1000  # ms
            results.append((method, avg_time, len(emb.embed(text))))

        except Exception as e:
            console.print(f"[red]❌ {method} 失败:[/red] {e}")
            continue

    if not results:
        console.print("[red]没有成功的测试[/red]")
        return

    # 显示结果
    table = Table(
        title="⚡ 性能对比",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("方法", style="green")
    table.add_column("平均耗时", justify="right", style="yellow")
    table.add_column("维度", justify="right")
    table.add_column("性能", justify="center")

    # 找到最快的
    fastest = min(results, key=lambda x: x[1])

    for method, avg_time, dim in sorted(results, key=lambda x: x[1]):
        # 性能条
        ratio = avg_time / fastest[1]
        bar_len = int(ratio * 10)
        bar = "█" * bar_len

        table.add_row(
            method,
            f"{avg_time:.2f} ms",
            str(dim),
            bar + f" {ratio:.1f}x",
        )

    console.print(table)


# 导出
__all__ = ["app"]
