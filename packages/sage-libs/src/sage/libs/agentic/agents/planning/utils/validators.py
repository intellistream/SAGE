"""
Validators for Plan Validation

Provides validation functions for plan steps, dependencies, and constraints.
"""

import logging
from typing import Any, Optional

from ..schemas import PlanRequest, PlanResult, PlanStep, ToolMetadata

logger = logging.getLogger(__name__)


def validate_step_structure(step: dict[str, Any]) -> bool:
    """
    Validate that a step dictionary has required fields.

    Args:
        step: Step dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["id", "action"]

    for field in required_fields:
        if field not in step:
            logger.debug(f"Step missing required field: {field}")
            return False

    # Validate types
    if not isinstance(step["id"], int):
        logger.debug(f"Step id must be int, got {type(step['id'])}")
        return False

    if not isinstance(step["action"], str):
        logger.debug(f"Step action must be str, got {type(step['action'])}")
        return False

    # Optional fields type checking
    if "depends_on" in step and not isinstance(step["depends_on"], list):
        logger.debug("Step depends_on must be a list")
        return False

    if "inputs" in step and not isinstance(step["inputs"], dict):
        logger.debug("Step inputs must be a dict")
        return False

    return True


def validate_step_dependencies(steps: list[PlanStep], allow_forward_deps: bool = False) -> bool:
    """
    Validate step dependencies are well-formed.

    Args:
        steps: List of PlanStep instances
        allow_forward_deps: If True, allow dependencies on later steps

    Returns:
        True if dependencies are valid, False otherwise
    """
    step_ids = {step.id for step in steps}

    for step in steps:
        for dep_id in step.depends_on:
            # Check dependency exists
            if dep_id not in step_ids:
                logger.warning(f"Step {step.id} depends on non-existent step {dep_id}")
                return False

            # Check for self-dependency
            if dep_id == step.id:
                logger.warning(f"Step {step.id} has self-dependency")
                return False

            # Check for forward dependency (optional)
            if not allow_forward_deps and dep_id > step.id:
                logger.warning(f"Step {step.id} has forward dependency on step {dep_id}")
                return False

    return True


def validate_tool_availability(steps: list[PlanStep], available_tools: list[ToolMetadata]) -> bool:
    """
    Validate that all required tools are available.

    Args:
        steps: List of PlanStep instances
        available_tools: List of available ToolMetadata

    Returns:
        True if all tools are available, False otherwise
    """
    tool_ids = {tool.tool_id for tool in available_tools}

    for step in steps:
        if step.tool_id and step.tool_id not in tool_ids:
            logger.warning(f"Step {step.id} requires unavailable tool: {step.tool_id}")
            return False

    return True


def validate_step_count(steps: list[PlanStep], min_steps: int = 1, max_steps: int = 20) -> bool:
    """
    Validate number of steps is within acceptable range.

    Args:
        steps: List of PlanStep instances
        min_steps: Minimum number of steps
        max_steps: Maximum number of steps

    Returns:
        True if step count is valid, False otherwise
    """
    num_steps = len(steps)

    if num_steps < min_steps:
        logger.warning(f"Too few steps: {num_steps} < {min_steps}")
        return False

    if num_steps > max_steps:
        logger.warning(f"Too many steps: {num_steps} > {max_steps}")
        return False

    return True


def validate_plan_result(result: PlanResult, request: Optional[PlanRequest] = None) -> bool:
    """
    Validate a complete plan result.

    Args:
        result: PlanResult to validate
        request: Original PlanRequest (optional, for constraint checking)

    Returns:
        True if plan is valid, False otherwise
    """
    if not result.success:
        logger.debug("Plan marked as unsuccessful")
        return False

    if not result.steps:
        logger.warning("Plan has no steps")
        return False

    # Validate step count
    if request:
        if not validate_step_count(
            result.steps, min_steps=request.min_steps, max_steps=request.max_steps
        ):
            return False

    # Validate dependencies
    if not validate_step_dependencies(result.steps):
        return False

    # Validate tool availability if request provided
    if request and request.tools:
        if not validate_tool_availability(result.steps, request.tools):
            return False

    return True


def check_plan_constraints(steps: list[PlanStep], constraints: list[str]) -> list[str]:
    """
    Check if plan violates any constraints.

    Args:
        steps: List of PlanStep instances
        constraints: List of constraint strings

    Returns:
        List of violated constraints (empty if all satisfied)
    """
    violations = []

    for constraint in constraints:
        constraint_lower = constraint.lower()

        # Example constraints (can be extended)
        if "no parallel" in constraint_lower:
            # Check if any steps have the same dependency set (potential parallelism)
            dep_sets = [frozenset(step.depends_on) for step in steps]
            if len(dep_sets) != len(set(dep_sets)):
                violations.append(constraint)

        elif "sequential" in constraint_lower:
            # Check if steps form a strict sequence
            for i, step in enumerate(steps):
                if i > 0 and step.depends_on != [steps[i - 1].id]:
                    violations.append(constraint)
                    break

        elif "tool" in constraint_lower:
            # Check tool-related constraints
            # Format: "must use tool X" or "must not use tool Y"
            if "must use" in constraint_lower:
                tool_name = constraint_lower.split("must use")[-1].strip()
                if not any(tool_name in (step.tool_id or "").lower() for step in steps):
                    violations.append(constraint)

            elif "must not use" in constraint_lower:
                tool_name = constraint_lower.split("must not use")[-1].strip()
                if any(tool_name in (step.tool_id or "").lower() for step in steps):
                    violations.append(constraint)

    return violations


def suggest_plan_improvements(steps: list[PlanStep]) -> list[str]:
    """
    Suggest improvements for a plan.

    Args:
        steps: List of PlanStep instances

    Returns:
        List of improvement suggestions
    """
    suggestions = []

    # Check for isolated steps (no dependencies, no dependents)
    # step_ids = {step.id for step in steps}  # Reserved for future validation
    depended_on = set()
    for step in steps:
        depended_on.update(step.depends_on)

    for step in steps:
        if not step.depends_on and step.id not in depended_on:
            if len(steps) > 1:
                suggestions.append(f"Step {step.id} is isolated (no dependencies or dependents)")

    # Check for very long dependency chains
    def get_chain_length(step_id: int, visited: Optional[set[int]] = None) -> int:
        if visited is None:
            visited = set()
        if step_id in visited:
            return 0
        visited.add(step_id)

        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.depends_on:
            return 1

        return 1 + max(get_chain_length(dep, visited.copy()) for dep in step.depends_on)

    max_chain = max((get_chain_length(step.id) for step in steps), default=0)
    if max_chain > 7:
        suggestions.append(
            f"Long dependency chain detected ({max_chain} steps). Consider parallelization."
        )

    # Check for missing tool assignments
    steps_without_tools = [step.id for step in steps if not step.tool_id]
    if steps_without_tools:
        suggestions.append(f"Steps without assigned tools: {steps_without_tools}")

    # Check for missing descriptions
    steps_without_desc = [step.id for step in steps if not step.description]
    if len(steps_without_desc) > len(steps) / 2:
        suggestions.append("Many steps lack descriptions. Consider adding for clarity.")

    return suggestions
