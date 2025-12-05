"""
Refiner Experiment Runner
=========================

统一的实验运行器，支持命令行和编程方式运行实验。
"""

import json
from pathlib import Path
from typing import Any

from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
    ExperimentResult,
    RefinerExperimentConfig,
)
from sage.benchmark.benchmark_refiner.experiments.comparison_experiment import (
    ComparisonExperiment,
    CompressionExperiment,
    LatencyExperiment,
    QualityExperiment,
)


class RefinerExperimentRunner:
    """
    Refiner 实验运行器

    提供统一的接口运行各种类型的 Refiner 评测实验。

    使用示例:
        # 方式1: 从配置文件运行
        runner = RefinerExperimentRunner()
        result = runner.run_from_config("config.yaml")

        # 方式2: 从配置对象运行
        config = RefinerExperimentConfig(
            name="my_experiment",
            algorithms=["baseline", "longrefiner"],
        )
        result = runner.run(config)

        # 方式3: 快速对比
        result = runner.quick_compare(
            algorithms=["baseline", "longrefiner", "reform"],
            max_samples=50,
        )
    """

    EXPERIMENT_TYPES = {
        "comparison": ComparisonExperiment,
        "quality": QualityExperiment,
        "latency": LatencyExperiment,
        "compression": CompressionExperiment,
    }

    def __init__(self, verbose: bool = True):
        """
        初始化运行器

        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose

    def _log(self, message: str) -> None:
        """日志输出"""
        if self.verbose:
            print(message)

    def run(
        self,
        config: RefinerExperimentConfig,
        experiment_type: str = "comparison",
    ) -> ExperimentResult:
        """
        运行实验

        Args:
            config: 实验配置
            experiment_type: 实验类型 (comparison, quality, latency, compression)

        Returns:
            ExperimentResult
        """
        if experiment_type not in self.EXPERIMENT_TYPES:
            raise ValueError(
                f"Unknown experiment type: {experiment_type}. "
                f"Available: {list(self.EXPERIMENT_TYPES.keys())}"
            )

        experiment_class = self.EXPERIMENT_TYPES[experiment_type]
        experiment = experiment_class(config)

        return experiment.run_full()

    def run_from_config(
        self,
        config_path: str,
        experiment_type: str = "comparison",
    ) -> ExperimentResult:
        """
        从配置文件运行实验

        Args:
            config_path: 配置文件路径 (YAML)
            experiment_type: 实验类型

        Returns:
            ExperimentResult
        """
        config = RefinerExperimentConfig.from_yaml(config_path)
        return self.run(config, experiment_type)

    def run_from_dict(
        self,
        config_dict: dict[str, Any],
        experiment_type: str = "comparison",
    ) -> ExperimentResult:
        """
        从字典运行实验

        Args:
            config_dict: 配置字典
            experiment_type: 实验类型

        Returns:
            ExperimentResult
        """
        config = RefinerExperimentConfig.from_dict(config_dict)
        return self.run(config, experiment_type)

    def quick_compare(
        self,
        algorithms: list[str] | None = None,
        max_samples: int = 50,
        budget: int = 2048,
        datasets: list[str] | None = None,
        dataset: str | None = None,  # 向后兼容
        output_dir: str = "./.benchmarks/refiner",
    ) -> ExperimentResult:
        """
        快速对比多种算法

        Args:
            algorithms: 要对比的算法列表，默认为所有已实现算法
            max_samples: 最大样本数
            budget: Token 预算
            datasets: 数据集列表
            dataset: 单个数据集名称 (向后兼容)
            output_dir: 输出目录

        Returns:
            ExperimentResult
        """
        if algorithms is None:
            algorithms = ["baseline", "longrefiner", "reform", "provence"]

        # 处理数据集参数：支持新的 datasets 和旧的 dataset
        if datasets is None:
            if dataset is not None:
                datasets = [dataset]
            else:
                datasets = ["nq"]

        config = RefinerExperimentConfig(
            name="quick_comparison",
            algorithms=algorithms,
            max_samples=max_samples,
            budget=budget,
            datasets=datasets,
            dataset_config=datasets[0],  # 保持向后兼容
            output_dir=output_dir,
            verbose=self.verbose,
        )

        return self.run(config, "comparison")

    def compare_budgets(
        self,
        algorithm: str,
        budgets: list[int],
        max_samples: int = 50,
        output_dir: str = "./.benchmarks/refiner",
    ) -> dict[int, ExperimentResult]:
        """
        对比不同 budget 下的表现

        Args:
            algorithm: 算法名称
            budgets: 要测试的 budget 列表
            max_samples: 最大样本数
            output_dir: 输出目录

        Returns:
            {budget: ExperimentResult} 字典
        """
        results = {}

        for budget in budgets:
            self._log(f"\n📊 Testing budget: {budget}")

            config = RefinerExperimentConfig(
                name=f"budget_sweep_{algorithm}_{budget}",
                algorithms=[algorithm],
                max_samples=max_samples,
                budget=budget,
                output_dir=output_dir,
                verbose=self.verbose,
            )

            result = self.run(config, "compression")
            results[budget] = result

        return results

    def run_sweep(
        self,
        algorithms: list[str],
        budgets: list[int],
        max_samples: int = 50,
        output_dir: str = "./.benchmarks/refiner",
    ) -> dict[str, dict[int, ExperimentResult]]:
        """
        运行完整的参数扫描

        Args:
            algorithms: 算法列表
            budgets: budget 列表
            max_samples: 最大样本数
            output_dir: 输出目录

        Returns:
            {algorithm: {budget: ExperimentResult}} 嵌套字典
        """
        all_results = {}

        for algorithm in algorithms:
            self._log(f"\n{'=' * 60}")
            self._log(f"🔧 Sweeping algorithm: {algorithm}")
            self._log(f"{'=' * 60}")

            all_results[algorithm] = self.compare_budgets(
                algorithm=algorithm,
                budgets=budgets,
                max_samples=max_samples,
                output_dir=output_dir,
            )

        # 保存汇总结果
        summary_path = Path(output_dir) / "sweep_summary.json"
        summary = {
            algo: {str(budget): result.to_dict() for budget, result in budget_results.items()}
            for algo, budget_results in all_results.items()
        }

        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        self._log(f"\n💾 Sweep summary saved to: {summary_path}")

        return all_results

    @staticmethod
    def print_comparison_table(result: ExperimentResult) -> None:
        """
        打印对比表格

        Args:
            result: 实验结果
        """
        # 检查是否有多数据集信息
        config = result.config
        datasets = config.get("datasets", [config.get("dataset_config", "unknown")])

        print("\n" + "=" * 80)
        print("                    Refiner Algorithm Comparison")
        if len(datasets) > 1:
            print(f"                    Datasets: {', '.join(datasets)}")
        print("=" * 80)

        headers = ["Algorithm", "F1 Score", "Compression", "Latency (s)", "Samples"]
        header_line = "| " + " | ".join(f"{h:^12}" for h in headers) + " |"
        print(header_line)
        print("|" + "|".join("-" * 14 for _ in headers) + "|")

        for name, metrics in result.algorithm_metrics.items():
            row = [
                name[:12],
                f"{metrics.avg_f1:.4f}",
                f"{metrics.avg_compression_rate:.2f}x",
                f"{metrics.avg_total_time:.2f}",
                str(metrics.num_samples),
            ]
            row_line = "| " + " | ".join(f"{v:^12}" for v in row) + " |"
            print(row_line)

        print("=" * 80)

        # 打印最佳算法
        print(f"\n🏆 Best F1: {result.best_f1_algorithm}")
        print(f"🏆 Best Compression: {result.best_compression_algorithm}")
        print(f"🏆 Best Latency: {result.best_latency_algorithm}")

    @staticmethod
    def print_multi_dataset_table(
        result: "MultiDatasetExperimentResult",  # noqa: F821
    ) -> None:
        """
        打印多数据集对比表格

        Args:
            result: 多数据集实验结果
        """
        from sage.benchmark.benchmark_refiner.experiments.comparison_experiment import (
            MultiDatasetExperimentResult,
        )

        if not isinstance(result, MultiDatasetExperimentResult):
            # 回退到单数据集表格
            RefinerExperimentRunner.print_comparison_table(result)
            return

        # 打印每个数据集的结果
        for dataset, ds_result in result.dataset_results.items():
            print(f"\n{'=' * 60}")
            print(f"                Dataset: {dataset}")
            print("=" * 60)

            headers = ["Algorithm", "F1", "Compression", "Latency"]
            print("| " + " | ".join(f"{h:^12}" for h in headers) + " |")
            print("|" + "|".join("-" * 14 for _ in headers) + "|")

            for name, metrics in ds_result.algorithm_metrics.items():
                row = [
                    name[:12],
                    f"{metrics.avg_f1:.4f}",
                    f"{metrics.avg_compression_rate:.2f}x",
                    f"{metrics.avg_total_time:.2f}s",
                ]
                print("| " + " | ".join(f"{v:^12}" for v in row) + " |")

        # 打印聚合结果
        print(f"\n{'=' * 60}")
        print("                Aggregated Results (Cross-Dataset Average)")
        print("=" * 60)

        headers = ["Algorithm", "F1", "Compression", "Latency", "Total Samples"]
        print("| " + " | ".join(f"{h:^12}" for h in headers) + " |")
        print("|" + "|".join("-" * 14 for _ in headers) + "|")

        for name, metrics in result.aggregated_metrics.items():
            row = [
                name[:12],
                f"{metrics.avg_f1:.4f}",
                f"{metrics.avg_compression_rate:.2f}x",
                f"{metrics.avg_total_time:.2f}s",
                str(metrics.num_samples),
            ]
            print("| " + " | ".join(f"{v:^12}" for v in row) + " |")

        print("=" * 60)
        print(f"\n🏆 Best F1: {result.best_f1_algorithm}")
        print(f"🏆 Best Compression: {result.best_compression_algorithm}")
        print(f"🏆 Best Latency: {result.best_latency_algorithm}")

    @staticmethod
    def generate_latex_table(result: ExperimentResult) -> str:
        """
        生成 LaTeX 表格

        Args:
            result: 实验结果

        Returns:
            LaTeX 表格字符串
        """
        lines = [
            r"\begin{table}[h]",
            r"\centering",
            r"\caption{Refiner Algorithm Comparison}",
            r"\label{tab:refiner-comparison}",
            r"\begin{tabular}{lcccc}",
            r"\toprule",
            r"Algorithm & F1 Score & Compression & Latency (s) & Samples \\",
            r"\midrule",
        ]

        for name, metrics in result.algorithm_metrics.items():
            # 标记最佳值
            f1_str = f"{metrics.avg_f1:.4f}"
            comp_str = f"{metrics.avg_compression_rate:.2f}x"
            lat_str = f"{metrics.avg_total_time:.2f}"

            if name == result.best_f1_algorithm:
                f1_str = r"\textbf{" + f1_str + "}"
            if name == result.best_compression_algorithm:
                comp_str = r"\textbf{" + comp_str + "}"
            if name == result.best_latency_algorithm:
                lat_str = r"\textbf{" + lat_str + "}"

            lines.append(f"{name} & {f1_str} & {comp_str} & {lat_str} & {metrics.num_samples} \\\\")

        lines.extend(
            [
                r"\bottomrule",
                r"\end{tabular}",
                r"\end{table}",
            ]
        )

        return "\n".join(lines)
