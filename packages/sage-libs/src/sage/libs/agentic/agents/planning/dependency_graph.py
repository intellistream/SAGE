"""
Dependency Graph for Task Planning

Handles dependency parsing, cycle detection, and topological sorting of plan steps.
"""

import logging
from typing import Optional

from .schemas import PlanStep

logger = logging.getLogger(__name__)


class DependencyGraph:
    """
    Dependency graph for plan steps.

    Provides:
    - Cycle detection
    - Topological sorting
    - Dependency validation
    """

    def __init__(self, steps: list[PlanStep]):
        """
        Initialize dependency graph from plan steps.

        Args:
            steps: List of PlanStep instances
        """
        self.steps = {step.id: step for step in steps}
        # Store both forward (dependency) and reverse (dependent) edges
        self.dependencies: dict[int, list[int]] = {}  # step -> what it depends on
        self.dependents: dict[int, list[int]] = {}  # step -> what depends on it
        self._build_graph()

    def _build_graph(self):
        """Build adjacency lists from step dependencies."""
        # Initialize empty lists
        for step_id in self.steps:
            self.dependencies[step_id] = []
            self.dependents[step_id] = []

        # Build both forward and reverse edges
        for step_id, step in self.steps.items():
            self.dependencies[step_id] = step.depends_on.copy()
            for dep_id in step.depends_on:
                if dep_id in self.dependents:
                    self.dependents[dep_id].append(step_id)

    @classmethod
    def from_steps(cls, steps: list[PlanStep]) -> "DependencyGraph":
        """
        Create dependency graph from steps.

        Args:
            steps: List of PlanStep instances

        Returns:
            DependencyGraph instance
        """
        return cls(steps)

    def detect_cycles(self) -> Optional[list[int]]:
        """
        Detect cycles in the dependency graph using DFS.

        Returns:
            List of step IDs in cycle if found, None otherwise
        """
        visited: set[int] = set()
        rec_stack: set[int] = set()
        parent: dict[int, int] = {}

        def dfs(node: int) -> Optional[list[int]]:
            visited.add(node)
            rec_stack.add(node)

            # Follow dependency edges: if node depends on X, then X -> node
            for neighbor in self.dependencies.get(node, []):
                if neighbor not in visited:
                    parent[neighbor] = node
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle, reconstruct it
                    cycle = [neighbor]
                    current: Optional[int] = node
                    while current != neighbor and current is not None:
                        cycle.append(current)
                        current = parent.get(current)
                    cycle.append(neighbor)
                    return cycle[::-1]

            rec_stack.remove(node)
            return None

        for step_id in self.steps:
            if step_id not in visited:
                cycle = dfs(step_id)
                if cycle:
                    return cycle

        return None

    def has_cycle(self) -> bool:
        """
        Check if graph has cycles.

        Returns:
            True if cycle exists, False otherwise
        """
        return self.detect_cycles() is not None

    def topological_sort(self) -> list[PlanStep]:
        """
        Perform topological sort using Kahn's algorithm.

        Returns:
            List of PlanStep in topological order

        Raises:
            ValueError: If graph contains cycles
        """
        # Check for cycles first
        cycle = self.detect_cycles()
        if cycle:
            raise ValueError(f"Cannot sort: graph contains cycle: {cycle}")

        # Calculate in-degrees: count how many steps each step depends on
        in_degree: dict[int, int] = {
            step_id: len(self.dependencies[step_id]) for step_id in self.steps
        }

        # Queue of nodes with no dependencies (in-degree 0)
        queue: list[int] = [step_id for step_id, deg in in_degree.items() if deg == 0]
        sorted_steps: list[PlanStep] = []

        while queue:
            # Sort queue to ensure deterministic order
            queue.sort()
            current = queue.pop(0)
            sorted_steps.append(self.steps[current])

            # For each step that depends on current, reduce its in-degree
            for dependent in self.dependents.get(current, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check if all nodes were processed
        if len(sorted_steps) != len(self.steps):
            missing = set(self.steps.keys()) - {s.id for s in sorted_steps}
            raise ValueError(f"Topological sort incomplete. Missing steps: {missing}")

        return sorted_steps

    def validate(self, max_steps: int = 10) -> bool:
        """
        Validate dependency graph.

        Checks:
        - No cycles
        - All dependencies exist
        - Step count within limits

        Args:
            max_steps: Maximum allowed steps

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If graph has no steps
        """
        # Check for empty graph
        if len(self.steps) == 0:
            raise ValueError("Cannot validate empty dependency graph")

        # Check step count
        if len(self.steps) > max_steps:
            logger.warning(f"Too many steps: {len(self.steps)} > {max_steps}")
            return False

        # Check all dependencies exist
        for step_id, step in self.steps.items():
            for dep_id in step.depends_on:
                if dep_id not in self.steps:
                    logger.warning(f"Step {step_id} depends on non-existent step {dep_id}")
                    return False

                # Check for self-dependency
                if dep_id == step_id:
                    logger.warning(f"Step {step_id} has self-dependency")
                    return False

        # Check for cycles
        if self.has_cycle():
            cycle = self.detect_cycles()
            logger.warning(f"Graph contains cycle: {cycle}")
            return False

        return True

    def get_root_steps(self) -> list[PlanStep]:
        """
        Get steps with no dependencies (root nodes).

        Returns:
            List of root PlanStep instances
        """
        return [step for step in self.steps.values() if not step.depends_on]

    def get_leaf_steps(self) -> list[PlanStep]:
        """
        Get steps that no other step depends on (leaf nodes).

        Returns:
            List of leaf PlanStep instances
        """
        depended_on = set()
        for step in self.steps.values():
            depended_on.update(step.depends_on)

        return [step for step_id, step in self.steps.items() if step_id not in depended_on]

    def get_execution_levels(self) -> list[list[PlanStep]]:
        """
        Get steps grouped by execution level (can be parallelized within level).

        Returns:
            List of lists, where each inner list contains steps at the same level
        """
        if self.has_cycle():
            raise ValueError("Cannot determine execution levels: graph has cycles")

        levels: list[list[PlanStep]] = []
        remaining = set(self.steps.keys())
        completed: set[int] = set()

        while remaining:
            # Find steps whose dependencies are all completed
            current_level_ids = []
            for step_id in remaining:
                step = self.steps[step_id]
                if all(dep in completed for dep in step.depends_on):
                    current_level_ids.append(step_id)

            if not current_level_ids:
                # No progress made, must be a cycle (shouldn't happen after cycle check)
                raise ValueError("Execution level calculation stalled")

            # Remove from remaining and add to completed AFTER finding all steps in this level
            current_level = []
            for step_id in current_level_ids:
                remaining.remove(step_id)
                completed.add(step_id)
                current_level.append(self.steps[step_id])

            # Sort by step ID for deterministic order
            current_level.sort(key=lambda s: s.id)
            levels.append(current_level)

        return levels

    def repair_dependencies(self) -> list[PlanStep]:
        """
        Attempt to repair invalid dependencies.

        Removes:
        - Self-dependencies
        - Dependencies on non-existent steps
        - Cycles (by removing edges)

        Returns:
            List of repaired PlanStep instances
        """
        repaired_steps = []

        for step in self.steps.values():
            # Create new step with cleaned dependencies
            clean_deps = []
            for dep_id in step.depends_on:
                # Remove self-dependencies
                if dep_id == step.id:
                    logger.info(f"Removed self-dependency from step {step.id}")
                    continue

                # Remove dependencies on non-existent steps
                if dep_id not in self.steps:
                    logger.info(
                        f"Removed dependency on non-existent step {dep_id} from step {step.id}"
                    )
                    continue

                clean_deps.append(dep_id)

            repaired_step = step.model_copy(update={"depends_on": clean_deps})
            repaired_steps.append(repaired_step)

        # Rebuild graph with repaired steps
        self.steps = {step.id: step for step in repaired_steps}
        self._build_graph()

        # If still has cycles, remove edges to break them
        max_iterations = 10
        iteration = 0
        while self.has_cycle() and iteration < max_iterations:
            cycle = self.detect_cycles()
            if cycle and len(cycle) >= 2:
                # Cycle format: [A, B, C, A] means A->B->C->A
                # Remove the last edge in the cycle: C -> A
                # cycle[-2] is the second-to-last node, cycle[-1] should be same as cycle[0]
                # So remove edge from cycle[-2] to cycle[0]
                if cycle[-1] == cycle[0] and len(cycle) > 2:
                    # Standard cycle format: [1, 2, 3, 1]
                    from_node = cycle[-2]
                    to_node = cycle[-1]
                else:
                    # Fallback: remove last edge
                    from_node = cycle[-1]
                    to_node = cycle[0]

                if from_node in self.steps:
                    step = self.steps[from_node]
                    if to_node in step.depends_on:
                        new_deps = [d for d in step.depends_on if d != to_node]
                        self.steps[from_node] = step.model_copy(update={"depends_on": new_deps})
                        self._build_graph()
                        logger.info(f"Removed dependency {from_node} -> {to_node} to break cycle")
            iteration += 1
            iteration += 1

        return list(self.steps.values())
