# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Parallelism strategies for model execution."""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .types import ExecutionInstance, ParallelismType, RequestMetadata


@dataclass
class ParallelismConfig:
    """Configuration for parallelism strategy."""

    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    data_parallel_size: int = 1
    expert_parallel_size: int = 1

    # Advanced configurations
    sequence_parallel: bool = False
    context_parallel_size: int = 1

    # Resource constraints
    total_gpus: int = 1
    gpu_memory_gb: float = 0.0

    # Performance hints
    model_size_gb: float = 0.0
    max_seq_length: int = 2048
    batch_size: int = 1

    def validate(self) -> bool:
        """Validate configuration."""
        total_parallelism = (
            self.tensor_parallel_size
            * self.pipeline_parallel_size
            * self.data_parallel_size
            * self.expert_parallel_size
        )
        return total_parallelism <= self.total_gpus

    @property
    def total_parallel_size(self) -> int:
        """Calculate total parallelism degree."""
        return (
            self.tensor_parallel_size
            * self.pipeline_parallel_size
            * self.data_parallel_size
            * self.expert_parallel_size
        )


class ParallelismStrategy(ABC):
    """Base class for parallelism strategies."""

    def __init__(self, name: str, strategy_type: ParallelismType):
        self.name = name
        self.strategy_type = strategy_type

    @abstractmethod
    def optimize(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> ParallelismConfig:
        """
        Optimize parallelism configuration for a request.

        Args:
            request: The inference request
            instance: Target execution instance
            available_gpus: Number of available GPUs

        Returns:
            Optimized parallelism configuration
        """
        pass

    @abstractmethod
    def estimate_performance(
        self,
        config: ParallelismConfig,
        request: RequestMetadata,
    ) -> dict[str, float]:
        """
        Estimate performance metrics for a configuration.

        Returns:
            Dict with keys: 'latency_ms', 'throughput_tokens_per_sec', 'gpu_utilization'
        """
        pass


class TensorParallelStrategy(ParallelismStrategy):
    """Tensor parallelism strategy - splits model weights across GPUs."""

    def __init__(self):
        super().__init__("TensorParallel", ParallelismType.TENSOR_PARALLEL)

    def optimize(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> ParallelismConfig:
        """Optimize tensor parallelism size."""

        # Tensor parallelism works best with powers of 2
        tp_size = self._find_optimal_tp_size(available_gpus)

        config = ParallelismConfig(
            tensor_parallel_size=tp_size,
            pipeline_parallel_size=1,
            data_parallel_size=1,
            total_gpus=available_gpus,
            gpu_memory_gb=instance.gpu_memory_gb,
        )

        return config

    def _find_optimal_tp_size(self, available_gpus: int) -> int:
        """Find optimal tensor parallel size (power of 2)."""
        # Prefer powers of 2: 1, 2, 4, 8, 16, ...
        tp_size = 1
        while tp_size * 2 <= available_gpus:
            tp_size *= 2
        return tp_size

    def estimate_performance(
        self,
        config: ParallelismConfig,
        request: RequestMetadata,
    ) -> dict[str, float]:
        """Estimate performance for tensor parallelism."""

        # Tensor parallelism has communication overhead
        communication_overhead = 1.0 + (0.1 * math.log2(config.tensor_parallel_size))

        # Estimate speedup (sublinear due to communication)
        speedup = config.tensor_parallel_size / communication_overhead

        base_latency_ms = 100.0  # Base latency
        estimated_latency = base_latency_ms / speedup

        return {
            "latency_ms": estimated_latency,
            "throughput_tokens_per_sec": 100.0 * speedup,
            "gpu_utilization": 0.8,
        }


class PipelineParallelStrategy(ParallelismStrategy):
    """Pipeline parallelism strategy - splits model layers across GPUs."""

    def __init__(self):
        super().__init__("PipelineParallel", ParallelismType.PIPELINE_PARALLEL)

    def optimize(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> ParallelismConfig:
        """Optimize pipeline parallelism size."""

        # Pipeline parallelism for large models
        pp_size = min(available_gpus, 4)  # Cap at 4 for pipeline

        config = ParallelismConfig(
            tensor_parallel_size=1,
            pipeline_parallel_size=pp_size,
            data_parallel_size=1,
            total_gpus=available_gpus,
            gpu_memory_gb=instance.gpu_memory_gb,
        )

        return config

    def estimate_performance(
        self,
        config: ParallelismConfig,
        request: RequestMetadata,
    ) -> dict[str, float]:
        """Estimate performance for pipeline parallelism."""

        # Pipeline parallelism has bubble overhead
        bubble_overhead = 1.0 + (0.15 * config.pipeline_parallel_size)

        # Memory efficiency improved

        base_latency_ms = 100.0
        estimated_latency = base_latency_ms * bubble_overhead

        return {
            "latency_ms": estimated_latency,
            "throughput_tokens_per_sec": 80.0 / bubble_overhead,
            "gpu_utilization": 0.7,
        }


class DataParallelStrategy(ParallelismStrategy):
    """Data parallelism strategy - replicates model across GPUs."""

    def __init__(self):
        super().__init__("DataParallel", ParallelismType.DATA_PARALLEL)

    def optimize(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> ParallelismConfig:
        """Optimize data parallelism size."""

        # Use all available GPUs for data parallelism
        dp_size = available_gpus

        config = ParallelismConfig(
            tensor_parallel_size=1,
            pipeline_parallel_size=1,
            data_parallel_size=dp_size,
            total_gpus=available_gpus,
            gpu_memory_gb=instance.gpu_memory_gb,
        )

        return config

    def estimate_performance(
        self,
        config: ParallelismConfig,
        request: RequestMetadata,
    ) -> dict[str, float]:
        """Estimate performance for data parallelism."""

        # Data parallelism scales well for throughput
        throughput_multiplier = config.data_parallel_size * 0.95

        base_latency_ms = 100.0

        return {
            "latency_ms": base_latency_ms,
            "throughput_tokens_per_sec": 100.0 * throughput_multiplier,
            "gpu_utilization": 0.85,
        }


class ExpertParallelStrategy(ParallelismStrategy):
    """Expert parallelism for Mixture-of-Experts models."""

    def __init__(self):
        super().__init__("ExpertParallel", ParallelismType.EXPERT_PARALLEL)

    def optimize(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> ParallelismConfig:
        """Optimize expert parallelism size."""

        # Expert parallelism for MoE models
        ep_size = min(available_gpus, 8)  # Typical number of experts

        config = ParallelismConfig(
            tensor_parallel_size=1,
            pipeline_parallel_size=1,
            data_parallel_size=1,
            expert_parallel_size=ep_size,
            total_gpus=available_gpus,
            gpu_memory_gb=instance.gpu_memory_gb,
        )

        return config

    def estimate_performance(
        self,
        config: ParallelismConfig,
        request: RequestMetadata,
    ) -> dict[str, float]:
        """Estimate performance for expert parallelism."""

        # Expert parallelism has routing overhead
        routing_overhead = 1.05

        base_latency_ms = 100.0
        estimated_latency = base_latency_ms * routing_overhead

        return {
            "latency_ms": estimated_latency,
            "throughput_tokens_per_sec": 120.0,
            "gpu_utilization": 0.75,
        }


class HybridParallelStrategy(ParallelismStrategy):
    """Hybrid parallelism combining multiple strategies."""

    def __init__(self):
        super().__init__("Hybrid", ParallelismType.HYBRID)
        self.tp_strategy = TensorParallelStrategy()
        self.pp_strategy = PipelineParallelStrategy()
        self.dp_strategy = DataParallelStrategy()

    def optimize(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> ParallelismConfig:
        """Optimize hybrid parallelism configuration."""

        # Intelligent hybrid strategy based on available GPUs
        if available_gpus >= 16:
            # Large scale: TP + PP + DP
            tp_size = 4
            pp_size = 2
            dp_size = available_gpus // (tp_size * pp_size)
        elif available_gpus >= 8:
            # Medium scale: TP + DP
            tp_size = 4
            pp_size = 1
            dp_size = available_gpus // tp_size
        elif available_gpus >= 4:
            # Small scale: TP only
            tp_size = available_gpus
            pp_size = 1
            dp_size = 1
        else:
            # Minimal: single GPU or TP=2
            tp_size = min(available_gpus, 2)
            pp_size = 1
            dp_size = 1

        config = ParallelismConfig(
            tensor_parallel_size=tp_size,
            pipeline_parallel_size=pp_size,
            data_parallel_size=dp_size,
            total_gpus=available_gpus,
            gpu_memory_gb=instance.gpu_memory_gb,
        )

        if not config.validate():
            # Fallback to TP only
            return self.tp_strategy.optimize(request, instance, available_gpus)

        return config

    def estimate_performance(
        self,
        config: ParallelismConfig,
        request: RequestMetadata,
    ) -> dict[str, float]:
        """Estimate performance for hybrid parallelism."""

        # Combine overhead from different parallelism types
        tp_overhead = 1.0 + (0.1 * math.log2(config.tensor_parallel_size))
        pp_overhead = 1.0 + (0.15 * config.pipeline_parallel_size)

        total_overhead = tp_overhead * pp_overhead

        # Throughput benefits from DP
        throughput_multiplier = config.data_parallel_size * 0.9

        base_latency_ms = 100.0
        estimated_latency = base_latency_ms * total_overhead

        return {
            "latency_ms": estimated_latency,
            "throughput_tokens_per_sec": 100.0 * throughput_multiplier / total_overhead,
            "gpu_utilization": 0.8,
        }


class ParallelismOptimizer:
    """Optimizer that selects the best parallelism strategy."""

    def __init__(self):
        self.strategies = {
            ParallelismType.TENSOR_PARALLEL: TensorParallelStrategy(),
            ParallelismType.PIPELINE_PARALLEL: PipelineParallelStrategy(),
            ParallelismType.DATA_PARALLEL: DataParallelStrategy(),
            ParallelismType.EXPERT_PARALLEL: ExpertParallelStrategy(),
            ParallelismType.HYBRID: HybridParallelStrategy(),
        }

    def select_strategy(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> tuple[ParallelismStrategy, ParallelismConfig]:
        """Select the best parallelism strategy for a request."""

        # Use hint if provided
        if request.parallelism_hint:
            strategy = self.strategies[request.parallelism_hint]
            config = strategy.optimize(request, instance, available_gpus)
            return strategy, config

        # Otherwise, intelligently select based on resources
        if available_gpus >= 8:
            strategy = self.strategies[ParallelismType.HYBRID]
        elif available_gpus >= 4:
            strategy = self.strategies[ParallelismType.TENSOR_PARALLEL]
        elif available_gpus >= 2:
            strategy = self.strategies[ParallelismType.DATA_PARALLEL]
        else:
            strategy = self.strategies[ParallelismType.TENSOR_PARALLEL]

        config = strategy.optimize(request, instance, available_gpus)
        return strategy, config

    def compare_strategies(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        available_gpus: int,
    ) -> dict[ParallelismType, dict[str, float]]:
        """Compare all strategies and return performance estimates."""

        results = {}
        for strategy_type, strategy in self.strategies.items():
            config = strategy.optimize(request, instance, available_gpus)
            perf = strategy.estimate_performance(config, request)
            perf["config"] = config  # type: ignore[assignment]
            results[strategy_type] = perf

        return results
