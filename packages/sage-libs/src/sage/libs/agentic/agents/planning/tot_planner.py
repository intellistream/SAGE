"""
Tree-of-Thoughts (ToT) Planner

Implements Tree-of-Thoughts planning strategy based on:
"Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (Yao et al., 2023)

Key Features:
- Explores multiple reasoning paths via tree search
- Uses LLM to generate and evaluate thought candidates
- Supports both BFS and DFS search strategies
- More powerful than linear Chain-of-Thought for complex planning
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from .base import BasePlanner
from .schemas import (
    PlannerConfig,
    PlanRequest,
    PlanResult,
    PlanStep,
)

logger = logging.getLogger(__name__)


class SearchMethod(str, Enum):
    """Search method for tree traversal."""

    BFS = "bfs"  # Breadth-first search
    DFS = "dfs"  # Depth-first search


class ToTConfig(PlannerConfig):
    """Configuration for Tree-of-Thoughts Planner.

    Extends base PlannerConfig with ToT-specific parameters.
    """

    # Tree search parameters
    max_depth: int = Field(default=3, ge=1, le=10, description="Maximum tree depth")
    branch_factor: int = Field(
        default=3, ge=1, le=10, description="Number of thought candidates per node"
    )
    search_method: SearchMethod = Field(
        default=SearchMethod.BFS, description="Tree search method (bfs or dfs)"
    )
    beam_width: int = Field(
        default=5, ge=1, le=20, description="Number of best nodes to keep in BFS"
    )

    # Evaluation thresholds
    min_thought_score: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum score to keep a thought"
    )
    early_stop_score: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Score threshold for early stopping"
    )

    # LLM parameters
    generation_temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for thought generation"
    )
    evaluation_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Temperature for thought evaluation"
    )


@dataclass
class ThoughtNode:
    """Node in the thought tree.

    Represents a single reasoning step with its score and position in the tree.
    """

    thought: str
    score: float = 0.0
    children: list[ThoughtNode] = field(default_factory=list)
    parent: Optional[ThoughtNode] = None
    depth: int = 0
    step_index: int = 0  # Which step in the plan this represents
    tool_id: Optional[str] = None  # Associated tool if any
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set depth based on parent."""
        if self.parent is not None:
            self.depth = self.parent.depth + 1
            self.step_index = self.parent.step_index + 1

    def get_path(self) -> list[ThoughtNode]:
        """Get path from root to this node."""
        path = []
        node = self
        while node is not None:
            path.append(node)
            node = node.parent
        return list(reversed(path))

    def get_path_thoughts(self) -> list[str]:
        """Get thoughts along the path from root."""
        return [node.thought for node in self.get_path() if node.thought]

    def get_cumulative_score(self) -> float:
        """Get cumulative score along the path."""
        path = self.get_path()
        if not path:
            return 0.0
        return sum(node.score for node in path) / len(path)


class TreeOfThoughtsPlanner(BasePlanner):
    """
    Tree-of-Thoughts Planner for complex task planning.

    Algorithm:
    1. Start with root node (task goal)
    2. Generate multiple candidate thoughts (next steps)
    3. Evaluate each thought using LLM
    4. Use BFS/DFS to explore promising paths
    5. Return the best complete plan found

    This planner is more powerful than simple sequential planning
    because it explores multiple reasoning paths and can backtrack.
    """

    name: str = "tree_of_thoughts_planner"

    # Prompt templates
    THOUGHT_GENERATION_PROMPT = """You are a planning assistant. Given a task and the current progress, generate {n} different possible next steps.

Task Goal: {goal}
Available Tools: {tools}
Current Progress:
{progress}

Generate {n} different next steps. Each step should:
1. Make clear progress toward the goal
2. Use one of the available tools if appropriate
3. Be specific and actionable

Output as JSON array:
[
    {{"thought": "description of step", "tool_id": "tool_name or null", "reasoning": "why this step"}},
    ...
]

Only output the JSON array, nothing else."""

    THOUGHT_EVALUATION_PROMPT = """Evaluate how good this planning step is for achieving the goal.

Task Goal: {goal}
Previous Steps: {previous_steps}
Proposed Step: {thought}
Tool Used: {tool_id}

Rate this step on a scale of 0-10:
- 10: Excellent step, directly advances the goal
- 7-9: Good step, makes progress
- 4-6: Acceptable step, some progress
- 1-3: Poor step, minimal or unclear progress
- 0: Bad step, wrong direction

Output JSON: {{"score": <0-10>, "reasoning": "brief explanation"}}"""

    def __init__(
        self,
        config: ToTConfig,
        llm_client: Any = None,
        **kwargs: Any,
    ):
        """
        Initialize Tree-of-Thoughts planner.

        Args:
            config: ToT configuration
            llm_client: LLM client for thought generation/evaluation
            **kwargs: Additional arguments
        """
        super().__init__(config)
        self.config: ToTConfig = config
        self.llm_client = llm_client

        # Statistics
        self._total_nodes_generated = 0
        self._total_nodes_evaluated = 0

    @classmethod
    def from_config(
        cls,
        config: ToTConfig,
        llm_client: Any = None,
        **kwargs: Any,
    ) -> TreeOfThoughtsPlanner:
        """Create planner from configuration."""
        return cls(config=config, llm_client=llm_client, **kwargs)

    def plan(self, request: PlanRequest) -> PlanResult:
        """
        Generate a plan using Tree-of-Thoughts search.

        Args:
            request: Planning request with goal, tools, constraints

        Returns:
            PlanResult with generated steps
        """
        self._total_nodes_generated = 0
        self._total_nodes_evaluated = 0

        # Initialize root node
        root = ThoughtNode(thought="", score=1.0)

        # Format tools for prompts
        tools_str = self._format_tools(request.tools)

        # Run tree search
        if self.config.search_method == SearchMethod.BFS:
            best_path = self._bfs_search(root, request, tools_str)
        else:
            best_path = self._dfs_search(root, request, tools_str)

        # Convert path to plan
        return self._path_to_plan(best_path, request)

    def _bfs_search(
        self,
        root: ThoughtNode,
        request: PlanRequest,
        tools_str: str,
    ) -> list[ThoughtNode]:
        """
        Breadth-first search for best plan.

        Explores the tree level by level, keeping top-k nodes at each level.
        """
        queue: list[ThoughtNode] = [root]
        best_complete_path: list[ThoughtNode] = []
        best_complete_score = -1.0

        for depth in range(self.config.max_depth):
            if not queue:
                break

            next_queue: list[ThoughtNode] = []

            for node in queue:
                # Generate candidate thoughts
                candidates = self._generate_thoughts(node, request, tools_str)

                for thought_info in candidates:
                    # Create child node
                    child = ThoughtNode(
                        thought=thought_info.get("thought", ""),
                        parent=node,
                        tool_id=thought_info.get("tool_id"),
                        metadata={"reasoning": thought_info.get("reasoning", "")},
                    )

                    # Evaluate thought
                    score = self._evaluate_thought(child, request)
                    child.score = score
                    self._total_nodes_evaluated += 1

                    # Skip low-scoring thoughts
                    if score < self.config.min_thought_score:
                        continue

                    node.children.append(child)
                    next_queue.append(child)

                    # Check for early stopping
                    if score >= self.config.early_stop_score:
                        path = child.get_path()
                        if len(path) >= request.min_steps:
                            return path

                    # Update best complete path
                    if child.step_index >= request.min_steps - 1:
                        path = child.get_path()
                        avg_score = child.get_cumulative_score()
                        if avg_score > best_complete_score:
                            best_complete_score = avg_score
                            best_complete_path = path

            # Keep top-k nodes for next level
            next_queue.sort(key=lambda n: n.score, reverse=True)
            queue = next_queue[: self.config.beam_width]

        # Return best path found
        if best_complete_path:
            return best_complete_path

        # Fallback: return path to highest-scoring node
        if queue:
            best_node = max(queue, key=lambda n: n.get_cumulative_score())
            return best_node.get_path()

        return [root]

    def _dfs_search(
        self,
        root: ThoughtNode,
        request: PlanRequest,
        tools_str: str,
    ) -> list[ThoughtNode]:
        """
        Depth-first search for best plan.

        Explores each path to completion before backtracking.
        """
        best_path: list[ThoughtNode] = []
        best_score = -1.0

        def dfs(node: ThoughtNode, visited_depth: int):
            nonlocal best_path, best_score

            # Check if we've reached desired depth
            if visited_depth >= request.min_steps:
                path = node.get_path()
                avg_score = node.get_cumulative_score()
                if avg_score > best_score:
                    best_score = avg_score
                    best_path = path

                # Early stop if score is high enough
                if avg_score >= self.config.early_stop_score:
                    return True  # Signal to stop search

            # Don't exceed max depth
            if visited_depth >= self.config.max_depth:
                return False

            # Generate and explore candidates
            candidates = self._generate_thoughts(node, request, tools_str)

            # Sort by initial evaluation for better pruning
            scored_candidates = []
            for thought_info in candidates:
                child = ThoughtNode(
                    thought=thought_info.get("thought", ""),
                    parent=node,
                    tool_id=thought_info.get("tool_id"),
                    metadata={"reasoning": thought_info.get("reasoning", "")},
                )
                score = self._evaluate_thought(child, request)
                child.score = score
                self._total_nodes_evaluated += 1

                if score >= self.config.min_thought_score:
                    scored_candidates.append((child, score))

            # Explore in order of score
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            for child, _ in scored_candidates:
                node.children.append(child)
                if dfs(child, visited_depth + 1):
                    return True  # Propagate early stop

            return False

        dfs(root, 0)

        return best_path if best_path else [root]

    def _generate_thoughts(
        self,
        node: ThoughtNode,
        request: PlanRequest,
        tools_str: str,
    ) -> list[dict[str, Any]]:
        """
        Generate candidate thoughts for next step.

        Args:
            node: Current node in the tree
            request: Planning request
            tools_str: Formatted tools string

        Returns:
            List of thought candidates with tool_id and reasoning
        """
        self._total_nodes_generated += self.config.branch_factor

        # If no LLM client, use rule-based fallback
        if self.llm_client is None:
            return self._generate_thoughts_fallback(node, request)

        # Format current progress
        progress = self._format_progress(node)

        # Build prompt
        prompt = self.THOUGHT_GENERATION_PROMPT.format(
            goal=request.goal,
            tools=tools_str,
            progress=progress if progress else "No steps taken yet.",
            n=self.config.branch_factor,
        )

        try:
            # Call LLM
            response = self.llm_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=self.config.generation_temperature,
            )

            # Parse response
            candidates = self._parse_thoughts_response(response)
            if candidates:
                return candidates
        except Exception as e:
            logger.warning(f"LLM thought generation failed: {e}")

        # Fallback to rule-based
        return self._generate_thoughts_fallback(node, request)

    def _evaluate_thought(self, node: ThoughtNode, request: PlanRequest) -> float:
        """
        Evaluate a thought node's quality.

        Args:
            node: Thought node to evaluate
            request: Planning request

        Returns:
            Score between 0 and 1
        """
        # If no LLM client, use heuristic evaluation
        if self.llm_client is None:
            return self._evaluate_thought_heuristic(node, request)

        # Format previous steps
        previous_steps = self._format_progress(node.parent) if node.parent else "None"

        # Build prompt
        prompt = self.THOUGHT_EVALUATION_PROMPT.format(
            goal=request.goal,
            previous_steps=previous_steps,
            thought=node.thought,
            tool_id=node.tool_id or "None",
        )

        try:
            # Call LLM
            response = self.llm_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=self.config.evaluation_temperature,
            )

            # Parse score
            score = self._parse_evaluation_response(response)
            return score
        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")

        # Fallback to heuristic
        return self._evaluate_thought_heuristic(node, request)

    def _generate_thoughts_fallback(
        self,
        node: ThoughtNode,
        request: PlanRequest,
    ) -> list[dict[str, Any]]:
        """
        Rule-based thought generation fallback.

        Used when LLM is not available.
        """
        candidates = []
        used_tools = set()

        # Get tools already used in path
        for path_node in node.get_path():
            if path_node.tool_id:
                used_tools.add(path_node.tool_id)

        # Generate thoughts for unused tools
        for tool in request.tools:
            tool_name = tool.name if hasattr(tool, "name") else str(tool)
            if tool_name not in used_tools:
                candidates.append(
                    {
                        "thought": f"Use {tool_name} to help with: {request.goal[:50]}...",
                        "tool_id": tool_name,
                        "reasoning": "Next available tool",
                    }
                )
                if len(candidates) >= self.config.branch_factor:
                    break

        # If not enough, add generic thoughts
        while len(candidates) < self.config.branch_factor:
            step_num = node.step_index + 1
            candidates.append(
                {
                    "thought": f"Step {step_num}: Continue working on {request.goal[:30]}...",
                    "tool_id": None,
                    "reasoning": "Generic progress step",
                }
            )

        return candidates[: self.config.branch_factor]

    def _evaluate_thought_heuristic(
        self,
        node: ThoughtNode,
        request: PlanRequest,
    ) -> float:
        """
        Heuristic thought evaluation.

        Used when LLM is not available.
        """
        score = 0.5  # Base score

        # Bonus for having a tool
        if node.tool_id:
            score += 0.2

        # Bonus if tool name appears in goal
        goal_lower = request.goal.lower()
        if node.tool_id and node.tool_id.lower() in goal_lower:
            score += 0.1

        # Bonus if thought mentions goal keywords
        thought_lower = node.thought.lower()
        goal_words = set(goal_lower.split())
        thought_words = set(thought_lower.split())
        overlap = len(goal_words & thought_words)
        score += min(overlap * 0.05, 0.2)

        return min(score, 1.0)

    def _format_tools(self, tools: list) -> str:
        """Format tools list for prompts."""
        if not tools:
            return "No tools available"

        tool_strs = []
        for tool in tools:
            if hasattr(tool, "name") and hasattr(tool, "description"):
                tool_strs.append(f"- {tool.name}: {tool.description}")
            elif hasattr(tool, "name"):
                tool_strs.append(f"- {tool.name}")
            else:
                tool_strs.append(f"- {str(tool)}")

        return "\n".join(tool_strs)

    def _format_progress(self, node: Optional[ThoughtNode]) -> str:
        """Format current progress for prompts."""
        if node is None:
            return ""

        thoughts = node.get_path_thoughts()
        if not thoughts:
            return ""

        return "\n".join(f"Step {i + 1}: {t}" for i, t in enumerate(thoughts))

    def _parse_thoughts_response(self, response: str) -> list[dict[str, Any]]:
        """Parse LLM response for thought candidates."""
        try:
            # Try to extract JSON array
            response = response.strip()

            # Remove code fences if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            # Find JSON array
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                candidates = json.loads(json_str)
                if isinstance(candidates, list):
                    return candidates
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse thoughts response: {e}")

        return []

    def _parse_evaluation_response(self, response: str) -> float:
        """Parse LLM response for evaluation score."""
        try:
            response = response.strip()

            # Remove code fences if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            # Try JSON parsing
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                result = json.loads(json_str)
                score = result.get("score", 5)
                return min(max(score / 10.0, 0.0), 1.0)

            # Try to find a number
            import re

            numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", response)
            if numbers:
                score = float(numbers[0])
                if score > 1:
                    score = score / 10.0
                return min(max(score, 0.0), 1.0)

        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse evaluation response: {e}")

        return 0.5  # Default middle score

    def _path_to_plan(
        self,
        path: list[ThoughtNode],
        request: PlanRequest,
    ) -> PlanResult:
        """
        Convert a thought path to a PlanResult.

        Args:
            path: List of ThoughtNodes from root to leaf
            request: Original planning request

        Returns:
            PlanResult with steps
        """
        steps = []

        for i, node in enumerate(path):
            # Skip root node (empty thought)
            if not node.thought:
                continue

            step = PlanStep(
                id=len(steps),
                action=node.thought,
                tool_id=node.tool_id,
                inputs={},
                depends_on=[len(steps) - 1] if steps else [],
                expected_outputs=[],
                description=node.metadata.get("reasoning", ""),
            )
            steps.append(step)

        # Ensure we have at least min_steps
        while len(steps) < request.min_steps and len(steps) < request.max_steps:
            step = PlanStep(
                id=len(steps),
                action=f"Continue execution toward: {request.goal[:50]}",
                tool_id=None,
                inputs={},
                depends_on=[len(steps) - 1] if steps else [],
                expected_outputs=[],
                description="Auto-generated step to meet minimum",
            )
            steps.append(step)

        # Limit to max_steps
        steps = steps[: request.max_steps]

        return PlanResult(
            steps=steps,
            success=len(steps) >= request.min_steps,
            error_message=None if len(steps) >= request.min_steps else "Plan too short",
            metadata={
                "search_method": self.config.search_method.value,
                "nodes_generated": self._total_nodes_generated,
                "nodes_evaluated": self._total_nodes_evaluated,
                "path_length": len(path),
            },
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get planning statistics."""
        return {
            "total_nodes_generated": self._total_nodes_generated,
            "total_nodes_evaluated": self._total_nodes_evaluated,
            "config": {
                "max_depth": self.config.max_depth,
                "branch_factor": self.config.branch_factor,
                "search_method": self.config.search_method.value,
                "beam_width": self.config.beam_width,
            },
        }
