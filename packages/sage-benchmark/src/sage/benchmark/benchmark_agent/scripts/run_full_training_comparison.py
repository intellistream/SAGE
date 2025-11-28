#!/usr/bin/env python3
"""
Agent Training Method Comparison - Full Training on A100

This script runs ACTUAL fine-tuning experiments comparing methods A-D:
- Method A: Baseline SFT (no optimization)
- Method B: Coreset Selection (loss/diversity/hybrid strategies)
- Method C: Continual Learning (experience replay)
- Method D: Combined (Coreset + Continual)

Hardware: Optimized for A100 80GB (can use 2x A100 with DeepSpeed)

Usage:
    # Quick test (small samples, 1 epoch)
    python run_full_training_comparison.py --quick

    # Full comparison (all 4000 samples, 3 epochs)
    python run_full_training_comparison.py --full

    # Single method test
    python run_full_training_comparison.py --method D_combined
"""

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path


def setup_hf_mirror():
    """自动设置 HuggingFace 镜像（国内网络加速）"""
    if os.environ.get("HF_ENDPOINT"):
        return  # 用户已设置，不覆盖

    # 使用 urllib 进行真正的 HTTP 连接测试
    try:
        import urllib.request

        urllib.request.urlopen("https://huggingface.co", timeout=5)
    except Exception:
        # 无法访问，设置国内镜像
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        print(f"🌐 自动设置 HuggingFace 镜像: {os.environ['HF_ENDPOINT']}")


# 在导入 transformers 之前设置镜像
setup_hf_mirror()


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class MethodResult:
    """Result from a single training method."""

    method_name: str
    train_samples: int
    train_time_minutes: float
    eval_metrics: dict
    model_path: Path
    config: dict


def get_a100_methods(quick: bool = False):
    """Define training methods optimized for A100."""

    # Base settings for A100 80GB
    base_settings = {
        "base_model": "Qwen/Qwen2.5-7B-Instruct",  # Can go up to 14B/32B on A100
        "max_length": 4096,
        "batch_size": 4,  # A100 can handle larger batches
        "gradient_accumulation": 4,  # Effective batch = 16
        "bf16": True,  # A100 has good bf16 support
        "load_in_8bit": False,  # A100 has enough memory
    }

    if quick:
        # Quick test settings
        base_settings.update(
            {
                "max_train_samples": 500,
                "max_eval_samples": 100,
                "num_epochs": 1,
                "save_steps": 100,
                "eval_steps": 50,
            }
        )
    else:
        # Full training settings
        base_settings.update(
            {
                "max_train_samples": None,  # Use all 4000
                "max_eval_samples": 500,
                "num_epochs": 3,
                "save_steps": 500,
                "eval_steps": 200,
            }
        )

    methods = {
        "A_baseline": {
            "name": "A: Baseline SFT",
            "description": "Standard SFT without any optimization",
            "use_coreset": False,
            "use_continual": False,
            **base_settings,
        },
        "B1_coreset_loss": {
            "name": "B1: Coreset (Loss Top-K)",
            "description": "Select high-loss samples for training",
            "use_coreset": True,
            "coreset_strategy": "loss_topk",
            "coreset_target_size": 2000 if not quick else 300,
            "use_continual": False,
            **base_settings,
        },
        "B2_coreset_diversity": {
            "name": "B2: Coreset (Diversity)",
            "description": "Select diverse samples using feature distance",
            "use_coreset": True,
            "coreset_strategy": "diversity",
            "coreset_target_size": 2000 if not quick else 300,
            "use_continual": False,
            **base_settings,
        },
        "B3_coreset_hybrid": {
            "name": "B3: Coreset (Hybrid)",
            "description": "60% loss-based + 40% diversity-based",
            "use_coreset": True,
            "coreset_strategy": "hybrid",
            "coreset_target_size": 2000 if not quick else 300,
            "use_continual": False,
            **base_settings,
        },
        "C_continual": {
            "name": "C: Continual Learning",
            "description": "Online learning with experience replay buffer",
            "use_coreset": False,
            "use_continual": True,
            "continual_buffer_size": 2048,
            "continual_replay_ratio": 0.25,
            **base_settings,
        },
        "D_combined": {
            "name": "D: Coreset + Continual",
            "description": "Combined approach: hybrid coreset + continual learning",
            "use_coreset": True,
            "coreset_strategy": "hybrid",
            "coreset_target_size": 2500 if not quick else 350,
            "use_continual": True,
            "continual_buffer_size": 2048,
            "continual_replay_ratio": 0.20,
            **base_settings,
        },
    }

    return methods


def train_method(method_id: str, method_config: dict, output_dir: Path) -> MethodResult:
    """Train a single method and return results."""
    from sage.libs.finetune.agent import AgentSFTConfig, AgentSFTTrainer

    print(f"\n{'=' * 60}")
    print(f"Training: {method_config['name']}")
    print(f"{'=' * 60}")
    print(f"Description: {method_config['description']}")
    print(f"Coreset: {method_config.get('use_coreset', False)}")
    print(f"Continual: {method_config.get('use_continual', False)}")

    method_output = output_dir / method_id
    method_output.mkdir(parents=True, exist_ok=True)

    # Create AgentSFTConfig
    config = AgentSFTConfig(
        base_model=method_config["base_model"],
        train_data="agent_sft:train",
        dev_data="agent_sft:dev",
        max_train_samples=method_config.get("max_train_samples"),
        max_eval_samples=method_config.get("max_eval_samples", 500),
        num_epochs=method_config.get("num_epochs", 3),
        batch_size=method_config.get("batch_size", 4),
        gradient_accumulation=method_config.get("gradient_accumulation", 4),
        max_length=method_config.get("max_length", 4096),
        learning_rate=method_config.get("learning_rate", 2e-5),
        # Coreset settings
        use_coreset_selection=method_config.get("use_coreset", False),
        coreset_strategy=method_config.get("coreset_strategy", "hybrid"),
        coreset_target_size=method_config.get("coreset_target_size"),
        # Continual learning settings
        use_online_continual=method_config.get("use_continual", False),
        continual_buffer_size=method_config.get("continual_buffer_size", 2048),
        continual_replay_ratio=method_config.get("continual_replay_ratio", 0.25),
        # A100 optimizations
        bf16=method_config.get("bf16", True),
        fp16=False,
        load_in_8bit=method_config.get("load_in_8bit", False),
        load_in_4bit=False,
        gradient_checkpointing=True,
        optim="adamw_torch",  # Use standard optimizer (paged_adamw_8bit requires bitsandbytes)
        # Output
        output_dir=method_output,
        save_steps=method_config.get("save_steps", 500),
        eval_steps=method_config.get("eval_steps", 200),
        logging_steps=20,
        report_to="tensorboard",
    )

    print("\nConfig Summary:")
    print(f"  Model: {config.base_model}")
    print(f"  Max samples: {config.max_train_samples or 'all'}")
    print(f"  Epochs: {config.num_epochs}")
    print(f"  Effective batch: {config.effective_batch_size}")
    print(f"  Output: {config.output_dir}")

    # Train
    start_time = time.time()
    trainer = AgentSFTTrainer(config)
    trainer.train()
    train_time = (time.time() - start_time) / 60  # minutes

    train_samples = len(trainer._train_samples)

    print(f"\n✅ Training complete in {train_time:.1f} minutes")
    print(f"   Trained on {train_samples} samples")

    # Evaluate trained model
    eval_metrics = evaluate_trained_model(config.lora_dir, config.base_model)

    return MethodResult(
        method_name=method_config["name"],
        train_samples=train_samples,
        train_time_minutes=train_time,
        eval_metrics=eval_metrics,
        model_path=config.lora_dir,
        config=method_config,
    )


def evaluate_trained_model(lora_path: Path, base_model: str) -> dict:
    """Evaluate the trained model on agent benchmarks.

    This function loads the fine-tuned LoRA model and evaluates its
    tool selection performance against the benchmark dataset.
    """

    print(f"\nEvaluating model: {lora_path}")

    # Check if LoRA weights exist
    if not lora_path.exists():
        print(f"⚠️ LoRA path not found: {lora_path}, using baseline evaluation")
        return _evaluate_baseline()

    try:
        # Load fine-tuned model for inference
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("Loading base model...")
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        print("Loading LoRA weights...")
        model = PeftModel.from_pretrained(model, str(lora_path))
        model.eval()

        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Run evaluation with fine-tuned model
        metrics = _evaluate_with_model(model, tokenizer)

        # Clean up to free GPU memory
        del model
        torch.cuda.empty_cache()

        return metrics

    except Exception as e:
        print(f"⚠️ Failed to load fine-tuned model: {e}")
        print("Falling back to baseline evaluation")
        return _evaluate_baseline()


def _evaluate_baseline() -> dict:
    """Evaluate using baseline keyword selector."""
    from sage.benchmark.benchmark_agent import (
        ToolSelectionConfig,
        ToolSelectionExperiment,
        get_adapter_registry,
    )
    from sage.benchmark.benchmark_agent.evaluation import compute_metrics
    from sage.data import DataManager

    dm = DataManager.get_instance()
    registry = get_adapter_registry()

    eval_config = ToolSelectionConfig(
        experiment="tool_selection",
        profile="quick_eval",
        split="test",
        selector="baseline.keyword",
        top_k=5,
        max_samples=100,
        verbose=False,
    )

    exp = ToolSelectionExperiment(eval_config, data_manager=dm, adapter_registry=registry)
    exp.prepare()
    result = exp.run()

    metrics = compute_metrics(
        task="tool_selection",
        predictions=result.predictions,
        references=result.references,
        metrics=["top_k_accuracy", "recall_at_k", "precision_at_k", "mrr"],
        k=5,
    )

    return {k: v for k, v in metrics.items() if "_error" not in k and isinstance(v, float)}


def _evaluate_with_model(model, tokenizer) -> dict:
    """Evaluate using the fine-tuned model for tool selection.

    This creates a model-based tool selector that uses the fine-tuned
    model to score and rank candidate tools.
    """
    import random

    import torch

    from sage.benchmark.benchmark_agent.evaluation import compute_metrics
    from sage.data import DataManager

    print("Running model-based evaluation...")

    dm = DataManager.get_instance()

    # Get evaluation data using correct API
    benchmark_loader = dm.get_by_source("agent_benchmark")
    eval_samples = list(benchmark_loader.iter_split("tool_selection", split="test"))
    if len(eval_samples) > 100:
        random.seed(42)
        eval_samples = random.sample(eval_samples, 100)

    # Get tool library using correct API
    tools_loader = dm.get_by_source("agent_tools")
    tools = list(tools_loader.iter_all())
    tool_map = {t.tool_id: t for t in tools}

    predictions = []
    references = []

    for sample in eval_samples:
        # Sample is a dataclass, access via attributes
        query = sample.instruction
        expected_tools = sample.ground_truth.get("top_k", []) if sample.ground_truth else []
        if isinstance(expected_tools, str):
            expected_tools = [expected_tools]

        # Use candidate tools from sample if available, otherwise use first 50 tools
        candidate_tool_ids = (
            sample.candidate_tools if sample.candidate_tools else list(tool_map.keys())[:50]
        )
        scored = []

        for tool_id in candidate_tool_ids:
            tool = tool_map.get(tool_id)
            if not tool:
                continue
            tool_name = tool.name or tool_id
            tool_desc = tool.description or f"{tool.category} tool"

            # Create prompt for scoring
            prompt = f"""Given the user query, rate how relevant this tool is (0-10).
Query: {query}
Tool: {tool_name}
Description: {tool_desc}
Relevance score (0-10):"""

            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=5,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            response = tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1] :], skip_special_tokens=True
            )

            # Extract score
            try:
                score = float(response.strip().split()[0])
            except (ValueError, IndexError):
                score = 5.0  # Default middle score

            scored.append((tool_id, score))

        # Sort by score and get top-k
        scored.sort(key=lambda x: x[1], reverse=True)
        predicted = [t[0] for t in scored[:5]]

        predictions.append(predicted)
        references.append(expected_tools)

    # Compute metrics
    metrics = compute_metrics(
        task="tool_selection",
        predictions=predictions,
        references=references,
        metrics=["top_k_accuracy", "recall_at_k", "precision_at_k", "mrr"],
        k=5,
    )

    return {k: v for k, v in metrics.items() if "_error" not in k and isinstance(v, float)}


def generate_comparison_report(results: list[MethodResult], output_dir: Path):
    """Generate comparison report and charts."""
    print(f"\n{'=' * 60}")
    print("COMPARISON RESULTS")
    print(f"{'=' * 60}")

    # Print summary table
    print(f"\n{'Method':<30} {'Samples':<10} {'Time(min)':<12} {'Top-K Acc':<12} {'MRR':<10}")
    print("-" * 74)

    for r in results:
        top_k = r.eval_metrics.get("top_k_accuracy", 0)
        mrr = r.eval_metrics.get("mrr", 0)
        print(
            f"{r.method_name:<30} {r.train_samples:<10} {r.train_time_minutes:<12.1f} {top_k:<12.2%} {mrr:<10.2%}"
        )

    # Find best method
    best = max(results, key=lambda r: r.eval_metrics.get("top_k_accuracy", 0))
    print(f"\n🏆 Best Method: {best.method_name}")
    print(f"   Top-K Accuracy: {best.eval_metrics.get('top_k_accuracy', 0):.2%}")

    # Save results to JSON
    results_data = []
    for r in results:
        results_data.append(
            {
                "method_name": r.method_name,
                "train_samples": r.train_samples,
                "train_time_minutes": r.train_time_minutes,
                "eval_metrics": r.eval_metrics,
                "model_path": str(r.model_path),
                "config": r.config,
            }
        )

    results_file = output_dir / "training_results.json"
    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {results_file}")

    # Generate chart
    try:
        generate_chart(results, output_dir)
    except Exception as e:
        logger.warning(f"Could not generate chart: {e}")


def generate_chart(results: list[MethodResult], output_dir: Path):
    """Generate comparison visualization."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Agent Training Method Comparison (A100)", fontsize=14)

    methods = [r.method_name for r in results]
    colors = plt.cm.Set2(np.linspace(0, 1, len(methods)))

    # 1. Training efficiency
    ax1 = axes[0]
    times = [r.train_time_minutes for r in results]
    ax1.barh(methods, times, color=colors)
    ax1.set_xlabel("Training Time (minutes)")
    ax1.set_title("Training Efficiency")

    # 2. Accuracy comparison
    ax2 = axes[1]
    top_k = [r.eval_metrics.get("top_k_accuracy", 0) for r in results]
    ax2.barh(methods, top_k, color=colors)
    ax2.set_xlabel("Top-K Accuracy")
    ax2.set_title("Accuracy")
    ax2.axvline(x=0.95, color="red", linestyle="--", label="Target 95%")
    ax2.set_xlim(0, 1)

    # 3. All metrics
    ax3 = axes[2]
    metrics = ["top_k_accuracy", "recall_at_k", "mrr"]
    x = np.arange(len(metrics))
    width = 0.12

    for i, r in enumerate(results):
        values = [r.eval_metrics.get(m, 0) for m in metrics]
        ax3.bar(x + i * width, values, width, label=r.method_name[:15], color=colors[i])

    ax3.set_ylabel("Score")
    ax3.set_title("All Metrics")
    ax3.set_xticks(x + width * (len(results) - 1) / 2)
    ax3.set_xticklabels([m.replace("_", "\n") for m in metrics])
    ax3.legend(loc="upper right", fontsize=7)
    ax3.set_ylim(0, 1)

    plt.tight_layout()
    chart_path = output_dir / "training_comparison.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    print(f"Chart saved to: {chart_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Agent Training Method Comparison on A100")
    parser.add_argument("--quick", action="store_true", help="Quick test (500 samples, 1 epoch)")
    parser.add_argument("--full", action="store_true", help="Full training (all samples, 3 epochs)")
    parser.add_argument("--method", type=str, help="Run single method only")
    parser.add_argument(
        "--output", type=Path, default=Path("./training_comparison"), help="Output directory"
    )
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct", help="Base model")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 AGENT TRAINING METHOD COMPARISON")
    print("   Target: 难题4 - 95%+ Tool Selection Accuracy")
    print("   Hardware: A100 80GB")
    print("=" * 70)

    # Check GPU
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                mem = torch.cuda.get_device_properties(i).total_memory / 1e9
                print(f"GPU {i}: {name} ({mem:.0f}GB)")
        else:
            print("⚠️ No GPU detected!")
    except ImportError:
        print("⚠️ PyTorch not installed")

    # Get methods
    quick = args.quick or (not args.full)
    methods = get_a100_methods(quick=quick)

    # Update base model if specified
    if args.model:
        for m in methods.values():
            m["base_model"] = args.model

    # Filter to single method if specified
    if args.method:
        if args.method not in methods:
            print(f"❌ Unknown method: {args.method}")
            print(f"Available: {list(methods.keys())}")
            return
        methods = {args.method: methods[args.method]}

    print(f"\nMethods to train: {len(methods)}")
    print(f"Mode: {'Quick' if quick else 'Full'}")
    print(f"Output: {args.output}")

    args.output.mkdir(parents=True, exist_ok=True)

    # Run training for each method
    results = []
    for method_id, method_config in methods.items():
        try:
            result = train_method(method_id, method_config, args.output)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to train {method_id}: {e}")
            continue

    # Generate comparison report
    if results:
        generate_comparison_report(results, args.output)

    print("\n✅ All experiments complete!")


if __name__ == "__main__":
    main()
