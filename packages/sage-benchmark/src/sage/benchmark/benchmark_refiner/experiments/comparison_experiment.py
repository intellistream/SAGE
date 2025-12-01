"""
Refiner Comparison Experiment
=============================

多算法对比评测实验，运行多种 Refiner 算法并生成对比报告。
"""

import statistics
import time
from datetime import datetime
from typing import Any

from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
    AlgorithmMetrics,
    BaseRefinerExperiment,
    ExperimentResult,
    RefinerExperimentConfig,
)


class ComparisonExperiment(BaseRefinerExperiment):
    """
    多算法对比实验

    对多种 Refiner 算法在同一数据集上进行评测，
    收集质量、压缩率、延迟等指标并生成对比报告。

    使用示例:
        config = RefinerExperimentConfig(
            name="algorithm_comparison",
            algorithms=["baseline", "longrefiner", "reform", "provence"],
            max_samples=100,
            budget=2048,
        )
        experiment = ComparisonExperiment(config)
        result = experiment.run_full()
    """

    def __init__(self, config: RefinerExperimentConfig):
        super().__init__(config)
        self.sample_results: dict[str, list[dict[str, Any]]] = {}

    def run(self) -> ExperimentResult:
        """
        运行对比实验

        对每种算法：
        1. 加载对应的 Pipeline 配置
        2. 运行 Pipeline
        3. 收集评测指标

        Returns:
            ExperimentResult 包含所有算法的对比结果
        """
        start_time = datetime.now()

        result = ExperimentResult(
            experiment_id=self.experiment_id,
            config=self.config.to_dict(),
            start_time=start_time.isoformat(),
        )

        for algorithm in self.config.algorithms:
            self._log(f"\n{'─' * 40}")
            self._log(f"🔧 Running algorithm: {algorithm}")
            self._log(f"{'─' * 40}")

            try:
                metrics = self._run_algorithm(algorithm)
                result.algorithm_metrics[algorithm] = metrics
                self._log(f"   ✅ Completed: F1={metrics.avg_f1:.4f}, "
                         f"Compression={metrics.avg_compression_rate:.2f}x")
            except Exception as e:
                self._log(f"   ❌ Failed: {e}")
                # 记录失败但继续其他算法
                result.algorithm_metrics[algorithm] = AlgorithmMetrics(
                    algorithm=algorithm,
                    num_samples=0,
                )

        end_time = datetime.now()
        result.end_time = end_time.isoformat()
        result.duration_seconds = (end_time - start_time).total_seconds()

        # 收集原始结果
        if self.config.save_raw_results:
            for algo, samples in self.sample_results.items():
                for sample in samples:
                    sample["algorithm"] = algo
                    result.raw_results.append(sample)

        return result

    def _run_algorithm(self, algorithm: str) -> AlgorithmMetrics:
        """
        运行单个算法的评测

        Args:
            algorithm: 算法名称

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
        sample_results = self._execute_pipeline(algorithm)
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

    def _execute_pipeline(self, algorithm: str) -> list[dict[str, Any]]:
        """
        执行指定算法的 Pipeline

        实际实现中会：
        1. 加载对应配置文件
        2. 创建 Pipeline
        3. 运行并收集结果

        Args:
            algorithm: 算法名称

        Returns:
            每个样本的评测结果列表
        """
        # TODO: 集成实际的 Pipeline 执行
        # 当前返回占位数据，实际使用时需要替换为真实 Pipeline 调用

        self._log(f"   📊 Processing {self.config.max_samples} samples...")

        results = []
        for i in range(min(self.config.max_samples, 10)):  # 演示用，限制数量
            # 模拟单个样本的处理
            sample_start = time.time()

            # 这里应该调用实际的 Pipeline
            # 目前使用占位数据
            sample_result = self._process_sample_placeholder(algorithm, i)

            sample_result["total_time"] = time.time() - sample_start
            results.append(sample_result)

            if (i + 1) % 10 == 0:
                self._log(f"   ... processed {i + 1}/{self.config.max_samples} samples")

        return results

    def _process_sample_placeholder(self, algorithm: str, sample_idx: int) -> dict[str, Any]:
        """
        处理单个样本的占位实现

        实际使用时应替换为真实的 Pipeline 调用。
        """
        import random

        random.seed(self.config.seed + sample_idx)

        # 模拟不同算法的特性
        base_f1 = 0.35

        if algorithm == "baseline":
            f1_bonus = 0.0
            compression = 1.0
            refine_time = 0.0
        elif algorithm == "longrefiner":
            f1_bonus = 0.03 + random.uniform(-0.02, 0.02)
            compression = 3.0 + random.uniform(-0.5, 0.5)
            refine_time = 0.8 + random.uniform(-0.2, 0.2)
        elif algorithm == "reform":
            f1_bonus = 0.01 + random.uniform(-0.02, 0.02)
            compression = 2.5 + random.uniform(-0.3, 0.3)
            refine_time = 0.3 + random.uniform(-0.1, 0.1)
        elif algorithm == "provence":
            f1_bonus = 0.02 + random.uniform(-0.02, 0.02)
            compression = 2.0 + random.uniform(-0.3, 0.3)
            refine_time = 0.1 + random.uniform(-0.05, 0.05)
        else:
            f1_bonus = 0.0
            compression = 1.0
            refine_time = 0.0

        original_tokens = 5000 + random.randint(-1000, 1000)
        compressed_tokens = int(original_tokens / compression)

        return {
            "sample_idx": sample_idx,
            "f1": base_f1 + f1_bonus + random.uniform(-0.05, 0.05),
            "compression_rate": compression,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "retrieve_time": 1.5 + random.uniform(-0.5, 0.5),
            "refine_time": refine_time,
            "generate_time": 1.0 + random.uniform(-0.3, 0.3),
        }


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
