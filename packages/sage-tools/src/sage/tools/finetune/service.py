#!/usr/bin/env python3
"""
Finetune CLI - Service Management
服务管理：训练执行、模型合并、服务部署
"""

import json
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def start_training(config_path: Path, use_native: bool = True):
    """启动训练过程

    Args:
        config_path: 训练配置文件路径
        use_native: 是否使用 SAGE 原生训练模块（推荐）
    """
    try:
        if use_native:
            # 使用 SAGE 原生训练模块
            console.print("[cyan]使用 SAGE 原生训练模块[/cyan]\n")

            # 导入训练模块
            from sage.tools.finetune.trainer import train_from_meta

            # 读取配置文件获取输出目录
            with open(config_path) as f:
                config = json.load(f)

            # output_dir 是 checkpoints 目录，我们需要的是其父目录
            checkpoint_dir = Path(config.get("output_dir", "finetune_output"))
            if checkpoint_dir.name == "checkpoints":
                output_dir = checkpoint_dir.parent
            else:
                output_dir = checkpoint_dir

            # 执行训练
            train_from_meta(output_dir)

        else:
            # 尝试使用 LLaMA-Factory (可能不兼容)
            cmd = ["llamafactory-cli", "train", str(config_path)]
            console.print("[yellow]⚠️  使用 LLaMA-Factory (可能存在兼容性问题)[/yellow]")
            console.print(f"[cyan]执行命令: {' '.join(cmd)}[/cyan]\n")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            for line in process.stdout:
                console.print(line, end="")

            process.wait()

            if process.returncode == 0:
                console.print("\n[green]✅ 训练完成！[/green]")
            else:
                console.print(f"\n[red]❌ 训练失败，退出码: {process.returncode}[/red]")

    except ImportError as e:
        console.print(f"[red]❌ 导入错误: {e}[/red]")
        console.print("[yellow]提示:[/yellow]")
        console.print(
            "  • 确保已安装微调依赖: [cyan]pip install -e packages/sage-libs[finetune][/cyan]"
        )
    except FileNotFoundError as e:
        console.print(f"[red]❌ 找不到命令: {e}[/red]")
        console.print("[yellow]提示:[/yellow]")
        console.print("  • 使用 SAGE 原生脚本 (推荐): [cyan]--use-native[/cyan]")
        console.print("  • 或安装 LLaMA-Factory: [cyan]pip install llmtuner[/cyan]")


def merge_lora_weights(
    checkpoint_path: Path, base_model: str, output_path: Path
) -> bool:
    """合并 LoRA 权重到基础模型

    Args:
        checkpoint_path: LoRA checkpoint 路径
        base_model: 基础模型名称
        output_path: 输出路径

    Returns:
        是否成功
    """
    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        console.print("[red]❌ 缺少依赖，请安装:[/red]")
        console.print("[cyan]pip install transformers peft[/cyan]")
        return False

    try:
        console.print("[cyan]⏳ 加载基础模型...[/cyan]")
        base = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype="auto", device_map="cpu"  # 在CPU上合并，节省显存
        )

        console.print("[cyan]⏳ 加载 LoRA 权重...[/cyan]")
        model = PeftModel.from_pretrained(base, str(checkpoint_path))

        console.print("[cyan]⏳ 合并权重...[/cyan]")
        merged_model = model.merge_and_unload()

        console.print("[cyan]⏳ 保存合并模型...[/cyan]")
        merged_model.save_pretrained(str(output_path))

        # 保存tokenizer
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        tokenizer.save_pretrained(str(output_path))

        console.print("\n[green]✅ 合并完成！[/green]")
        console.print(f"📁 合并模型已保存到: [cyan]{output_path}[/cyan]")
        return True

    except Exception as e:
        console.print(f"[red]❌ 合并失败: {e}[/red]")
        return False


def serve_model_with_vllm(
    model_path: Path,
    host: str = "0.0.0.0",
    port: int = 8000,
    gpu_memory_utilization: float = 0.9,
    daemon: bool = False,
    lora_path: Path | None = None,
    lora_name: str | None = None,
) -> subprocess.Popen | None:
    """使用 vLLM 启动模型服务

    Args:
        model_path: 模型路径
        host: 服务主机
        port: 服务端口
        gpu_memory_utilization: GPU 显存利用率
        daemon: 是否后台运行
        lora_path: LoRA 路径（可选）
        lora_name: LoRA 名称（可选）

    Returns:
        进程对象（如果是daemon模式）
    """
    # 检查 vLLM 是否安装
    try:
        import vllm  # noqa: F401
    except ImportError:
        console.print("[yellow]⚠️  vLLM 未安装，正在安装...[/yellow]")
        subprocess.run(["pip", "install", "vllm"], check=True)
        console.print("[green]✅ vLLM 安装完成[/green]\n")

    # 构建命令
    cmd = [
        "python",
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        str(model_path),
        "--host",
        host,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        str(gpu_memory_utilization),
    ]

    if lora_path and lora_name:
        cmd.extend(["--enable-lora", "--lora-modules", f"{lora_name}={lora_path}"])

    console.print(f"[cyan]📡 启动命令: {' '.join(cmd)}[/cyan]\n")
    console.print(
        Panel.fit(
            f"[bold green]🎉 服务启动中...[/bold green]\n\n"
            f"📍 API 地址: [cyan]http://{host}:{port}[/cyan]\n"
            f"🤖 模型: [green]{model_path.name}[/green]\n\n"
            f"[bold]使用方式:[/bold]\n"
            f"  sage chat --backend compatible --base-url http://localhost:{port}/v1\n\n"
            f"[yellow]按 Ctrl+C 停止服务[/yellow]",
            border_style="green",
        )
    )

    if daemon:
        # 后台运行
        log_file = Path.cwd() / f"vllm_{model_path.name}.log"
        pid_file = Path.cwd() / f"vllm_{model_path.name}.pid"

        with open(log_file, "w") as f:
            process = subprocess.Popen(
                cmd, stdout=f, stderr=subprocess.STDOUT, start_new_session=True
            )

        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        console.print("\n[green]✅ 服务已在后台启动[/green]")
        console.print(f"PID: {process.pid}")
        console.print(f"日志: [cyan]{log_file}[/cyan]")
        console.print(f"\n停止服务: [cyan]kill {process.pid}[/cyan]")

        return process
    else:
        # 前台运行
        subprocess.run(cmd)
        return None
