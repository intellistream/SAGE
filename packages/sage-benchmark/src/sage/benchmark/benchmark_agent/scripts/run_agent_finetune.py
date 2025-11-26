#!/usr/bin/env python
"""
Agent Tool Planning 微调训练脚本

使用 sage.libs.finetune (LoRATrainer) + sage.tools.agent_training 数据
在 A100 GPU 上训练 Agent Tool Planning 模型

用法:
    # 快速测试 (小数据 + 小模型)
    python run_agent_finetune.py --quick

    # 标准训练 (7B模型 + 全部数据)
    python run_agent_finetune.py --standard

    # 大模型训练 (14B+, 需要多卡)
    python run_agent_finetune.py --large

    # 自定义配置
    python run_agent_finetune.py --model Qwen/Qwen2.5-7B-Instruct --epochs 5 --max-samples 1000
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent


def setup_environment():
    """配置环境"""
    # 禁用 tokenizers 并行 (避免警告)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # 设置 HF 缓存目录
    cache_dir = PROJECT_ROOT / ".sage" / "cache" / "huggingface"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_dir)


def check_gpu():
    """检查 GPU 状态"""
    try:
        import torch

        if not torch.cuda.is_available():
            print("❌ CUDA 不可用")
            return None, 0

        gpu_count = torch.cuda.device_count()
        gpu_info = []
        total_memory = 0

        for i in range(gpu_count):
            name = torch.cuda.get_device_name(i)
            mem_total = torch.cuda.get_device_properties(i).total_memory / 1024**3
            mem_free = (
                torch.cuda.get_device_properties(i).total_memory - torch.cuda.memory_reserved(i)
            ) / 1024**3
            gpu_info.append(f"  GPU {i}: {name} ({mem_total:.1f}GB total, ~{mem_free:.1f}GB free)")
            total_memory += mem_total

        print("🖥️  GPU 状态:")
        print("\n".join(gpu_info))
        print()

        return gpu_count, total_memory

    except ImportError:
        print("❌ PyTorch 未安装")
        return None, 0


def load_agent_sft_data(max_samples: int | None = None) -> list[dict]:
    """加载 Agent SFT 训练数据

    Args:
        max_samples: 最大样本数 (None = 全部)

    Returns:
        对话格式数据列表
    """
    from sage.data import DataManager
    from sage.libs.finetune.agent import AgentDialogProcessor

    print("\n📊 加载 Agent SFT 数据...")

    # 使用 DataManager 加载数据
    dm = DataManager.get_instance()
    raw_data = dm.load("agent_sft", split="train")
    if max_samples:
        raw_data = raw_data[:max_samples]

    # 处理成对话格式
    processor = AgentDialogProcessor()
    dialogs = processor.process_batch(raw_data)

    # 转换成 sage.libs.finetune 需要的 conversation 格式
    formatted_data = []
    for dialog in dialogs:
        conversations = []
        for msg in dialog.messages:
            conversations.append({"role": msg.role, "content": msg.content})
        formatted_data.append({"conversations": conversations})

    print(f"✅ 加载了 {len(formatted_data)} 条对话数据")
    return formatted_data


def save_training_data(data: list[dict], output_path: Path) -> Path:
    """保存训练数据为 JSON 文件

    Args:
        data: 对话数据
        output_path: 输出目录

    Returns:
        数据文件路径
    """
    data_file = output_path / "train_data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 训练数据保存到: {data_file}")
    return data_file


def get_training_config(
    preset: str,
    model_name: str | None = None,
    epochs: int | None = None,
    output_dir: Path | None = None,
    data_path: Path | None = None,
) -> Any:
    """获取训练配置

    Args:
        preset: 预设配置 (quick/standard/large)
        model_name: 模型名称 (覆盖预设)
        epochs: 训练轮数 (覆盖预设)
        output_dir: 输出目录
        data_path: 数据路径

    Returns:
        TrainingConfig
    """
    from sage.libs.finetune import LoRAConfig, PresetConfigs

    if preset == "quick":
        # 快速测试: 小模型, 少 epoch
        config = PresetConfigs.a100()
        config.model_name = model_name or "Qwen/Qwen2.5-1.5B-Instruct"
        config.num_train_epochs = epochs or 1
        config.max_length = 2048
        config.per_device_train_batch_size = 4

    elif preset == "standard":
        # 标准训练: 7B 模型
        config = PresetConfigs.a100()
        config.model_name = model_name or "Qwen/Qwen2.5-7B-Instruct"
        config.num_train_epochs = epochs or 3
        config.max_length = 4096

    elif preset == "large":
        # 大模型训练: 14B+
        config = PresetConfigs.a100()
        config.model_name = model_name or "Qwen/Qwen2.5-14B-Instruct"
        config.num_train_epochs = epochs or 3
        config.max_length = 4096
        config.per_device_train_batch_size = 4  # 减小 batch size
        config.gradient_accumulation_steps = 4
        # 使用更大的 LoRA rank
        config.lora = LoRAConfig(
            r=16,
            lora_alpha=32,
            target_modules=[
                "q_proj",
                "v_proj",
                "k_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
        )

    else:
        # 自定义
        config = PresetConfigs.a100()
        if model_name:
            config.model_name = model_name
        if epochs:
            config.num_train_epochs = epochs

    # 设置公共参数
    if output_dir:
        config.output_dir = output_dir
    if data_path:
        config.data_path = data_path

    # Agent-specific 优化
    # 工具规划任务需要更长的上下文
    if config.max_length < 2048:
        config.max_length = 2048

    return config


def run_training(config) -> Path:
    """执行训练

    Args:
        config: TrainingConfig

    Returns:
        输出目录
    """
    from sage.libs.finetune import LoRATrainer

    print("\n" + "=" * 60)
    print("🚀 开始 Agent Tool Planning 微调训练")
    print("=" * 60)
    print("\n📋 训练配置:")
    print(f"  • 基础模型: {config.model_name}")
    print(f"  • 训练轮数: {config.num_train_epochs}")
    print(f"  • 序列长度: {config.max_length}")
    print(f"  • Batch Size: {config.per_device_train_batch_size}")
    print(f"  • 梯度累积: {config.gradient_accumulation_steps}")
    print(f"  • 有效 Batch: {config.effective_batch_size}")
    print(f"  • LoRA Rank: {config.lora.r}")
    print(f"  • 精度: {'bf16' if config.bf16 else 'fp16' if config.fp16 else 'fp32'}")
    print(f"  • 输出目录: {config.output_dir}")
    print()

    # 创建训练器
    trainer = LoRATrainer(config)

    # 执行训练
    trainer.train()

    return config.output_dir


def evaluate_model(model_dir: Path):
    """评估训练后的模型

    Args:
        model_dir: 模型目录
    """
    print("\n" + "=" * 60)
    print("📊 评估训练后的模型")
    print("=" * 60)

    # TODO: 集成 benchmark 评估
    # from sage.benchmark import ToolSelectionExperiment

    print("\n💡 手动评估命令:")
    print("  # 测试对话")
    print(f"  sage finetune chat {model_dir.name}")
    print("  ")
    print("  # 合并权重")
    print(f"  sage finetune merge {model_dir.name}")
    print("  ")
    print("  # 运行 benchmark")
    print(f"  python run_method_comparison.py --model-path {model_dir / 'lora_weights'}")


def main():
    parser = argparse.ArgumentParser(
        description="Agent Tool Planning 微调训练",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 快速测试 (1.5B模型, 1 epoch, ~100样本)
  python run_agent_finetune.py --quick

  # 标准训练 (7B模型, 3 epochs, 全部数据)
  python run_agent_finetune.py --standard

  # 大模型训练 (14B模型)
  python run_agent_finetune.py --large

  # 自定义配置
  python run_agent_finetune.py --model Qwen/Qwen2.5-7B-Instruct --epochs 5 --max-samples 2000
        """,
    )

    # 预设配置
    preset_group = parser.add_mutually_exclusive_group()
    preset_group.add_argument("--quick", action="store_true", help="快速测试 (1.5B, 1 epoch)")
    preset_group.add_argument("--standard", action="store_true", help="标准训练 (7B, 3 epochs)")
    preset_group.add_argument("--large", action="store_true", help="大模型训练 (14B+)")

    # 自定义参数
    parser.add_argument("--model", type=str, help="基础模型名称 (覆盖预设)")
    parser.add_argument("--epochs", type=int, help="训练轮数 (覆盖预设)")
    parser.add_argument("--max-samples", type=int, help="最大样本数 (None=全部)")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument("--skip-eval", action="store_true", help="跳过评估")
    parser.add_argument("--dry-run", action="store_true", help="只显示配置, 不执行训练")

    args = parser.parse_args()

    # 设置环境
    setup_environment()

    print("=" * 60)
    print("🧠 Agent Tool Planning Fine-tuning")
    print("   使用 sage.libs.finetune + sage.tools.agent_training")
    print("=" * 60)

    # 检查 GPU
    gpu_count, total_memory = check_gpu()
    if gpu_count is None:
        print("\n❌ 无法检测到 GPU, 退出")
        sys.exit(1)

    # 确定预设
    if args.quick:
        preset = "quick"
        max_samples = args.max_samples or 100
    elif args.standard:
        preset = "standard"
        max_samples = args.max_samples
    elif args.large:
        preset = "large"
        max_samples = args.max_samples
    else:
        preset = "standard"  # 默认
        max_samples = args.max_samples

    # 设置输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = PROJECT_ROOT / ".sage" / "finetune_output" / f"agent_tool_planning_{preset}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    train_data = load_agent_sft_data(max_samples=max_samples)
    data_file = save_training_data(train_data, output_dir)

    # 获取配置
    config = get_training_config(
        preset=preset,
        model_name=args.model,
        epochs=args.epochs,
        output_dir=output_dir,
        data_path=data_file,
    )

    if args.dry_run:
        print("\n📋 [Dry Run] 训练配置:")
        print(f"  预设: {preset}")
        print(f"  模型: {config.model_name}")
        print(f"  数据: {len(train_data)} 样本")
        print(f"  轮数: {config.num_train_epochs}")
        print(f"  输出: {config.output_dir}")
        print("\n使用 --standard/--quick/--large 执行实际训练")
        return

    # 执行训练
    output_dir = run_training(config)

    # 评估
    if not args.skip_eval:
        evaluate_model(output_dir)

    print("\n" + "=" * 60)
    print("✅ 完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
