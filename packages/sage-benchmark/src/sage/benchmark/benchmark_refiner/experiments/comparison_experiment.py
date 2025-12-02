"""
Refiner Comparison Experiment
=============================

多算法对比评测实验，运行多种 Refiner 算法并生成对比报告。
支持多数据集批量运行。

重要：此模块调用真实的 RAG Pipeline 进行评测，通过 ResultsCollector 收集结果。
"""

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
    AlgorithmMetrics,
    BaseRefinerExperiment,
    ExperimentResult,
    RefinerExperimentConfig,
)
from sage.benchmark.benchmark_refiner.experiments.results_collector import (
    ResultsCollector,
)
from sage.common.utils.config.loader import load_config


@dataclass
class DatasetResult:
    """单个数据集的评测结果"""

    dataset: str
    algorithm_metrics: dict[str, AlgorithmMetrics] = field(default_factory=dict)
    raw_results: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "dataset": self.dataset,
            "algorithm_metrics": {
                name: metrics.to_dict() for name, metrics in self.algorithm_metrics.items()
            },
            "raw_results": self.raw_results if len(self.raw_results) <= 100 else [],
            "success": self.success,
            "error": self.error,
        }


@dataclass
class MultiDatasetExperimentResult:
    """
    多数据集实验结果

    扩展 ExperimentResult 以支持按数据集分组的结果。
    """

    experiment_id: str
    config: dict[str, Any]
    dataset_results: dict[str, DatasetResult] = field(default_factory=dict)
    aggregated_metrics: dict[str, AlgorithmMetrics] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    success: bool = True
    error: str = ""

    # 对比结果
    best_f1_algorithm: str = ""
    best_compression_algorithm: str = ""
    best_latency_algorithm: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "experiment_id": self.experiment_id,
            "config": self.config,
            "datasets": {name: result.to_dict() for name, result in self.dataset_results.items()},
            "aggregated": {
                name: metrics.to_dict() for name, metrics in self.aggregated_metrics.items()
            },
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error": self.error,
            "summary": {
                "best_f1_algorithm": self.best_f1_algorithm,
                "best_compression_algorithm": self.best_compression_algorithm,
                "best_latency_algorithm": self.best_latency_algorithm,
            },
        }

    def to_experiment_result(self) -> ExperimentResult:
        """
        转换为标准 ExperimentResult 以保持向后兼容性。

        使用聚合指标作为 algorithm_metrics。
        """
        all_raw_results = []
        for ds_result in self.dataset_results.values():
            for sample in ds_result.raw_results:
                sample["dataset"] = ds_result.dataset
                all_raw_results.append(sample)

        return ExperimentResult(
            experiment_id=self.experiment_id,
            config=self.config,
            algorithm_metrics=self.aggregated_metrics,
            raw_results=all_raw_results,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_seconds=self.duration_seconds,
            success=self.success,
            error=self.error,
            best_f1_algorithm=self.best_f1_algorithm,
            best_compression_algorithm=self.best_compression_algorithm,
            best_latency_algorithm=self.best_latency_algorithm,
        )


class ComparisonExperiment(BaseRefinerExperiment):
    """
    多算法对比实验

    对多种 Refiner 算法在同一数据集上进行评测，
    收集质量、压缩率、延迟等指标并生成对比报告。

    支持多数据集批量运行。

    使用示例:
        config = RefinerExperimentConfig(
            name="algorithm_comparison",
            algorithms=["baseline", "longrefiner", "reform", "provence"],
            datasets=["nq", "hotpotqa", "2wikimultihopqa"],
            max_samples=100,
            budget=2048,
        )
        experiment = ComparisonExperiment(config)
        result = experiment.run_full()
    """

    def __init__(self, config: RefinerExperimentConfig):
        super().__init__(config)
        self.sample_results: dict[str, list[dict[str, Any]]] = {}
        # 多数据集结果存储
        self.multi_dataset_result: MultiDatasetExperimentResult | None = None

    def run(self) -> ExperimentResult:
        """
        运行对比实验

        对每个数据集和每种算法：
        1. 加载对应的 Pipeline 配置
        2. 运行 Pipeline
        3. 收集评测指标

        Returns:
            ExperimentResult 包含所有算法的对比结果（聚合）
        """
        start_time = datetime.now()

        # 获取要运行的数据集列表
        datasets = self.config.get_datasets()

        # 初始化多数据集结果
        self.multi_dataset_result = MultiDatasetExperimentResult(
            experiment_id=self.experiment_id,
            config=self.config.to_dict(),
            start_time=start_time.isoformat(),
        )

        # 对每个数据集运行实验
        for dataset in datasets:
            self._log(f"\n{'=' * 50}")
            self._log(f"📊 Running on dataset: {dataset}")
            self._log(f"{'=' * 50}")

            dataset_result = self._run_on_dataset(dataset)
            self.multi_dataset_result.dataset_results[dataset] = dataset_result

        # 聚合跨数据集结果
        self._aggregate_results()

        end_time = datetime.now()
        self.multi_dataset_result.end_time = end_time.isoformat()
        self.multi_dataset_result.duration_seconds = (end_time - start_time).total_seconds()

        # 保存多数据集结果
        self._save_multi_dataset_result()

        # 返回标准 ExperimentResult（向后兼容）
        return self.multi_dataset_result.to_experiment_result()

    def _run_on_dataset(self, dataset: str) -> DatasetResult:
        """
        在单个数据集上运行所有算法的评测

        Args:
            dataset: 数据集名称

        Returns:
            DatasetResult 该数据集上所有算法的评测结果
        """
        result = DatasetResult(dataset=dataset)

        for algorithm in self.config.algorithms:
            self._log(f"\n{'─' * 40}")
            self._log(f"🔧 Running algorithm: {algorithm} on {dataset}")
            self._log(f"{'─' * 40}")

            try:
                metrics = self._run_algorithm(algorithm, dataset)
                result.algorithm_metrics[algorithm] = metrics
                self._log(
                    f"   ✅ Completed: F1={metrics.avg_f1:.4f}, "
                    f"Compression={metrics.avg_compression_rate:.2f}x"
                )
            except Exception as e:
                self._log(f"   ❌ Failed: {e}")
                # 记录失败但继续其他算法
                result.algorithm_metrics[algorithm] = AlgorithmMetrics(
                    algorithm=algorithm,
                    num_samples=0,
                )

        # 收集原始结果
        if self.config.save_raw_results:
            for algo, samples in self.sample_results.items():
                for sample in samples:
                    sample["algorithm"] = algo
                    sample["dataset"] = dataset
                    result.raw_results.append(sample)

        # 清空单数据集的临时结果
        self.sample_results.clear()

        return result

    def _aggregate_results(self) -> None:
        """
        聚合跨数据集的结果

        计算每个算法在所有数据集上的平均性能。
        """
        if self.multi_dataset_result is None:
            return

        # 收集每个算法在所有数据集上的指标
        algo_metrics_collection: dict[str, dict[str, list[float]]] = {}

        for ds_result in self.multi_dataset_result.dataset_results.values():
            for algo, metrics in ds_result.algorithm_metrics.items():
                if algo not in algo_metrics_collection:
                    algo_metrics_collection[algo] = {
                        "f1": [],
                        "compression_rate": [],
                        "total_time": [],
                        "retrieve_time": [],
                        "refine_time": [],
                        "generate_time": [],
                        "num_samples": [],
                    }

                if metrics.num_samples > 0:
                    algo_metrics_collection[algo]["f1"].append(metrics.avg_f1)
                    algo_metrics_collection[algo]["compression_rate"].append(
                        metrics.avg_compression_rate
                    )
                    algo_metrics_collection[algo]["total_time"].append(metrics.avg_total_time)
                    algo_metrics_collection[algo]["retrieve_time"].append(metrics.avg_retrieve_time)
                    algo_metrics_collection[algo]["refine_time"].append(metrics.avg_refine_time)
                    algo_metrics_collection[algo]["generate_time"].append(metrics.avg_generate_time)
                    algo_metrics_collection[algo]["num_samples"].append(metrics.num_samples)

        # 计算聚合指标
        for algo, metrics_dict in algo_metrics_collection.items():
            if not metrics_dict["f1"]:
                continue

            aggregated = AlgorithmMetrics(
                algorithm=algo,
                num_samples=int(sum(metrics_dict["num_samples"])),
                avg_f1=statistics.mean(metrics_dict["f1"]),
                avg_compression_rate=statistics.mean(metrics_dict["compression_rate"]),
                avg_total_time=statistics.mean(metrics_dict["total_time"]),
                avg_retrieve_time=statistics.mean(metrics_dict["retrieve_time"]),
                avg_refine_time=statistics.mean(metrics_dict["refine_time"]),
                avg_generate_time=statistics.mean(metrics_dict["generate_time"]),
            )

            # 计算标准差
            if len(metrics_dict["f1"]) > 1:
                aggregated.std_f1 = statistics.stdev(metrics_dict["f1"])
                aggregated.std_compression_rate = statistics.stdev(metrics_dict["compression_rate"])
                aggregated.std_total_time = statistics.stdev(metrics_dict["total_time"])

            self.multi_dataset_result.aggregated_metrics[algo] = aggregated

        # 确定最佳算法
        if self.multi_dataset_result.aggregated_metrics:
            best_f1 = max(
                self.multi_dataset_result.aggregated_metrics.items(),
                key=lambda x: x[1].avg_f1,
            )
            self.multi_dataset_result.best_f1_algorithm = best_f1[0]

            best_compression = max(
                self.multi_dataset_result.aggregated_metrics.items(),
                key=lambda x: x[1].avg_compression_rate,
            )
            self.multi_dataset_result.best_compression_algorithm = best_compression[0]

            best_latency = min(
                self.multi_dataset_result.aggregated_metrics.items(),
                key=lambda x: x[1].avg_total_time if x[1].avg_total_time > 0 else float("inf"),
            )
            self.multi_dataset_result.best_latency_algorithm = best_latency[0]

    def _save_multi_dataset_result(self) -> None:
        """保存多数据集结果到单独的 JSON 文件"""
        import json

        if self.multi_dataset_result is None:
            return

        result_path = self.output_dir / "multi_dataset_results.json"
        with open(result_path, "w") as f:
            json.dump(self.multi_dataset_result.to_dict(), f, indent=2, ensure_ascii=False)
        self._log(f"💾 Multi-dataset results saved to: {result_path}")

    def _run_algorithm(self, algorithm: str, dataset: str = "") -> AlgorithmMetrics:
        """
        运行单个算法的评测

        Args:
            algorithm: 算法名称
            dataset: 数据集名称（用于日志）

        Returns:
            AlgorithmMetrics 该算法的评测指标
        """
        # 收集每个样本的指标
        f1_scores: list[float] = []
        compression_rates: list[float] = []
        original_tokens_list: list[float] = []
        compressed_tokens_list: list[float] = []
        retrieve_times: list[float] = []
        refine_times: list[float] = []
        generate_times: list[float] = []
        total_times: list[float] = []

        # 这里我们模拟运行 Pipeline 并收集结果
        # 实际实现中会调用对应的 Pipeline
        sample_results = self._execute_pipeline(algorithm, dataset)
        self.sample_results[algorithm] = sample_results

        for sample in sample_results:
            if "f1" in sample:
                f1_scores.append(sample["f1"])
            if "compression_rate" in sample:
                compression_rates.append(sample["compression_rate"])
            if "original_tokens" in sample:
                original_tokens_list.append(sample["original_tokens"])
            if "compressed_tokens" in sample:
                compressed_tokens_list.append(sample["compressed_tokens"])
            if "retrieve_time" in sample:
                retrieve_times.append(sample["retrieve_time"])
            if "refine_time" in sample:
                refine_times.append(sample["refine_time"])
            if "generate_time" in sample:
                generate_times.append(sample["generate_time"])
            if "total_time" in sample:
                total_times.append(sample["total_time"])

        # 计算统计指标
        metrics = AlgorithmMetrics(
            algorithm=algorithm,
            num_samples=len(sample_results),
        )

        if f1_scores:
            metrics.avg_f1 = statistics.mean(f1_scores)
            metrics.std_f1 = statistics.stdev(f1_scores) if len(f1_scores) > 1 else 0.0

        if compression_rates:
            metrics.avg_compression_rate = statistics.mean(compression_rates)
            metrics.std_compression_rate = (
                statistics.stdev(compression_rates) if len(compression_rates) > 1 else 0.0
            )

        if original_tokens_list:
            metrics.avg_original_tokens = statistics.mean(original_tokens_list)

        if compressed_tokens_list:
            metrics.avg_compressed_tokens = statistics.mean(compressed_tokens_list)

        if retrieve_times:
            metrics.avg_retrieve_time = statistics.mean(retrieve_times)

        if refine_times:
            metrics.avg_refine_time = statistics.mean(refine_times)

        if generate_times:
            metrics.avg_generate_time = statistics.mean(generate_times)

        if total_times:
            metrics.avg_total_time = statistics.mean(total_times)
            metrics.std_total_time = statistics.stdev(total_times) if len(total_times) > 1 else 0.0

        return metrics

    def _execute_pipeline(self, algorithm: str, dataset: str = "") -> list[dict[str, Any]]:
        """
        执行真实 Pipeline 并收集结果

        通过 ResultsCollector 收集评测 Operators 产生的指标。

        Args:
            algorithm: 算法名称
            dataset: 数据集名称

        Returns:
            每个样本的评测结果列表
        """
        dataset_info = f" ({dataset})" if dataset else ""
        self._log(f"   📊 Running real pipeline for {algorithm}{dataset_info}...")

        # 1. 加载并修改配置
        config = self._load_and_modify_config(algorithm, dataset)

        # 2. 重置 ResultsCollector
        collector = ResultsCollector()
        collector.reset()
        collector.set_metadata(
            algorithm=algorithm,
            dataset=dataset,
            max_samples=self.config.max_samples,
        )

        # 3. 运行 Pipeline
        try:
            self._run_pipeline_module(algorithm, config)
        except Exception as e:
            self._log(f"   ⚠️ Pipeline error: {e}")
            # 返回空结果
            return []

        # 4. 从 ResultsCollector 获取结果
        results = collector.get_results()
        self._log(f"   ✅ Collected {len(results)} sample results")

        return results

    def _load_and_modify_config(self, algorithm: str, dataset: str = "") -> dict[str, Any]:
        """
        加载算法配置并修改实验参数

        Args:
            algorithm: 算法名称
            dataset: 数据集名称

        Returns:
            修改后的配置字典
        """
        # 配置文件路径
        config_dir = Path(__file__).parent.parent / "config"
        config_filename = f"config_{algorithm}.yaml"
        config_path = config_dir / config_filename

        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}. "
                f"Please create config_{algorithm}.yaml for algorithm '{algorithm}'."
            )

        # 加载配置
        config = load_config(str(config_path))

        # 修改 source.max_samples
        if "source" in config:
            config["source"]["max_samples"] = self.config.max_samples

        # 修改 source.hf_dataset_config（如果指定了数据集）
        if dataset and "source" in config:
            config["source"]["hf_dataset_config"] = dataset
            self._log(f"   📁 Using dataset: {dataset}")

        return config

    def _run_pipeline_module(self, algorithm: str, config: dict[str, Any]) -> None:
        """
        运行指定算法的 Pipeline

        根据算法名称动态导入对应的 Pipeline 模块并执行。
        使用 time.sleep() 等待 Pipeline 完成。

        Args:
            algorithm: 算法名称
            config: Pipeline 配置

        Raises:
            ValueError: 如果算法不支持
        """
        # 算法到 Pipeline 模块的映射
        pipeline_mapping = {
            "baseline": "baseline_rag",
            "longrefiner": "longrefiner_rag",
            "reform": "reform_rag",
            "provence": "provence_rag",
            "longllmlingua": "longllmlingua_rag",
            "llmlingua2": "llmlingua2_rag",
        }

        if algorithm not in pipeline_mapping:
            raise ValueError(
                f"Unknown algorithm: {algorithm}. Supported: {list(pipeline_mapping.keys())}"
            )

        module_name = pipeline_mapping[algorithm]
        self._log(f"   🚀 Starting {module_name} pipeline...")

        # 动态导入 Pipeline 模块
        if algorithm == "baseline":
            from sage.benchmark.benchmark_refiner.implementations.pipelines.baseline_rag import (
                pipeline_run,
            )
        elif algorithm == "longrefiner":
            from sage.benchmark.benchmark_refiner.implementations.pipelines.longrefiner_rag import (
                pipeline_run,
            )
        elif algorithm == "reform":
            from sage.benchmark.benchmark_refiner.implementations.pipelines.reform_rag import (
                pipeline_run,
            )
        elif algorithm == "provence":
            from sage.benchmark.benchmark_refiner.implementations.pipelines.provence_rag import (
                pipeline_run,
            )
        elif algorithm == "longllmlingua":
            from sage.benchmark.benchmark_refiner.implementations.pipelines.longllmlingua_rag import (
                pipeline_run,
            )
        elif algorithm == "llmlingua2":
            from sage.benchmark.benchmark_refiner.implementations.pipelines.llmlingua2_rag import (
                pipeline_run,
            )

        # 计算预估等待时间
        # 基于样本数和算法复杂度估算
        base_time_per_sample = {
            "baseline": 3,  # 秒/样本
            "longrefiner": 10,
            "reform": 5,
            "provence": 4,
            "longllmlingua": 15,
            "llmlingua2": 4,
        }
        estimated_time = (
            self.config.max_samples * base_time_per_sample.get(algorithm, 5) + 60
        )  # 额外 60 秒缓冲

        self._log(f"   ⏱️ Estimated time: {estimated_time}s ({estimated_time // 60}min)")

        # 运行 Pipeline（在单独的过程中运行）
        pipeline_run(config)

        # 等待 Pipeline 完成
        # 使用 time.sleep() 是设计要求
        time.sleep(estimated_time)

        self._log(f"   ✅ Pipeline {module_name} completed")


class QualityExperiment(BaseRefinerExperiment):
    """
    质量评测实验

    专注于评测 Refiner 对答案质量的影响：
    - F1 Score
    - Recall
    - ROUGE-L
    - Accuracy
    """

    def run(self) -> ExperimentResult:
        """运行质量评测实验"""
        # 使用 ComparisonExperiment 的逻辑，但专注于质量指标
        comparison = ComparisonExperiment(self.config)
        return comparison.run()


class LatencyExperiment(BaseRefinerExperiment):
    """
    延迟评测实验

    专注于评测 Refiner 的延迟表现：
    - Retrieve Time
    - Refine Time
    - Generate Time
    - End-to-End Latency
    """

    def run(self) -> ExperimentResult:
        """运行延迟评测实验"""
        # 使用 ComparisonExperiment 的逻辑，但专注于延迟指标
        comparison = ComparisonExperiment(self.config)
        return comparison.run()


class CompressionExperiment(BaseRefinerExperiment):
    """
    压缩率评测实验

    专注于评测 Refiner 的压缩效果：
    - Compression Rate
    - Original Tokens
    - Compressed Tokens
    - Token Budget 遵守情况
    """

    def run(self) -> ExperimentResult:
        """运行压缩率评测实验"""
        # 使用 ComparisonExperiment 的逻辑，但专注于压缩指标
        comparison = ComparisonExperiment(self.config)
        return comparison.run()
