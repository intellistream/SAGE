#!/usr/bin/env python3
"""
Agent SFT Training Example

This example demonstrates how to:
1. Load agent SFT data from sage-benchmark
2. Train a model using LoRA fine-tuning
3. Evaluate the trained model on agent benchmarks

Target: 难题4 - 高精度工具规划与调用 (95%+ accuracy goal)

Usage:
    # Quick test (small model, limited samples)
    python agent_sft_training_example.py --quick

    # Full training
    python agent_sft_training_example.py --full

    # Evaluation only (with existing model)
    python agent_sft_training_example.py --eval-only --model-path ./output

Requirements:
    - GPU with 8GB+ VRAM for quick mode
    - GPU with 24GB+ VRAM for full mode
    - pip install transformers peft accelerate bitsandbytes
"""

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if training dependencies are installed."""
    try:
        import accelerate  # noqa: F401
        import peft  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401

        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Install with: pip install transformers peft accelerate bitsandbytes")
        return False


def show_data_stats():
    """Display agent SFT data statistics."""
    from sage.data.sources.agent_sft import AgentSFTDataLoader
    from sage.data.sources.agent_tools import AgentToolsDataLoader

    print("\n" + "=" * 60)
    print("AGENT DATA STATISTICS")
    print("=" * 60)

    # Tools
    tools_loader = AgentToolsDataLoader()
    tools = list(tools_loader.iter_all())
    print(f"\n📦 Agent Tools: {len(tools)} tools")

    # SFT Data
    sft_loader = AgentSFTDataLoader()
    stats = sft_loader.get_stats()
    print("\n📚 Agent SFT Data:")
    print(f"   Total dialogs: {stats.total_dialogs}")
    print(f"   Train: {stats.train_count}")
    print(f"   Dev: {stats.dev_count}")
    print(f"   Test: {stats.test_count}")

    # Task distribution
    print("\n📊 Additional Stats:")
    print(f"   Avg turns/dialog: {stats.avg_turns:.1f}")
    print(f"   Avg tools/dialog: {stats.avg_tools_per_dialog:.1f}")
    print(f"   Unique tools: {stats.unique_tools}")

    return True


def train_quick_mode(output_dir: Path):
    """Quick training mode for testing the pipeline."""
    from sage.libs.finetune.agent import AgentSFTConfig, AgentSFTTrainer

    print("\n" + "=" * 60)
    print("QUICK TRAINING MODE")
    print("=" * 60)

    config = AgentSFTConfig(
        base_model="Qwen/Qwen2.5-1.5B-Instruct",
        train_data="agent_sft:train",
        dev_data="agent_sft:dev",
        max_train_samples=200,  # Limited for quick test
        max_eval_samples=50,
        num_epochs=1,
        batch_size=1,
        gradient_accumulation=8,
        max_length=1024,
        load_in_8bit=True,
        output_dir=output_dir,
        logging_steps=10,
        save_steps=100,
        eval_steps=50,
    )

    print("\nConfig:")
    print(f"  Model: {config.base_model}")
    print(f"  Train samples: {config.max_train_samples}")
    print(f"  Epochs: {config.num_epochs}")
    print(f"  Effective batch: {config.effective_batch_size}")
    print(f"  Output: {config.output_dir}")

    trainer = AgentSFTTrainer(config)
    trainer.train()

    return config.lora_dir


def train_full_mode(output_dir: Path):
    """Full training mode for production."""
    from sage.libs.finetune.agent import AgentSFTConfig, AgentSFTTrainer

    print("\n" + "=" * 60)
    print("FULL TRAINING MODE")
    print("=" * 60)

    config = AgentSFTConfig(
        base_model="Qwen/Qwen2.5-7B-Instruct",
        train_data="agent_sft:train",
        dev_data="agent_sft:dev",
        max_train_samples=None,  # Use all data
        max_eval_samples=500,
        num_epochs=3,
        batch_size=1,
        gradient_accumulation=16,
        max_length=4096,
        load_in_8bit=True,
        output_dir=output_dir,
        task_weights={
            "tool_selection": 0.35,
            "multi_step_planning": 0.30,
            "timing_decision": 0.20,
            "tool_retrieval": 0.15,
        },
        logging_steps=20,
        save_steps=500,
        eval_steps=200,
        report_to="tensorboard",
    )

    print("\nConfig:")
    print(f"  Model: {config.base_model}")
    print(f"  Train data: {config.train_data} (full)")
    print(f"  Epochs: {config.num_epochs}")
    print(f"  Effective batch: {config.effective_batch_size}")
    print(f"  Output: {config.output_dir}")

    trainer = AgentSFTTrainer(config)
    trainer.train()

    return config.lora_dir


def evaluate_model(model_path: Path):
    """Evaluate trained model on agent benchmarks."""
    from sage.benchmark.benchmark_agent import (
        ToolSelectionConfig,
        ToolSelectionExperiment,
        get_adapter_registry,
    )
    from sage.benchmark.benchmark_agent.evaluation import compute_metrics
    from sage.data import DataManager

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)

    dm = DataManager.get_instance()
    registry = get_adapter_registry()

    # Run tool selection experiment
    config = ToolSelectionConfig(
        experiment="tool_selection",
        profile="quick_eval",
        split="test",
        selector="baseline.keyword",  # TODO: Replace with trained model
        top_k=5,
        max_samples=100,
        verbose=True,
    )

    exp = ToolSelectionExperiment(config, data_manager=dm, adapter_registry=registry)
    exp.prepare()
    result = exp.run()

    # Compute metrics
    metrics = compute_metrics(
        task="tool_selection",
        predictions=result.predictions,
        references=result.references,
        metrics=["top_k_accuracy", "recall_at_k", "mrr"],
        k=5,
    )

    print("\n" + "-" * 40)
    print("EVALUATION RESULTS")
    print("-" * 40)
    for name, value in metrics.items():
        if "_error" not in name and isinstance(value, float):
            print(f"  {name}: {value * 100:.2f}%")

    # Target comparison
    print("\n" + "-" * 40)
    print("TARGET COMPARISON (难题4)")
    print("-" * 40)
    target = 0.95
    top_k_acc = metrics.get("top_k_accuracy", 0)
    if top_k_acc >= target:
        print(f"  ✓ Top-5 Accuracy: {top_k_acc * 100:.1f}% >= {target * 100:.0f}% (TARGET MET)")
    else:
        gap = target - top_k_acc
        print(
            f"  △ Top-5 Accuracy: {top_k_acc * 100:.1f}% < {target * 100:.0f}% (gap: {gap * 100:.1f}%)"
        )
        print("    Note: Baseline strategy used. Train with SFT data for better results.")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Agent SFT Training Example")
    parser.add_argument("--quick", action="store_true", help="Quick training mode")
    parser.add_argument("--full", action="store_true", help="Full training mode")
    parser.add_argument("--eval-only", action="store_true", help="Evaluation only")
    parser.add_argument("--model-path", type=Path, help="Path to trained model")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / ".sage" / "agent_training_example",
        help="Output directory",
    )
    parser.add_argument("--stats-only", action="store_true", help="Show data stats only")
    args = parser.parse_args()

    print("=" * 60)
    print("SAGE Agent SFT Training Pipeline")
    print("Target: 难题4 - 高精度工具规划与调用")
    print("=" * 60)

    # Show data statistics
    show_data_stats()

    if args.stats_only:
        return

    # Check dependencies
    if not args.eval_only:
        if not check_dependencies():
            return

    # Training
    model_path = args.model_path
    if args.quick:
        model_path = train_quick_mode(args.output_dir / "quick")
    elif args.full:
        model_path = train_full_mode(args.output_dir / "full")
    elif not args.eval_only:
        print("\nNo training mode specified. Use --quick or --full")
        print("Use --stats-only to just see data statistics")
        return

    # Evaluation
    if model_path or args.eval_only:
        evaluate_model(model_path)


if __name__ == "__main__":
    main()
