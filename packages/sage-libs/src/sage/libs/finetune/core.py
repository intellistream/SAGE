#!/usr/bin/env python3
"""
Finetune CLI - Core Logic
核心逻辑：数据准备、配置生成
"""

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models import FinetuneTask
from .utils import collect_sage_code_files

console = Console()


def prepare_training_data(
    task_type: FinetuneTask,
    root_dir: Path,
    output_dir: Path,
    format: str = "alpaca",
    custom_data_path: Path | None = None,
    **kwargs,
) -> Path:
    """准备训练数据集（支持多种任务类型）"""
    output_dir.mkdir(parents=True, exist_ok=True)

    training_data = []

    if task_type == FinetuneTask.CODE_UNDERSTANDING:
        # 代码理解任务 - 收集代码文件
        extensions = kwargs.get("extensions", [".py", ".yaml", ".yml", ".toml", ".md", ".rst"])
        files = collect_sage_code_files(root_dir, extensions=extensions)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"📝 准备代码理解数据 ({len(files)} 个文件)...", total=len(files)
            )

            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    rel_path = file_path.relative_to(root_dir)

                    if format == "alpaca":
                        # 文件功能解释
                        training_data.append(
                            {
                                "instruction": f"请解释项目中 {rel_path} 文件的功能和实现",
                                "input": "",
                                "output": content,
                            }
                        )

                        # 代码问答
                        if file_path.suffix == ".py":
                            training_data.append(
                                {
                                    "instruction": f"项目中 {rel_path} 文件包含哪些类和函数？请详细说明。",
                                    "input": content[:1500],
                                    "output": f"这是 {rel_path} 的代码实现，包含了核心功能。让我为你详细分析...",
                                }
                            )

                            # 代码修改建议
                            training_data.append(
                                {
                                    "instruction": f"如何改进 {rel_path} 中的代码？",
                                    "input": content[:1000],
                                    "output": f"基于 {rel_path} 的代码分析，我建议从以下几个方面改进...",
                                }
                            )

                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[yellow]⚠️  跳过文件 {file_path}: {e}[/yellow]")
                    continue

    elif task_type == FinetuneTask.QA_PAIRS:
        # 问答对任务
        if custom_data_path and custom_data_path.exists():
            with open(custom_data_path, encoding="utf-8") as f:
                qa_data = json.load(f)

            for item in qa_data:
                if format == "alpaca":
                    training_data.append(
                        {
                            "instruction": item.get("question", ""),
                            "input": item.get("context", ""),
                            "output": item.get("answer", ""),
                        }
                    )
        else:
            console.print("[yellow]⚠️  需要提供问答数据文件路径[/yellow]")

    elif task_type == FinetuneTask.INSTRUCTION:
        # 指令微调任务
        if custom_data_path and custom_data_path.exists():
            with open(custom_data_path, encoding="utf-8") as f:
                instruction_data = json.load(f)

            for item in instruction_data:
                if format == "alpaca":
                    training_data.append(
                        {
                            "instruction": item.get("instruction", ""),
                            "input": item.get("input", ""),
                            "output": item.get("output", ""),
                        }
                    )
        else:
            console.print("[yellow]⚠️  需要提供指令数据文件路径[/yellow]")

    elif task_type == FinetuneTask.CHAT:
        # 对话微调任务
        if custom_data_path and custom_data_path.exists():
            with open(custom_data_path, encoding="utf-8") as f:
                chat_data = json.load(f)

            for item in chat_data:
                if format == "chat":
                    training_data.append({"conversations": item.get("conversations", [])})
                elif format == "alpaca":
                    # 转换为alpaca格式
                    conversations = item.get("conversations", [])
                    if len(conversations) >= 2:
                        training_data.append(
                            {
                                "instruction": conversations[0].get("content", ""),
                                "input": "",
                                "output": conversations[1].get("content", ""),
                            }
                        )
        else:
            console.print("[yellow]⚠️  需要提供对话数据文件路径[/yellow]")

    elif task_type == FinetuneTask.CUSTOM:
        # 自定义数据集
        if custom_data_path and custom_data_path.exists():
            with open(custom_data_path, encoding="utf-8") as f:
                training_data = json.load(f)
            console.print(f"✅ 已加载自定义数据集: {len(training_data)} 条")
        else:
            console.print("[red]❌ 自定义任务需要提供数据文件路径[/red]")
            import typer

            raise typer.Exit(1)

    # 保存训练数据
    output_file = output_dir / f"training_data_{task_type.value}_{format}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)

    console.print(f"\n✅ 训练数据已生成: [cyan]{output_file}[/cyan]")
    console.print(f"   📊 共 {len(training_data)} 条训练样本")

    return output_file


def generate_training_config(
    model_name: str,
    dataset_path: Path,
    output_dir: Path,
    framework: str = "llama-factory",
) -> Path:
    """生成训练配置文件"""

    config = {}

    if framework == "llama-factory":
        config = {
            "model_name_or_path": model_name,
            "stage": "sft",
            "do_train": True,
            "finetuning_type": "lora",
            "lora_target": "all",
            "dataset": str(dataset_path),
            "template": "qwen",
            "cutoff_len": 4096,
            "max_samples": 10000,
            "overwrite_cache": True,
            "preprocessing_num_workers": 16,
            "output_dir": str(output_dir / "checkpoints"),
            "logging_steps": 10,
            "save_steps": 500,
            "plot_loss": True,
            "overwrite_output_dir": True,
            "per_device_train_batch_size": 2,
            "gradient_accumulation_steps": 8,
            "learning_rate": 5e-5,
            "num_train_epochs": 3,
            "lr_scheduler_type": "cosine",
            "warmup_ratio": 0.1,
            "fp16": True,
            "lora_rank": 8,
            "lora_alpha": 16,
            "lora_dropout": 0.05,
        }
    elif framework == "unsloth":
        config = {
            "model_name": model_name,
            "max_seq_length": 4096,
            "load_in_4bit": True,
            "dataset": str(dataset_path),
            "dataset_text_field": "text",
            "packing": False,
            "output_dir": str(output_dir / "checkpoints"),
            "num_train_epochs": 3,
            "per_device_train_batch_size": 2,
            "gradient_accumulation_steps": 4,
            "warmup_steps": 10,
            "learning_rate": 2e-4,
            "fp16": True,
            "logging_steps": 1,
            "optim": "adamw_8bit",
            "weight_decay": 0.01,
            "lr_scheduler_type": "linear",
            "seed": 3407,
        }

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = output_dir / f"{framework}_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return config_path
