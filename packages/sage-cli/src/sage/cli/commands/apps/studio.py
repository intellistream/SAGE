"""SAGE Studio CLI - Studio Web 界面管理命令"""

import typer
from rich.console import Console

# Use ChatModeManager (with LLM support) as the default manager
from sage.studio.chat_manager import ChatModeManager

console = Console()
app = typer.Typer(help="SAGE Studio - 图形化界面管理工具")

# Create ChatModeManager instance (replaces old StudioManager)
studio_manager = ChatModeManager()


@app.command()
def start(
    port: int | None = typer.Option(None, "--port", "-p", help="指定端口"),
    host: str = typer.Option("localhost", "--host", "-h", help="指定主机"),
    dev: bool = typer.Option(True, "--dev/--prod", help="开发模式（默认）或生产模式"),
    gateway_port: int | None = typer.Option(
        None, "--gateway-port", help="指定 Gateway 端口（默认 8889，若被占用将自动切到 8899）"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="自动确认所有提示（用于 CI/CD 或脚本）"),
    no_gateway: bool = typer.Option(False, "--no-gateway", help="不自动启动 Gateway"),
    no_auto_install: bool = typer.Option(
        False, "--no-auto-install", help="禁用自动安装依赖（如缺少依赖会提示失败）"
    ),
    no_auto_build: bool = typer.Option(
        False, "--no-auto-build", help="禁用自动构建（生产模式下如缺少构建会提示失败）"
    ),
    no_llm: bool = typer.Option(False, "--no-llm", help="禁用本地 LLM 服务（默认启动 sageLLM）"),
    no_embedding: bool = typer.Option(
        False, "--no-embedding", help="禁用本地 Embedding 服务（用于无 GPU 的 CI/CD 环境）"
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="指定模型（默认: Qwen/Qwen2.5-0.5B-Instruct - 超小模型）",
    ),
    use_finetuned: bool = typer.Option(
        False,
        "--use-finetuned",
        help="🎓 使用最新的微调模型（如果可用）",
    ),
    list_finetuned: bool = typer.Option(
        False,
        "--list-finetuned",
        help="📋 列出可用的微调模型",
    ),
):
    """启动 SAGE Studio（默认启动本地 LLM）

    自动化功能（可通过选项禁用）：
    - 自动启动 Gateway 服务（如未运行）
    - 自动启动本地 LLM 服务（通过 sageLLM，使用 0.5B 小模型）
    - 自动下载模型（从 HuggingFace，缓存到 ~/.sage/models/vllm/）
    - 自动安装前端依赖（如缺少 node_modules）
    - 自动构建生产包（如生产模式且缺少构建输出）

    模型管理：
    - 默认模型 Qwen2.5-0.5B-Instruct 非常小（~300MB），适合快速启动
    - 首次使用会从 HuggingFace 自动下载，后续使用本地缓存
    - 模型缓存位置：~/.sage/models/vllm/<model-id>/
    - 使用 'sage llm model show' 查看已缓存模型
    - 使用 'sage llm model download' 预下载模型

    微调模型集成：
    - 使用 --use-finetuned 自动使用最新的微调模型
    - 使用 --list-finetuned 查看所有可用的微调模型
    - 微调模型位置：~/.sage/studio_finetune/
    - 微调模型会自动被 sageLLM 识别和加载

    示例：
        sage studio start                          # 默认启动（含 0.5B 小模型）
        sage studio start --no-llm                 # 不启动 LLM
        sage studio start --llm-model Qwen/Qwen2.5-7B-Instruct  # 使用 7B 模型（首次会下载）
        sage studio start --use-finetuned         # 使用最新微调模型
        sage studio start --list-finetuned        # 列出可用微调模型

    环境变量：
        SAGE_STUDIO_LLM=true                       # 默认启用本地 LLM
        SAGE_STUDIO_LLM_MODEL=model_name           # 默认模型
        SAGE_STUDIO_LLM_GPU_MEMORY=0.9             # GPU 内存使用率
        SAGE_STUDIO_LLM_TENSOR_PARALLEL=1          # Tensor 并行度
        SAGE_LLM_MODEL_ROOT=~/.sage/models/llm     # 模型缓存位置

    所有自动操作都会先征求确认。
    """
    console.print("[blue]🚀 启动 SAGE Studio...[/blue]")

    try:
        # Handle --list-finetuned flag
        if list_finetuned:
            finetuned_models = studio_manager.list_finetuned_models()
            if not finetuned_models:
                console.print("[yellow]📋 暂无可用的微调模型[/yellow]")
                console.print("提示：使用 'sage finetune start' 开始微调任务")
                return

            console.print(f"\n[cyan]🎓 可用的微调模型 ({len(finetuned_models)}):[/cyan]\n")
            for i, model in enumerate(finetuned_models, 1):
                console.print(f"{i}. [green]{model['name']}[/green]")
                console.print(f"   类型: {model['type']}")
                console.print(f"   基础模型: {model['base_model']}")
                console.print(f"   路径: {model['path']}")
                console.print(f"   完成时间: {model['completed_at']}\n")

            console.print("[cyan]💡 使用方式：[/cyan]")
            console.print("  sage studio start --use-finetuned     # 使用最新微调模型")
            console.print(
                f'  sage studio start --llm-model "{finetuned_models[0]["path"]}"  # 指定特定模型'
            )
            return

        # 先检查是否已经在运行
        running_pid = studio_manager.is_running()
        if running_pid:
            # Check for orphan process (PID -1)
            if running_pid == -1:
                if yes:
                    console.print("[yellow]⚠️  检测到端口占用 (PID: -1)，尝试强制清理...[/yellow]")
                    # Use the internal method _kill_process_on_port
                    # We need to know the port. If port arg is None, use config or default.
                    target_port = port or studio_manager.load_config().get(
                        "port", studio_manager.default_port
                    )
                    studio_manager._kill_process_on_port(target_port)
                    # Re-check
                    if studio_manager.is_running():
                        console.print("[red]❌ 无法清理端口占用，请手动检查[/red]")
                        raise typer.Exit(code=1)
                else:
                    console.print("[yellow]⚠️  检测到端口占用 (PID: -1)[/yellow]")
                    console.print("[dim]   请运行 'sage studio stop' 或手动清理端口[/dim]")
                    raise typer.Exit(code=1)
            else:
                config = studio_manager.load_config()
                url = f"http://{config['host']}:{config['port']}"
                console.print(f"[green]✅ Studio 已经在运行中 (PID: {running_pid})[/green]")
                console.print(f"[blue]🌐 访问地址: {url}[/blue]")
                return

        # Start Studio with ChatModeManager (includes Gateway + LLM by default)
        # Pass llm=None to allow auto-detection (if no_llm is False)
        # Pass llm=False if user explicitly requested no_llm
        success = studio_manager.start(
            frontend_port=port,
            host=host,
            dev=dev,
            llm=False if no_llm else None,
            llm_model=llm_model,
            use_finetuned=use_finetuned,
            skip_confirm=yes,
            no_embedding=no_embedding,
            gateway_port=gateway_port,
        )

        if success:
            console.print("[green]✅ Studio 启动成功[/green]")
            console.print("\n[cyan]💡 提示：[/cyan]")
            if not no_llm:
                console.print("  • 本地 LLM 服务已通过 sageLLM 启动")
                console.print("  • UnifiedInferenceClient 将自动检测并使用")
                console.print("  • 使用 'sage studio status' 查看服务状态")
            console.print("  • Chat 模式需要 Gateway 服务支持")
            console.print("  • 使用 'sage studio stop' 停止服务")
        else:
            console.print("[red]❌ Studio 启动失败[/red]")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stop(
    all: bool = typer.Option(False, "--all", help="同时停止 LLM 和 Embedding 基础设施服务"),
):
    """停止 SAGE Studio（默认保留 LLM/Embedding 服务）

    默认只停止 Studio 前端和 Gateway。
    使用 --all 选项可同时停止 LLM 和 Embedding 服务。
    """
    console.print("[blue]🛑 停止 SAGE Studio...[/blue]")

    try:
        success = studio_manager.stop(stop_infrastructure=all)

        if success:
            console.print("[green]✅ Studio 已停止[/green]")
        else:
            console.print("[yellow]ℹ️ Studio 未运行或停止失败[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 停止失败: {e}[/red]")


@app.command()
def restart(
    port: int | None = typer.Option(None, "--port", "-p", help="指定端口"),
    host: str = typer.Option("localhost", "--host", "-h", help="指定主机"),
    dev: bool = typer.Option(True, "--dev/--prod", help="开发模式（默认）或生产模式"),
    clean: bool = typer.Option(True, "--clean/--no-clean", help="清理前端构建缓存（默认开启）"),
    no_llm: bool = typer.Option(False, "--no-llm", help="禁用本地 LLM 服务"),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="指定模型（默认: Qwen/Qwen2.5-0.5B-Instruct）",
    ),
    use_finetuned: bool = typer.Option(
        False,
        "--use-finetuned",
        help="🎓 使用最新的微调模型",
    ),
):
    """重启 SAGE Studio（包括 Gateway 和 LLM 服务）

    默认使用开发模式并清理前端构建缓存以确保使用最新代码。
    使用 --no-clean 可跳过清理步骤。
    使用 --prod 可使用生产模式（需要构建）。
    默认启动本地 LLM 服务，使用 --no-llm 可禁用。
    使用 --use-finetuned 可启动最新的微调模型。

    注意：重启会同时停止并重新启动所有服务，以确保加载最新的代码。
    """
    console.print("[blue]🔄 重启 SAGE Studio...[/blue]")

    try:
        # 先停止所有服务
        studio_manager.stop()

        # 清理前端缓存（如果启用）
        if clean:
            console.print("[yellow]🧹 清理前端构建缓存...[/yellow]")
            cleaned = studio_manager.clean_frontend_cache()
            if cleaned:
                console.print("[green]✅ 缓存清理完成[/green]")
            else:
                console.print("[yellow]⚠️ 缓存清理跳过（未找到缓存目录）[/yellow]")

        # 再启动
        success = studio_manager.start(
            frontend_port=port,
            host=host,
            dev=dev,
            llm=not no_llm,
            llm_model=llm_model,
            use_finetuned=use_finetuned,
        )

        if success:
            console.print("[green]✅ Studio 重启成功[/green]")
            if not no_llm:
                console.print("[green]🤖 本地 LLM 服务已通过 sageLLM 启动[/green]")
                if use_finetuned:
                    console.print("[green]🎓 使用微调模型[/green]")
        else:
            console.print("[red]❌ Studio 重启失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 重启失败: {e}[/red]")


@app.command()
def status():
    """查看 SAGE Studio 状态（包括 LLM 服务）"""
    console.print("[blue]📊 检查 SAGE Studio 状态...[/blue]")

    try:
        studio_manager.status()
    except Exception as e:
        console.print(f"[red]❌ 状态检查失败: {e}[/red]")


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="跟踪日志"),
    backend: bool = typer.Option(False, "--backend", "-b", help="查看后端API日志"),
    gateway: bool = typer.Option(False, "--gateway", "-g", help="查看 Gateway 日志"),
):
    """查看 SAGE Studio 日志

    示例：
        sage studio logs                # 前端日志
        sage studio logs --backend      # 后端日志
        sage studio logs --gateway      # Gateway 日志
        sage studio logs --follow       # 跟踪日志输出

    注意：本地 LLM 服务由 sageLLM 管理，日志通过 sageLLM 查看
    """
    console.print("[blue]📋 查看 Studio 日志...[/blue]")

    try:
        studio_manager.logs(follow=follow, backend=backend, gateway=gateway)
    except Exception as e:
        console.print(f"[red]❌ 查看日志失败: {e}[/red]")


@app.command()
def install():
    """安装 SAGE Studio 依赖"""
    console.print("[blue]📦 安装 SAGE Studio...[/blue]")

    try:
        success = studio_manager.install()
        if success:
            console.print("[green]✅ Studio 安装成功[/green]")
        else:
            console.print("[red]❌ Studio 安装失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 安装失败: {e}[/red]")


@app.command()
def build():
    """构建 SAGE Studio"""
    console.print("[blue]� 构建 SAGE Studio...[/blue]")

    try:
        success = studio_manager.build()
        if success:
            console.print("[green]✅ Studio 构建成功[/green]")
        else:
            console.print("[red]❌ Studio 构建失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 构建失败: {e}[/red]")


@app.command()
def open():
    """在浏览器中打开 Studio"""
    console.print("[blue]🌐 打开 Studio 界面...[/blue]")

    try:
        import webbrowser

        running_pid = studio_manager.is_running()
        if running_pid:
            config = studio_manager.load_config()
            url = f"http://{config['host']}:{config['port']}"
            webbrowser.open(url)
            console.print(f"[green]✅ 已在浏览器中打开: {url}[/green]")
        else:
            console.print("[yellow]⚠️ Studio 未运行，请先启动 Studio[/yellow]")
            console.print("使用命令: [bold]sage studio start[/bold]")
    except Exception as e:
        console.print(f"[red]❌ 打开失败: {e}[/red]")


@app.command()
def clean():
    """清理 Studio 缓存和临时文件"""
    console.print("[blue]🧹 清理 Studio 缓存...[/blue]")

    try:
        success = studio_manager.clean()  # type: ignore[attr-defined]
        if success:
            console.print("[green]✅ 清理完成[/green]")
        else:
            console.print("[red]❌ 清理失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 清理失败: {e}[/red]")


@app.command()
def npm(
    args: list[str] = typer.Argument(
        ...,
        metavar="ARGS...",
        help="传递给 npm 的参数，例如: install、run build、run lint",
    ),
):
    """在 Studio 前端目录中运行 npm 命令。"""
    joined = " ".join(args)
    console.print(f"[blue]执行 npm {joined}[/blue]")

    success = studio_manager.run_npm_command(args)
    if not success:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
