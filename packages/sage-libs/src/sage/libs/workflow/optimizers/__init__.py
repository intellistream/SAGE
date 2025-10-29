"""
Example Optimizers for Reference

Layer: L3 (Core - Algorithm Library)

This module provides reference implementations of optimization strategies.
Students can use these as starting points for their own research.
"""

import time
from typing import Any, Dict, Optional

from ..base import BaseOptimizer, OptimizationResult, WorkflowGraph
from ..constraints import ConstraintChecker


class NoOpOptimizer(BaseOptimizer):
    """
    No-operation optimizer that returns the original workflow unchanged.

    Useful as a baseline for comparison.
    """

    def __init__(self):
        """Initialize no-op optimizer."""
        super().__init__(name="NoOp")

    def optimize(
        self,
        workflow: WorkflowGraph,
        constraints: dict[str, Any] | None = None,
    ) -> OptimizationResult:
        """Return workflow unchanged."""
        start_time = time.time()

        # Clone to maintain consistent behavior
        optimized = workflow.clone()

        execution_time = time.time() - start_time
        metrics = self.calculate_metrics(workflow, optimized, execution_time=execution_time)

        return OptimizationResult(
            original_workflow=workflow,
            optimized_workflow=optimized,
            metrics=metrics,
            steps=["No optimization performed"],
        )


class GreedyOptimizer(BaseOptimizer):
    """
    Greedy optimizer that removes highest-cost nodes when possible.

    Strategy:
        1. Sort nodes by cost (descending)
        2. Try removing each node
        3. Keep removal if constraints still satisfied
        4. Repeat until no more removals possible

    This is a simple example - students can implement more sophisticated strategies!
    """

    def __init__(self, max_removals: int | None = None):
        """
        Initialize greedy optimizer.

        Args:
            max_removals: Maximum number of nodes to remove (None for unlimited)
        """
        super().__init__(name="Greedy")
        self.max_removals = max_removals

    def optimize(
        self,
        workflow: WorkflowGraph,
        constraints: dict[str, Any] | None = None,
    ) -> OptimizationResult:
        """Optimize using greedy node removal."""
        start_time = time.time()
        optimized = workflow.clone()
        steps = []
        removals = 0

        # Setup constraint checker if constraints provided
        checker = None
        if constraints:
            checker = self._build_constraint_checker(constraints)

        # Sort nodes by cost (descending)
        sorted_nodes = sorted(
            optimized.nodes.items(),
            key=lambda x: x[1].cost,
            reverse=True,
        )

        for node_id, node in sorted_nodes:
            if self.max_removals and removals >= self.max_removals:
                break

            # Try removing this node
            if self._can_remove_node(optimized, node_id, checker):
                self._remove_node(optimized, node_id)
                removals += 1
                steps.append(f"Removed node {node_id} (cost={node.cost:.2f})")

        execution_time = time.time() - start_time
        metrics = self.calculate_metrics(
            workflow, optimized, execution_time=execution_time, iterations=removals
        )

        return OptimizationResult(
            original_workflow=workflow,
            optimized_workflow=optimized,
            metrics=metrics,
            steps=steps,
        )

    def _can_remove_node(
        self,
        workflow: WorkflowGraph,
        node_id: str,
        checker: ConstraintChecker | None,
    ) -> bool:
        """Check if node can be safely removed."""
        # Don't remove nodes with no predecessors (input nodes)
        if not workflow.get_predecessors(node_id):
            return False

        # Don't remove nodes with no successors (output nodes)
        if not workflow.get_successors(node_id):
            return False

        # If constraints specified, check if removal would violate them
        if checker:
            # Create temporary workflow without this node
            temp = workflow.clone()
            self._remove_node(temp, node_id)
            if not checker.is_satisfied(temp):
                return False

        return True

    def _remove_node(self, workflow: WorkflowGraph, node_id: str):
        """Remove a node from workflow."""
        # Remove node
        del workflow.nodes[node_id]

        # Remove edges
        del workflow.edges[node_id]
        for edges in workflow.edges.values():
            edges.discard(node_id)

    def _build_constraint_checker(self, constraints: dict[str, Any]) -> ConstraintChecker:
        """Build constraint checker from constraint dictionary."""
        from ..constraints import (
            BudgetConstraint,
            ConstraintChecker,
            LatencyConstraint,
            QualityConstraint,
        )

        checker = ConstraintChecker()

        if "max_cost" in constraints:
            checker.add_constraint(BudgetConstraint(max_cost=constraints["max_cost"]))
        if "max_latency" in constraints:
            checker.add_constraint(LatencyConstraint(max_latency=constraints["max_latency"]))
        if "min_quality" in constraints:
            checker.add_constraint(QualityConstraint(min_quality=constraints["min_quality"]))

        return checker


class ParallelizationOptimizer(BaseOptimizer):
    """
    Optimizer that identifies parallelization opportunities.

    Strategy:
        1. Find independent subgraphs
        2. Mark nodes that can execute in parallel
        3. Reduce critical path latency

    This is a conceptual example - actual parallel execution would require
    integration with SAGE's execution engine.
    """

    def __init__(self):
        """Initialize parallelization optimizer."""
        super().__init__(name="Parallelization")

    def optimize(
        self,
        workflow: WorkflowGraph,
        constraints: dict[str, Any] | None = None,
    ) -> OptimizationResult:
        """Optimize by identifying parallelization opportunities."""
        start_time = time.time()
        optimized = workflow.clone()
        steps = []

        # Find independent nodes at each level
        levels = self._compute_levels(optimized)
        parallel_groups = 0

        for level, nodes in levels.items():
            if len(nodes) > 1:
                # These nodes can execute in parallel
                parallel_groups += 1
                steps.append(f"Level {level}: {len(nodes)} nodes can run in parallel: {nodes}")

                # Mark nodes with parallelization metadata
                for node_id in nodes:
                    optimized.nodes[node_id].metadata["parallel_level"] = level
                    optimized.nodes[node_id].metadata["parallel_group_size"] = len(nodes)

                # Reduce latency (conceptual - assumes parallel execution)
                # In reality, this would depend on available resources
                max_latency = max(optimized.nodes[n].latency for n in nodes)
                for node_id in nodes:
                    # All nodes in level execute in time of slowest node
                    optimized.nodes[node_id].metadata["effective_latency"] = max_latency

        execution_time = time.time() - start_time
        metrics = self.calculate_metrics(
            workflow,
            optimized,
            execution_time=execution_time,
            iterations=parallel_groups,
        )

        # Adjust latency reduction based on parallelization
        if parallel_groups > 0:
            # Estimate latency reduction (this is a simplified model)
            metrics.latency_reduction = min(50.0, parallel_groups * 10.0)  # Cap at 50%

        return OptimizationResult(
            original_workflow=workflow,
            optimized_workflow=optimized,
            metrics=metrics,
            steps=steps,
        )

    def _compute_levels(self, workflow: WorkflowGraph) -> dict[int, list]:
        """Compute topological levels for parallelization."""
        levels: dict[int, list] = {}
        node_levels: dict[str, int] = {}

        # Compute level for each node (longest path from source)
        def compute_level(node_id: str) -> int:
            if node_id in node_levels:
                return node_levels[node_id]

            predecessors = workflow.get_predecessors(node_id)
            if not predecessors:
                level = 0
            else:
                level = max(compute_level(p) for p in predecessors) + 1

            node_levels[node_id] = level
            return level

        for node_id in workflow.nodes:
            level = compute_level(node_id)
            if level not in levels:
                levels[level] = []
            levels[level].append(node_id)

        return levels
