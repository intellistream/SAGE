"""
Constraint System for Workflow Optimization

Layer: L3 (Core - Algorithm Library)

This module provides constraint checking functionality for workflow optimization.
Students can define custom constraints or use built-in ones.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .base import WorkflowGraph


class BaseConstraint(ABC):
    """
    Abstract base class for workflow constraints.

    Students can implement custom constraints by inheriting from this class.
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        """
        Initialize constraint.

        Args:
            name: Name of the constraint
            config: Configuration parameters
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    def check(self, workflow: WorkflowGraph) -> bool:
        """
        Check if workflow satisfies the constraint.

        Args:
            workflow: Workflow to check

        Returns:
            True if constraint is satisfied, False otherwise
        """
        pass

    @abstractmethod
    def get_violation_message(self, workflow: WorkflowGraph) -> str:
        """
        Get a message describing constraint violation.

        Args:
            workflow: Workflow to check

        Returns:
            Human-readable violation message
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class BudgetConstraint(BaseConstraint):
    """
    Constraint on total workflow cost.

    Example:
        >>> constraint = BudgetConstraint(max_cost=100.0)
        >>> satisfied = constraint.check(workflow)
    """

    def __init__(self, max_cost: float, name: str = "BudgetConstraint"):
        """
        Initialize budget constraint.

        Args:
            max_cost: Maximum allowed cost
            name: Constraint name
        """
        super().__init__(name, {"max_cost": max_cost})
        self.max_cost = max_cost

    def check(self, workflow: WorkflowGraph) -> bool:
        """Check if workflow cost is within budget."""
        return workflow.total_cost() <= self.max_cost

    def get_violation_message(self, workflow: WorkflowGraph) -> str:
        """Get violation message."""
        actual_cost = workflow.total_cost()
        return (
            f"Budget exceeded: {actual_cost:.2f} > {self.max_cost:.2f} "
            f"(over by {actual_cost - self.max_cost:.2f})"
        )


class LatencyConstraint(BaseConstraint):
    """
    Constraint on total workflow latency.

    Example:
        >>> constraint = LatencyConstraint(max_latency=5.0)
        >>> satisfied = constraint.check(workflow)
    """

    def __init__(self, max_latency: float, name: str = "LatencyConstraint"):
        """
        Initialize latency constraint.

        Args:
            max_latency: Maximum allowed latency (seconds)
            name: Constraint name
        """
        super().__init__(name, {"max_latency": max_latency})
        self.max_latency = max_latency

    def check(self, workflow: WorkflowGraph) -> bool:
        """Check if workflow latency is within limit."""
        return workflow.total_latency() <= self.max_latency

    def get_violation_message(self, workflow: WorkflowGraph) -> str:
        """Get violation message."""
        actual_latency = workflow.total_latency()
        return (
            f"Latency exceeded: {actual_latency:.2f}s > {self.max_latency:.2f}s "
            f"(over by {actual_latency - self.max_latency:.2f}s)"
        )


class QualityConstraint(BaseConstraint):
    """
    Constraint on minimum workflow quality.

    Example:
        >>> constraint = QualityConstraint(min_quality=0.8)
        >>> satisfied = constraint.check(workflow)
    """

    def __init__(self, min_quality: float, name: str = "QualityConstraint"):
        """
        Initialize quality constraint.

        Args:
            min_quality: Minimum required quality score (0-1)
            name: Constraint name
        """
        super().__init__(name, {"min_quality": min_quality})
        self.min_quality = min_quality

    def check(self, workflow: WorkflowGraph) -> bool:
        """Check if workflow quality meets minimum."""
        return workflow.average_quality() >= self.min_quality

    def get_violation_message(self, workflow: WorkflowGraph) -> str:
        """Get violation message."""
        actual_quality = workflow.average_quality()
        return (
            f"Quality below minimum: {actual_quality:.2f} < {self.min_quality:.2f} "
            f"(short by {self.min_quality - actual_quality:.2f})"
        )


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""

    constraint: BaseConstraint
    message: str
    severity: str = "error"  # "error", "warning"


class ConstraintChecker:
    """
    Checks multiple constraints on a workflow.

    Example:
        >>> checker = ConstraintChecker()
        >>> checker.add_constraint(BudgetConstraint(max_cost=100))
        >>> checker.add_constraint(LatencyConstraint(max_latency=5))
        >>> violations = checker.check_all(workflow)
        >>> if violations:
        ...     for v in violations:
        ...         print(f"Violation: {v.message}")
    """

    def __init__(self):
        """Initialize constraint checker."""
        self.constraints: list[BaseConstraint] = []

    def add_constraint(self, constraint: BaseConstraint):
        """
        Add a constraint to check.

        Args:
            constraint: Constraint to add
        """
        self.constraints.append(constraint)

    def remove_constraint(self, constraint_name: str):
        """
        Remove a constraint by name.

        Args:
            constraint_name: Name of constraint to remove
        """
        self.constraints = [c for c in self.constraints if c.name != constraint_name]

    def check_all(
        self, workflow: WorkflowGraph, stop_on_first: bool = False
    ) -> list[ConstraintViolation]:
        """
        Check all constraints.

        Args:
            workflow: Workflow to check
            stop_on_first: If True, stop after first violation

        Returns:
            List of constraint violations (empty if all satisfied)
        """
        violations = []

        for constraint in self.constraints:
            if not constraint.check(workflow):
                violation = ConstraintViolation(
                    constraint=constraint,
                    message=constraint.get_violation_message(workflow),
                )
                violations.append(violation)

                if stop_on_first:
                    break

        return violations

    def is_satisfied(self, workflow: WorkflowGraph) -> bool:
        """
        Check if all constraints are satisfied.

        Args:
            workflow: Workflow to check

        Returns:
            True if all constraints satisfied, False otherwise
        """
        return len(self.check_all(workflow, stop_on_first=True)) == 0

    def __repr__(self) -> str:
        return f"ConstraintChecker(constraints={len(self.constraints)})"
