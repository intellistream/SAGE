"""
Workflow Evaluator for Benchmarking Optimizers

Layer: L3 (Core - Algorithm Library)

This module provides tools for evaluating and comparing different optimization
strategies on standard benchmarks.
"""

import time
from dataclasses import dataclass
from typing import Any

from .base import BaseOptimizer, OptimizationMetrics, WorkflowGraph
from .constraints import ConstraintChecker


@dataclass
class BenchmarkResult:
    """Result of running an optimizer on a benchmark."""

    optimizer_name: str
    workflow_name: str
    metrics: OptimizationMetrics
    constraints_satisfied: bool
    error: str | None = None


class WorkflowEvaluator:
    """
    Evaluator for comparing optimization strategies.

    Example:
        >>> evaluator = WorkflowEvaluator()
        >>>
        >>> # Add benchmark workflows
        >>> evaluator.add_benchmark("simple", simple_workflow)
        >>> evaluator.add_benchmark("complex", complex_workflow)
        >>>
        >>> # Evaluate optimizers
        >>> results = evaluator.evaluate_all([optimizer1, optimizer2])
        >>> evaluator.print_comparison(results)
    """

    def __init__(self):
        """Initialize evaluator."""
        self.benchmarks: dict[str, WorkflowGraph] = {}
        self.constraint_checker: ConstraintChecker | None = None

    def add_benchmark(self, name: str, workflow: WorkflowGraph):
        """
        Add a benchmark workflow.

        Args:
            name: Benchmark name
            workflow: Workflow to use as benchmark
        """
        self.benchmarks[name] = workflow

    def set_constraints(self, checker: ConstraintChecker):
        """
        Set constraint checker for evaluation.

        Args:
            checker: ConstraintChecker instance
        """
        self.constraint_checker = checker

    def evaluate_optimizer(
        self,
        optimizer: BaseOptimizer,
        workflow: WorkflowGraph,
        workflow_name: str = "workflow",
    ) -> BenchmarkResult:
        """
        Evaluate an optimizer on a single workflow.

        Args:
            optimizer: Optimizer to evaluate
            workflow: Workflow to optimize
            workflow_name: Name of the workflow

        Returns:
            BenchmarkResult
        """
        try:
            # Run optimization
            start_time = time.time()
            result = optimizer.optimize(workflow)
            execution_time = time.time() - start_time

            # Update metrics with actual execution time
            result.metrics.execution_time = execution_time

            # Check constraints if provided
            constraints_satisfied = True
            if self.constraint_checker:
                constraints_satisfied = self.constraint_checker.is_satisfied(
                    result.optimized_workflow
                )

            return BenchmarkResult(
                optimizer_name=optimizer.name,
                workflow_name=workflow_name,
                metrics=result.metrics,
                constraints_satisfied=constraints_satisfied,
            )

        except Exception as e:
            return BenchmarkResult(
                optimizer_name=optimizer.name,
                workflow_name=workflow_name,
                metrics=OptimizationMetrics(),
                constraints_satisfied=False,
                error=str(e),
            )

    def evaluate_all(self, optimizers: list[BaseOptimizer]) -> dict[str, list[BenchmarkResult]]:
        """
        Evaluate all optimizers on all benchmarks.

        Args:
            optimizers: List of optimizers to evaluate

        Returns:
            Dictionary mapping optimizer names to their results
        """
        results: dict[str, list[BenchmarkResult]] = {}

        for optimizer in optimizers:
            optimizer_results = []
            for benchmark_name, workflow in self.benchmarks.items():
                result = self.evaluate_optimizer(optimizer, workflow, benchmark_name)
                optimizer_results.append(result)
            results[optimizer.name] = optimizer_results

        return results

    def print_comparison(self, results: dict[str, list[BenchmarkResult]]):
        """
        Print comparison table of optimization results.

        Args:
            results: Results from evaluate_all()
        """
        print("\n" + "=" * 80)
        print("WORKFLOW OPTIMIZATION BENCHMARK RESULTS")
        print("=" * 80)

        # Group by workflow
        workflows: set[str] = set()
        for optimizer_results in results.values():
            workflows.update(r.workflow_name for r in optimizer_results)

        for workflow_name in sorted(workflows):
            print(f"\n📊 Benchmark: {workflow_name}")
            print("-" * 80)
            print(
                f"{'Optimizer':<20} {'Cost↓':<10} {'Latency↓':<12} {'Quality Δ':<12} "
                f"{'Time':<10} {'OK':<5}"
            )
            print("-" * 80)

            for optimizer_name, optimizer_results in results.items():
                for result in optimizer_results:
                    if result.workflow_name == workflow_name:
                        if result.error:
                            print(f"{optimizer_name:<20} ERROR: {result.error}")
                        else:
                            m = result.metrics
                            status = "✓" if result.constraints_satisfied else "✗"
                            print(
                                f"{optimizer_name:<20} "
                                f"{m.cost_reduction:>8.1f}% "
                                f"{m.latency_reduction:>10.1f}% "
                                f"{m.quality_change:>+10.2f} "
                                f"{m.execution_time:>8.3f}s "
                                f"{status:<5}"
                            )

        print("\n" + "=" * 80)

    def generate_report(self, results: dict[str, list[BenchmarkResult]]) -> dict[str, Any]:
        """
        Generate structured report of results.

        Args:
            results: Results from evaluate_all()

        Returns:
            Dictionary with aggregated statistics
        """
        report: dict[str, Any] = {"optimizers": {}, "summary": {}}

        for optimizer_name, optimizer_results in results.items():
            stats = {
                "avg_cost_reduction": sum(r.metrics.cost_reduction for r in optimizer_results)
                / len(optimizer_results),
                "avg_latency_reduction": sum(r.metrics.latency_reduction for r in optimizer_results)
                / len(optimizer_results),
                "avg_quality_change": sum(r.metrics.quality_change for r in optimizer_results)
                / len(optimizer_results),
                "avg_execution_time": sum(r.metrics.execution_time for r in optimizer_results)
                / len(optimizer_results),
                "constraints_satisfied_count": sum(
                    1 for r in optimizer_results if r.constraints_satisfied
                ),
                "total_benchmarks": len(optimizer_results),
                "error_count": sum(1 for r in optimizer_results if r.error),
            }
            report["optimizers"][optimizer_name] = stats

        # Find best optimizer per metric
        best_cost = max(
            report["optimizers"].items(),
            key=lambda x: x[1]["avg_cost_reduction"],
        )
        best_latency = max(
            report["optimizers"].items(),
            key=lambda x: x[1]["avg_latency_reduction"],
        )
        best_quality = max(
            report["optimizers"].items(),
            key=lambda x: x[1]["avg_quality_change"],
        )

        report["summary"] = {
            "best_cost_optimizer": best_cost[0],
            "best_latency_optimizer": best_latency[0],
            "best_quality_optimizer": best_quality[0],
        }

        return report


def create_synthetic_workflow(
    num_agents: int = 5,
    avg_cost: float = 10.0,
    avg_latency: float = 1.0,
    connectivity: float = 0.3,
) -> WorkflowGraph:
    """
    Create a synthetic workflow for testing.

    Args:
        num_agents: Number of agent nodes
        avg_cost: Average cost per agent
        avg_latency: Average latency per agent
        connectivity: Probability of edge between nodes (0-1)

    Returns:
        WorkflowGraph
    """
    import random

    from .base import NodeType

    workflow = WorkflowGraph(name=f"synthetic_{num_agents}")

    # Add nodes
    for i in range(num_agents):
        cost = avg_cost * random.uniform(0.5, 1.5)
        latency = avg_latency * random.uniform(0.5, 1.5)
        quality = random.uniform(0.7, 1.0)

        workflow.add_node(
            node_id=f"agent_{i}",
            node_type=NodeType.AGENT,
            metrics={
                "cost": cost,
                "latency": latency,
                "quality": quality,
            },
        )

    # Add edges (ensure DAG)
    for i in range(num_agents):
        for j in range(i + 1, num_agents):
            if random.random() < connectivity:
                try:
                    workflow.add_edge(f"agent_{i}", f"agent_{j}")
                except ValueError:
                    # Skip if would create cycle
                    pass

    return workflow
