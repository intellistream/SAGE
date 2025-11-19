"""
Example usage of the Workflow Optimizer Framework

This example demonstrates how to use the framework to research and develop
workflow optimization strategies.
"""

from sage.libs.agentic.workflow import (
    BudgetConstraint,
    ConstraintChecker,
    LatencyConstraint,
    NodeType,
    QualityConstraint,
    WorkflowEvaluator,
    WorkflowGraph,
)
from sage.libs.agentic.workflow.evaluator import create_synthetic_workflow
from sage.libs.agentic.workflow.optimizers import (
    GreedyOptimizer,
    NoOpOptimizer,
    ParallelizationOptimizer,
)


def example_basic_workflow():
    """Example: Create and optimize a simple workflow."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Workflow Optimization")
    print("=" * 80)

    # Create a simple workflow
    workflow = WorkflowGraph(name="rag_pipeline")

    # Add nodes
    workflow.add_node(
        "retriever",
        NodeType.AGENT,
        metrics={"cost": 5.0, "latency": 0.5, "quality": 0.9},
    )
    workflow.add_node(
        "reranker",
        NodeType.AGENT,
        metrics={"cost": 15.0, "latency": 1.0, "quality": 0.95},
    )
    workflow.add_node(
        "generator",
        NodeType.AGENT,
        metrics={"cost": 25.0, "latency": 2.0, "quality": 0.85},
    )

    # Add dependencies
    workflow.add_edge("retriever", "reranker")
    workflow.add_edge("reranker", "generator")

    print(f"\nOriginal workflow: {workflow}")
    print(f"  Total cost: ${workflow.total_cost():.2f}")
    print(f"  Total latency: {workflow.total_latency():.2f}s")
    print(f"  Average quality: {workflow.average_quality():.2f}")

    # Apply optimizer
    optimizer = GreedyOptimizer(max_removals=1)
    result = optimizer.optimize(
        workflow,
        constraints={
            "max_cost": 40.0,
            "min_quality": 0.85,
        },
    )

    print("\nOptimized workflow:")
    print(f"  Total cost: ${result.optimized_workflow.total_cost():.2f}")
    print(f"  Total latency: {result.optimized_workflow.total_latency():.2f}s")
    print(f"  Average quality: {result.optimized_workflow.average_quality():.2f}")
    print(f"\nMetrics: {result.metrics}")
    print("\nOptimization steps:")
    for step in result.steps:
        print(f"  - {step}")


def example_constraint_checking():
    """Example: Check constraints on a workflow."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Constraint Checking")
    print("=" * 80)

    # Create workflow
    workflow = create_synthetic_workflow(num_agents=5, avg_cost=20.0)

    print(f"\nWorkflow: {workflow}")
    print(f"  Total cost: ${workflow.total_cost():.2f}")
    print(f"  Total latency: {workflow.total_latency():.2f}s")

    # Setup constraints
    checker = ConstraintChecker()
    checker.add_constraint(BudgetConstraint(max_cost=80.0))
    checker.add_constraint(LatencyConstraint(max_latency=5.0))
    checker.add_constraint(QualityConstraint(min_quality=0.8))

    # Check constraints
    violations = checker.check_all(workflow)

    if violations:
        print("\n❌ Constraint violations found:")
        for v in violations:
            print(f"  - {v.message}")
    else:
        print("\n✅ All constraints satisfied!")


def example_benchmarking():
    """Example: Compare multiple optimizers."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Benchmarking Multiple Optimizers")
    print("=" * 80)

    # Create evaluator
    evaluator = WorkflowEvaluator()

    # Add benchmarks
    evaluator.add_benchmark("small", create_synthetic_workflow(num_agents=3))
    evaluator.add_benchmark("medium", create_synthetic_workflow(num_agents=7))
    evaluator.add_benchmark("large", create_synthetic_workflow(num_agents=12))

    # Setup constraints
    checker = ConstraintChecker()
    checker.add_constraint(BudgetConstraint(max_cost=100.0))
    checker.add_constraint(QualityConstraint(min_quality=0.7))
    evaluator.set_constraints(checker)

    # Evaluate optimizers
    optimizers = [
        NoOpOptimizer(),
        GreedyOptimizer(),
        ParallelizationOptimizer(),
    ]

    results = evaluator.evaluate_all(optimizers)
    evaluator.print_comparison(results)

    # Generate report
    report = evaluator.generate_report(results)
    print("\n📊 Summary:")
    print(f"  Best cost reduction: {report['summary']['best_cost_optimizer']}")
    print(f"  Best latency reduction: {report['summary']['best_latency_optimizer']}")
    print(f"  Best quality improvement: {report['summary']['best_quality_optimizer']}")


def example_custom_optimizer():
    """Example: Implement a custom optimizer."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Custom Optimizer Implementation")
    print("=" * 80)

    from sage.libs.agentic.workflow import BaseOptimizer, OptimizationResult

    class CostThresholdOptimizer(BaseOptimizer):
        """
        Custom optimizer: Remove all nodes above a cost threshold.

        This is a simple example showing how students can implement
        their own optimization strategies.
        """

        def __init__(self, cost_threshold: float = 20.0):
            super().__init__(name=f"CostThreshold({cost_threshold})")
            self.cost_threshold = cost_threshold

        def optimize(self, workflow, constraints=None):
            import time

            start = time.time()
            optimized = workflow.clone()
            steps = []

            # Find nodes above threshold
            to_remove = [
                nid
                for nid, node in optimized.nodes.items()
                if node.cost > self.cost_threshold
                # Don't remove input/output nodes
                and optimized.get_predecessors(nid)
                and optimized.get_successors(nid)
            ]

            # Remove them
            for node_id in to_remove:
                node = optimized.nodes[node_id]
                del optimized.nodes[node_id]
                del optimized.edges[node_id]
                for edges in optimized.edges.values():
                    edges.discard(node_id)
                steps.append(f"Removed {node_id} (cost={node.cost:.2f})")

            exec_time = time.time() - start
            metrics = self.calculate_metrics(workflow, optimized, exec_time, len(to_remove))

            return OptimizationResult(
                original_workflow=workflow,
                optimized_workflow=optimized,
                metrics=metrics,
                steps=steps,
            )

    # Test custom optimizer
    workflow = create_synthetic_workflow(num_agents=8, avg_cost=15.0)
    print(f"\nOriginal workflow cost: ${workflow.total_cost():.2f}")

    custom_optimizer = CostThresholdOptimizer(cost_threshold=18.0)
    result = custom_optimizer.optimize(workflow)

    print(f"Optimized workflow cost: ${result.optimized_workflow.total_cost():.2f}")
    print(f"Metrics: {result.metrics}")
    print("\nSteps taken:")
    for step in result.steps:
        print(f"  - {step}")


if __name__ == "__main__":
    """Run all examples."""
    example_basic_workflow()
    example_constraint_checking()
    example_benchmarking()
    example_custom_optimizer()

    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
    print("\nNext steps for students:")
    print("  1. Study the example optimizers in workflow/optimizers/")
    print("  2. Implement your own optimizer by inheriting from BaseOptimizer")
    print("  3. Test on synthetic workflows or create domain-specific benchmarks")
    print("  4. Compare your optimizer against baselines using WorkflowEvaluator")
    print("  5. Experiment with different constraint combinations")
    print("\nHappy researching! 🚀")
