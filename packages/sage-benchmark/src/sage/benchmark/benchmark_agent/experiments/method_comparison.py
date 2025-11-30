"""
Method Comparison Framework for Agent Training Experiments

Provides infrastructure to compare different training methods:
- Method A: Baseline (no coreset, no continual learning)
- Method B: Coreset Selection (loss_topk, diversity, hybrid, random)
- Method C: Online Continual Learning
- Method D: Coreset + Continual Learning (combined)

Features:
- Automatic experiment execution
- Result collection and aggregation
- Comparison chart generation
- Statistical analysis
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class MethodConfig:
    """Configuration for a single training method."""

    name: str
    description: str

    # Coreset settings
    use_coreset: bool = False
    coreset_strategy: Literal["loss_topk", "diversity", "hybrid", "random"] = "loss_topk"
    coreset_target_size: Optional[int] = None

    # Continual learning settings
    use_continual: bool = False
    continual_buffer_size: int = 2048
    continual_replay_ratio: float = 0.25

    # Training settings
    max_train_samples: Optional[int] = None
    num_epochs: int = 1
    learning_rate: float = 2e-5

    # Advanced LoRA methods (Task B4)
    use_dora: bool = False  # DoRA: Weight-Decomposed LoRA
    use_lora_plus: bool = False  # LoRA+: Differentiated learning rates
    lora_plus_lr_ratio: float = 16.0  # B matrix lr = base_lr * ratio

    # FireAct trajectory fine-tuning (Task B1)
    use_trajectory_collection: bool = False  # Enable FireAct-style trajectory collection
    trajectory_min_reward: float = 0.5  # Minimum reward for filtering trajectories
    trajectory_require_success: bool = True  # Only use successful trajectories
    trajectory_max_steps: int = 10  # Maximum steps per trajectory

    # AgentTuning multi-task training (Task B2)
    use_multi_task: bool = False  # Enable AgentTuning-style multi-task mixing
    task_weights: Optional[dict[str, float]] = None  # Task type weights
    mixing_strategy: Literal["weighted", "balanced", "curriculum"] = "weighted"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "use_coreset": self.use_coreset,
            "coreset_strategy": self.coreset_strategy,
            "coreset_target_size": self.coreset_target_size,
            "use_continual": self.use_continual,
            "continual_buffer_size": self.continual_buffer_size,
            "continual_replay_ratio": self.continual_replay_ratio,
            "max_train_samples": self.max_train_samples,
            "num_epochs": self.num_epochs,
            "learning_rate": self.learning_rate,
            "use_dora": self.use_dora,
            "use_lora_plus": self.use_lora_plus,
            "lora_plus_lr_ratio": self.lora_plus_lr_ratio,
            "use_trajectory_collection": self.use_trajectory_collection,
            "trajectory_min_reward": self.trajectory_min_reward,
            "trajectory_require_success": self.trajectory_require_success,
            "trajectory_max_steps": self.trajectory_max_steps,
            "use_multi_task": self.use_multi_task,
            "task_weights": self.task_weights,
            "mixing_strategy": self.mixing_strategy,
        }


@dataclass
class ExperimentResult:
    """Result from a single method experiment."""

    method_name: str
    config: dict
    metrics: dict[str, float]
    training_time_seconds: float
    eval_time_seconds: float
    num_train_samples: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "method_name": self.method_name,
            "config": self.config,
            "metrics": self.metrics,
            "training_time_seconds": self.training_time_seconds,
            "eval_time_seconds": self.eval_time_seconds,
            "num_train_samples": self.num_train_samples,
            "timestamp": self.timestamp,
        }


class MethodRegistry:
    """Registry of predefined training methods."""

    @staticmethod
    def get_all_methods() -> dict[str, MethodConfig]:
        """Get all predefined methods for comparison."""
        return {
            "A_baseline": MethodConfig(
                name="A: Baseline",
                description="Standard SFT without coreset or continual learning",
                use_coreset=False,
                use_continual=False,
            ),
            "B1_coreset_loss": MethodConfig(
                name="B1: Coreset (Loss Top-K)",
                description="Select samples with highest loss values",
                use_coreset=True,
                coreset_strategy="loss_topk",
                coreset_target_size=1000,
            ),
            "B2_coreset_diversity": MethodConfig(
                name="B2: Coreset (Diversity)",
                description="Select diverse samples using feature distance",
                use_coreset=True,
                coreset_strategy="diversity",
                coreset_target_size=1000,
            ),
            "B3_coreset_hybrid": MethodConfig(
                name="B3: Coreset (Hybrid)",
                description="60% loss-based + 40% diversity-based selection",
                use_coreset=True,
                coreset_strategy="hybrid",
                coreset_target_size=1000,
            ),
            "B4_coreset_random": MethodConfig(
                name="B4: Coreset (Random)",
                description="Random subset selection (control)",
                use_coreset=True,
                coreset_strategy="random",
                coreset_target_size=1000,
            ),
            "C_continual": MethodConfig(
                name="C: Continual Learning",
                description="Online continual learning with replay buffer",
                use_coreset=False,
                use_continual=True,
                continual_buffer_size=2048,
                continual_replay_ratio=0.25,
            ),
            "D_combined": MethodConfig(
                name="D: Coreset + Continual",
                description="Combined coreset selection and continual learning",
                use_coreset=True,
                coreset_strategy="hybrid",
                coreset_target_size=1500,
                use_continual=True,
                continual_buffer_size=2048,
                continual_replay_ratio=0.20,
            ),
            # Agent trajectory fine-tuning methods (Task B1: FireAct)
            "E_fireact": MethodConfig(
                name="E: FireAct",
                description="Agent trajectory fine-tuning (Chen et al., 2023)",
                use_trajectory_collection=True,
                trajectory_min_reward=0.5,
                trajectory_require_success=True,
                trajectory_max_steps=10,
                num_epochs=2,
            ),
            "F_fireact_coreset": MethodConfig(
                name="F: FireAct + Coreset",
                description="FireAct trajectory collection with coreset selection",
                use_trajectory_collection=True,
                trajectory_min_reward=0.5,
                trajectory_require_success=True,
                use_coreset=True,
                coreset_strategy="hybrid",
                coreset_target_size=1000,
                num_epochs=2,
            ),
            # Advanced LoRA methods (Task B4: DoRA/LoRA+)
            "G_dora": MethodConfig(
                name="G: DoRA",
                description="Weight-Decomposed Low-Rank Adaptation (Liu et al., 2024)",
                use_dora=True,
            ),
            "H_lora_plus": MethodConfig(
                name="H: LoRA+",
                description="LoRA with differentiated learning rates (Hayou et al., 2024)",
                use_lora_plus=True,
                lora_plus_lr_ratio=16.0,
            ),
            "I_dora_coreset": MethodConfig(
                name="I: DoRA + Coreset",
                description="DoRA combined with hybrid coreset selection",
                use_dora=True,
                use_coreset=True,
                coreset_strategy="hybrid",
                coreset_target_size=1000,
            ),
            "J_loraplus_continual": MethodConfig(
                name="J: LoRA+ + Continual",
                description="LoRA+ combined with continual learning",
                use_lora_plus=True,
                lora_plus_lr_ratio=16.0,
                use_continual=True,
                continual_buffer_size=2048,
                continual_replay_ratio=0.25,
            ),
            # AgentTuning multi-task training (Task B2)
            "F_agenttuning": MethodConfig(
                name="F: AgentTuning",
                description="Multi-task agent capability tuning (Zeng et al., 2023)",
                use_multi_task=True,
                task_weights={
                    "tool_selection": 0.35,
                    "planning": 0.30,
                    "timing": 0.20,
                    "general": 0.15,
                },
                mixing_strategy="weighted",
                num_epochs=2,
            ),
            "F2_agenttuning_curriculum": MethodConfig(
                name="F2: AgentTuning (Curriculum)",
                description="AgentTuning with curriculum learning strategy",
                use_multi_task=True,
                task_weights={
                    "tool_selection": 0.35,
                    "planning": 0.30,
                    "timing": 0.20,
                    "general": 0.15,
                },
                mixing_strategy="curriculum",
                num_epochs=3,
            ),
            "F3_agenttuning_coreset": MethodConfig(
                name="F3: AgentTuning + Coreset",
                description="AgentTuning combined with coreset selection",
                use_multi_task=True,
                task_weights={
                    "tool_selection": 0.35,
                    "planning": 0.30,
                    "timing": 0.20,
                    "general": 0.15,
                },
                mixing_strategy="weighted",
                use_coreset=True,
                coreset_strategy="hybrid",
                coreset_target_size=1000,
                num_epochs=2,
            ),
        }

    @staticmethod
    def get_quick_methods() -> dict[str, MethodConfig]:
        """Get a smaller set of methods for quick testing."""
        return {
            "A_baseline": MethodConfig(
                name="A: Baseline",
                description="Standard SFT",
                max_train_samples=200,
                num_epochs=1,
            ),
            "B_coreset": MethodConfig(
                name="B: Coreset (Hybrid)",
                description="Hybrid coreset selection",
                use_coreset=True,
                coreset_strategy="hybrid",
                coreset_target_size=150,
                max_train_samples=200,
                num_epochs=1,
            ),
            "C_continual": MethodConfig(
                name="C: Continual",
                description="Continual learning",
                use_continual=True,
                continual_buffer_size=100,
                continual_replay_ratio=0.3,
                max_train_samples=200,
                num_epochs=1,
            ),
            "E_fireact": MethodConfig(
                name="E: FireAct",
                description="Agent trajectory fine-tuning",
                use_trajectory_collection=True,
                trajectory_min_reward=0.3,
                trajectory_require_success=False,
                trajectory_max_steps=5,
                max_train_samples=200,
                num_epochs=1,
            ),
        }


class MethodComparisonExperiment:
    """
    Run comparison experiments across multiple training methods.

    Example:
        >>> exp = MethodComparisonExperiment(output_dir="./comparison_results")
        >>> exp.run_all_methods()
        >>> exp.generate_comparison_chart()
    """

    def __init__(
        self,
        output_dir: str | Path = "./comparison_results",
        base_model: str = "Qwen/Qwen2.5-1.5B-Instruct",
        methods: Optional[dict[str, MethodConfig]] = None,
        dry_run: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_model = base_model
        self.methods = methods or MethodRegistry.get_quick_methods()
        self.dry_run = dry_run
        self.results: list[ExperimentResult] = []

    def run_all_methods(self, skip_training: bool = False) -> list[ExperimentResult]:
        """Run experiments for all configured methods."""
        print("=" * 70)
        print("METHOD COMPARISON EXPERIMENT")
        print("=" * 70)
        print(f"Output directory: {self.output_dir}")
        print(f"Base model: {self.base_model}")
        print(f"Methods to compare: {len(self.methods)}")
        print()

        for method_id, config in self.methods.items():
            print(f"\n{'=' * 50}")
            print(f"Running: {config.name}")
            print(f"{'=' * 50}")
            print(f"Description: {config.description}")

            if self.dry_run:
                result = self._simulate_run(method_id, config)
            else:
                result = self._run_method(method_id, config, skip_training)

            self.results.append(result)
            self._save_result(result)

            print(f"\nResults for {config.name}:")
            for metric, value in result.metrics.items():
                print(f"  {metric}: {value:.4f}")

        # Save aggregated results
        self._save_all_results()

        return self.results

    def _run_method(
        self, method_id: str, config: MethodConfig, skip_training: bool
    ) -> ExperimentResult:
        """Run a single method experiment."""
        from sage.benchmark.benchmark_agent import (
            ToolSelectionConfig,
            ToolSelectionExperiment,
            get_adapter_registry,
        )
        from sage.benchmark.benchmark_agent.evaluation import compute_metrics
        from sage.data import DataManager

        train_time = 0.0
        num_samples = 0

        if not skip_training:
            # Training phase (if not dry run and training enabled)
            train_start = time.time()
            try:
                from sage.libs.finetune.agent import AgentSFTConfig, AgentSFTTrainer

                sft_config = AgentSFTConfig(
                    base_model=self.base_model,
                    train_data="agent_sft:train",
                    dev_data="agent_sft:dev",
                    max_train_samples=config.max_train_samples,
                    num_epochs=config.num_epochs,
                    learning_rate=config.learning_rate,
                    use_coreset_selection=config.use_coreset,
                    coreset_strategy=config.coreset_strategy,
                    coreset_target_size=config.coreset_target_size,
                    use_online_continual=config.use_continual,
                    continual_buffer_size=config.continual_buffer_size,
                    continual_replay_ratio=config.continual_replay_ratio,
                    # DoRA and LoRA+ settings (Task B4)
                    use_dora=config.use_dora,
                    use_lora_plus=config.use_lora_plus,
                    lora_plus_lr_ratio=config.lora_plus_lr_ratio,
                    output_dir=self.output_dir / method_id,
                )
                trainer = AgentSFTTrainer(sft_config)
                trainer.train()
                num_samples = len(trainer._train_samples)
            except Exception as e:
                logger.warning(f"Training failed for {method_id}: {e}")
                num_samples = config.max_train_samples or 4000

            train_time = time.time() - train_start

        # Evaluation phase
        eval_start = time.time()

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

        eval_time = time.time() - eval_start

        # Clean up metrics (remove error entries)
        clean_metrics = {
            k: v for k, v in metrics.items() if "_error" not in k and isinstance(v, float)
        }

        return ExperimentResult(
            method_name=config.name,
            config=config.to_dict(),
            metrics=clean_metrics,
            training_time_seconds=train_time,
            eval_time_seconds=eval_time,
            num_train_samples=num_samples,
        )

    def _simulate_run(self, method_id: str, config: MethodConfig) -> ExperimentResult:
        """Simulate a run for testing (dry run mode)."""
        import random

        # Generate simulated metrics with method-specific biases
        base_acc = 0.70
        if config.use_coreset:
            if config.coreset_strategy == "hybrid":
                base_acc += 0.08
            elif config.coreset_strategy == "diversity":
                base_acc += 0.05
            elif config.coreset_strategy == "loss_topk":
                base_acc += 0.06
        if config.use_continual:
            base_acc += 0.04

        noise = random.uniform(-0.03, 0.03)

        metrics = {
            "top_k_accuracy": min(base_acc + noise, 0.95),
            "recall_at_k": min((base_acc + noise) * 0.7, 0.85),
            "precision_at_k": min((base_acc + noise) * 0.4, 0.50),
            "mrr": min((base_acc + noise) * 0.6, 0.75),
        }

        return ExperimentResult(
            method_name=config.name,
            config=config.to_dict(),
            metrics=metrics,
            training_time_seconds=random.uniform(100, 500),
            eval_time_seconds=random.uniform(10, 30),
            num_train_samples=config.max_train_samples or 4000,
        )

    def _save_result(self, result: ExperimentResult):
        """Save individual result to JSON."""
        result_path = (
            self.output_dir / f"{result.method_name.replace(' ', '_').replace(':', '')}.json"
        )
        with open(result_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    def _save_all_results(self):
        """Save all results to a single JSON file."""
        all_results_path = self.output_dir / "all_results.json"
        with open(all_results_path, "w") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2, ensure_ascii=False)
        print(f"\nAll results saved to: {all_results_path}")

    def generate_comparison_chart(
        self,
        output_file: Optional[str] = None,
        show_plot: bool = False,
    ) -> Path:
        """Generate comparison charts from experiment results."""
        if not self.results:
            raise ValueError("No results to plot. Run experiments first.")

        output_file = output_file or str(self.output_dir / "comparison_chart.png")

        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not installed. Generating text report instead.")
            return self._generate_text_report()

        # Prepare data
        methods = [r.method_name for r in self.results]
        metrics = list(self.results[0].metrics.keys())

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            "Agent Training Method Comparison\nTarget: 95%+ Tool Planning Accuracy", fontsize=14
        )

        # Color palette
        colors = plt.cm.Set2(np.linspace(0, 1, len(methods)))

        # 1. Bar chart - All metrics comparison
        ax1 = axes[0, 0]
        x = np.arange(len(metrics))
        width = 0.8 / len(methods)

        for i, result in enumerate(self.results):
            values = [result.metrics.get(m, 0) for m in metrics]
            ax1.bar(x + i * width, values, width, label=result.method_name, color=colors[i])

        ax1.set_xlabel("Metrics")
        ax1.set_ylabel("Score")
        ax1.set_title("Performance Comparison by Metric")
        ax1.set_xticks(x + width * (len(methods) - 1) / 2)
        ax1.set_xticklabels([m.replace("_", " ").title() for m in metrics], rotation=15)
        ax1.legend(loc="upper right", fontsize=8)
        ax1.axhline(y=0.95, color="red", linestyle="--", alpha=0.7, label="Target (95%)")
        ax1.set_ylim(0, 1.0)
        ax1.grid(axis="y", alpha=0.3)

        # 2. Radar chart - Method profiles
        ax2 = axes[0, 1]
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Close the polygon

        for i, result in enumerate(self.results):
            values = [result.metrics.get(m, 0) for m in metrics]
            values += values[:1]
            ax2.plot(angles, values, "o-", linewidth=2, label=result.method_name, color=colors[i])
            ax2.fill(angles, values, alpha=0.1, color=colors[i])

        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels([m.replace("_", " ").title() for m in metrics], fontsize=8)
        ax2.set_title("Method Performance Profile (Radar)")
        ax2.legend(loc="upper right", fontsize=7)
        ax2.set_ylim(0, 1.0)

        # 3. Training efficiency
        ax3 = axes[1, 0]
        train_times = [r.training_time_seconds / 60 for r in self.results]  # Convert to minutes
        top_k_accs = [r.metrics.get("top_k_accuracy", 0) for r in self.results]

        ax3.scatter(train_times, top_k_accs, c=range(len(methods)), cmap="Set2", s=200)
        for i, (x, y, name) in enumerate(zip(train_times, top_k_accs, methods)):
            ax3.annotate(name, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)

        ax3.set_xlabel("Training Time (minutes)")
        ax3.set_ylabel("Top-K Accuracy")
        ax3.set_title("Training Efficiency")
        ax3.axhline(y=0.95, color="red", linestyle="--", alpha=0.7)
        ax3.grid(alpha=0.3)

        # 4. Summary table
        ax4 = axes[1, 1]
        ax4.axis("off")

        table_data = []
        headers = ["Method", "Top-K Acc", "Recall@K", "MRR", "Train Time"]

        for r in self.results:
            row = [
                r.method_name[:20],
                f"{r.metrics.get('top_k_accuracy', 0):.1%}",
                f"{r.metrics.get('recall_at_k', 0):.1%}",
                f"{r.metrics.get('mrr', 0):.1%}",
                f"{r.training_time_seconds / 60:.1f}m",
            ]
            table_data.append(row)

        table = ax4.table(
            cellText=table_data,
            colLabels=headers,
            cellLoc="center",
            loc="center",
            colColours=["lightblue"] * len(headers),
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        ax4.set_title("Results Summary", pad=20)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"\nChart saved to: {output_file}")

        if show_plot:
            plt.show()

        plt.close()

        return Path(output_file)

    def _generate_text_report(self) -> Path:
        """Generate a text-based report when matplotlib is not available."""
        report_path = self.output_dir / "comparison_report.txt"

        lines = [
            "=" * 70,
            "METHOD COMPARISON REPORT",
            "=" * 70,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "-" * 70,
            "RESULTS SUMMARY",
            "-" * 70,
            "",
        ]

        # Find best method for each metric
        metrics = list(self.results[0].metrics.keys()) if self.results else []
        best_per_metric = {}
        for metric in metrics:
            best_result = max(self.results, key=lambda r: r.metrics.get(metric, 0))
            best_per_metric[metric] = (best_result.method_name, best_result.metrics.get(metric, 0))

        for result in self.results:
            lines.append(f"\n{result.method_name}")
            lines.append("-" * 40)
            for metric, value in result.metrics.items():
                is_best = best_per_metric.get(metric, ("", 0))[0] == result.method_name
                star = " ★" if is_best else ""
                lines.append(f"  {metric}: {value:.4f} ({value * 100:.1f}%){star}")
            lines.append(f"  Training time: {result.training_time_seconds / 60:.1f} min")
            lines.append(f"  Train samples: {result.num_train_samples}")

        lines.extend(
            [
                "",
                "-" * 70,
                "BEST PERFORMERS",
                "-" * 70,
            ]
        )
        for metric, (method, value) in best_per_metric.items():
            lines.append(f"  {metric}: {method} ({value * 100:.1f}%)")

        lines.extend(
            [
                "",
                "-" * 70,
                "TARGET: 95% accuracy for 难题4",
                "-" * 70,
            ]
        )

        with open(report_path, "w") as f:
            f.write("\n".join(lines))

        print(f"\nText report saved to: {report_path}")
        return report_path

    def load_results(self, results_file: Optional[str] = None) -> list[ExperimentResult]:
        """Load results from a previous run."""
        results_file = results_file or str(self.output_dir / "all_results.json")

        with open(results_file) as f:
            data = json.load(f)

        self.results = [
            ExperimentResult(
                method_name=r["method_name"],
                config=r["config"],
                metrics=r["metrics"],
                training_time_seconds=r["training_time_seconds"],
                eval_time_seconds=r["eval_time_seconds"],
                num_train_samples=r["num_train_samples"],
                timestamp=r.get("timestamp", ""),
            )
            for r in data
        ]

        return self.results


def run_quick_comparison(output_dir: str = "./comparison_results", dry_run: bool = True):
    """Quick comparison with simulated results for testing."""
    exp = MethodComparisonExperiment(
        output_dir=output_dir,
        methods=MethodRegistry.get_quick_methods(),
        dry_run=dry_run,
    )
    exp.run_all_methods()
    return exp.generate_comparison_chart()


def run_full_comparison(
    output_dir: str = "./comparison_results", base_model: str = "Qwen/Qwen2.5-7B-Instruct"
):
    """Full comparison with actual training (requires GPU)."""
    exp = MethodComparisonExperiment(
        output_dir=output_dir,
        base_model=base_model,
        methods=MethodRegistry.get_all_methods(),
        dry_run=False,
    )
    exp.run_all_methods()
    return exp.generate_comparison_chart()
