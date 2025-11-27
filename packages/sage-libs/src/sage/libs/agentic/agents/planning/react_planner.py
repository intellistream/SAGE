"""
ReAct Planner

Implements ReAct (Reasoning + Acting) planning strategy from:
"ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2023)

The key idea is to interleave reasoning traces (Thought) with actions,
allowing the model to track progress and adjust plans dynamically.

Pattern:
    Thought 1: [reasoning about current state and what to do]
    Action 1: [tool_name(params)]
    Observation 1: [result of action - in planning mode, this is predicted]
    Thought 2: [reasoning based on observation]
    Action 2: [next_tool(params)]
    ...
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from jinja2 import Template
from pydantic import Field

from .base import BasePlanner
from .schemas import (
    PlannerConfig,
    PlanRequest,
    PlanResult,
    PlanStep,
)

logger = logging.getLogger(__name__)


class ReActConfig(PlannerConfig):
    """Configuration for ReAct planner."""

    max_iterations: int = Field(default=10, ge=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    stop_on_finish: bool = Field(default=True)
    include_observations: bool = Field(default=True)  # Include predicted observations

    class Config:
        extra = "allow"


@dataclass
class ReActStep:
    """Single step in ReAct reasoning chain."""

    step_id: int
    thought: str  # Reasoning about what to do
    action: str  # Tool to call
    action_input: dict[str, Any] = field(default_factory=dict)  # Tool parameters
    observation: str = ""  # Predicted result (empty in pure planning mode)
    confidence: float = 0.8

    def to_plan_step(self) -> PlanStep:
        """Convert to standard PlanStep format."""
        return PlanStep(
            id=self.step_id,
            action=self.action,
            tool_id=self.action,
            inputs=self.action_input,
            depends_on=[self.step_id - 1] if self.step_id > 0 else [],
            expected_outputs=[],
            description=self.thought,
        )


@dataclass
class ReActTrace:
    """Complete ReAct reasoning trace."""

    steps: list[ReActStep] = field(default_factory=list)
    final_thought: str = ""
    success: bool = True

    @property
    def reasoning_trace(self) -> str:
        """Get formatted reasoning trace."""
        lines = []
        for step in self.steps:
            lines.append(f"Thought {step.step_id + 1}: {step.thought}")
            lines.append(f"Action {step.step_id + 1}: {step.action}")
            if step.action_input:
                lines.append(f"Action Input {step.step_id + 1}: {step.action_input}")
            if step.observation:
                lines.append(f"Observation {step.step_id + 1}: {step.observation}")
            lines.append("")  # Blank line between steps
        if self.final_thought:
            lines.append(f"Final Thought: {self.final_thought}")
        return "\n".join(lines)

    @property
    def tool_sequence(self) -> list[str]:
        """Get sequence of tools used."""
        return [step.action for step in self.steps if step.action and step.action != "finish"]


class ReActPlanner(BasePlanner):
    """
    ReAct Planner implementing Thought-Action-Observation loop.

    This planner generates step-by-step plans by reasoning about:
    1. Current state and goal
    2. Which tool to use next
    3. Expected results (observations)

    Features:
    - Explicit reasoning traces for interpretability
    - Iterative refinement based on predicted observations
    - Graceful fallback when LLM unavailable
    - Compatible with benchmark framework

    Usage:
        >>> config = ReActConfig(max_iterations=10)
        >>> planner = ReActPlanner(config, llm_client=my_llm)
        >>> request = PlanRequest(goal="Process data and send email", tools=[...])
        >>> result = planner.plan(request)
        >>> print(result.metadata.get("reasoning_trace"))
    """

    name: str = "react_planner"

    # Default prompt template
    DEFAULT_TEMPLATE = """You are a task planning assistant using ReAct (Reasoning + Acting) framework.

## Task
{{ goal }}

## Available Tools
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}

## Constraints
{% for constraint in constraints %}
- {{ constraint }}
{% endfor %}

## Instructions
Generate a step-by-step plan using the Thought-Action pattern.
For each step:
1. Think about what needs to be done next (Thought)
2. Choose a tool to accomplish it (Action)
3. Predict what result you expect (Observation)

Use this exact format:
Thought: [your reasoning about what to do next]
Action: [tool_name]
Action Input: [parameters as JSON if needed]
Observation: [predicted result]

When the task is complete, use:
Thought: [summary of what was accomplished]
Action: finish
Action Input: {}

{% if history %}
## Previous Steps
{% for step in history %}
Thought: {{ step.thought }}
Action: {{ step.action }}
{% if step.action_input %}Action Input: {{ step.action_input }}{% endif %}
{% if step.observation %}Observation: {{ step.observation }}{% endif %}
{% endfor %}
{% endif %}

Generate the next step:"""

    def __init__(
        self,
        config: PlannerConfig,
        llm_client: Any = None,
        tool_selector: Optional[Any] = None,
        **kwargs: Any,
    ):
        """
        Initialize ReAct planner.

        Args:
            config: Planner configuration (ReActConfig recommended)
            llm_client: LLM client for plan generation
            tool_selector: Optional tool selector for fallback
            **kwargs: Additional arguments
        """
        super().__init__(config)

        # Convert config if needed
        if isinstance(config, ReActConfig):
            self.react_config = config
        else:
            self.react_config = ReActConfig(
                min_steps=config.min_steps,
                max_steps=config.max_steps,
            )

        self.llm_client = llm_client
        self.tool_selector = tool_selector
        self.template = self._load_template()

        # Statistics
        self._total_plans = 0
        self._successful_plans = 0

    @classmethod
    def from_config(
        cls,
        config: PlannerConfig,
        llm_client: Any = None,
        tool_selector: Optional[Any] = None,
        **kwargs: Any,
    ) -> "ReActPlanner":
        """Create planner from configuration."""
        return cls(
            config=config,
            llm_client=llm_client,
            tool_selector=tool_selector,
            **kwargs,
        )

    def _load_template(self) -> Template:
        """Load Jinja2 template for ReAct prompting."""
        template_path = Path(__file__).parent / "prompt_templates" / "react_planner.j2"

        try:
            if template_path.exists():
                with open(template_path, encoding="utf-8") as f:
                    template_str = f.read()
                return Template(template_str)
        except Exception as e:
            logger.warning(f"Failed to load template from {template_path}: {e}")

        # Use default template
        return Template(self.DEFAULT_TEMPLATE)

    def _render_prompt(
        self,
        request: PlanRequest,
        history: list[ReActStep],
    ) -> str:
        """Render prompt for next ReAct step."""
        return self.template.render(
            goal=request.goal,
            context=request.context,
            tools=request.tools,
            constraints=request.constraints,
            history=history,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate next step."""
        if self.llm_client is None:
            logger.warning("No LLM client available for ReAct planner")
            return ""

        try:
            # Try chat interface first
            if hasattr(self.llm_client, "chat"):
                messages = [
                    {
                        "role": "system",
                        "content": "You are a ReAct planning assistant. Generate one step at a time using Thought-Action-Observation format.",
                    },
                    {"role": "user", "content": prompt},
                ]
                response = self.llm_client.chat(
                    messages,
                    temperature=self.react_config.temperature,
                    max_tokens=512,
                )
                return response if isinstance(response, str) else str(response)

            # Try generate interface
            if hasattr(self.llm_client, "generate"):
                results = self.llm_client.generate(prompt)
                if results and results[0].get("generations"):
                    return results[0]["generations"][0].get("text", "")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")

        return ""

    def _parse_react_step(
        self,
        response: str,
        step_id: int,
        available_tools: list[str],
    ) -> Optional[ReActStep]:
        """Parse LLM response into ReActStep."""
        import json
        import re

        thought = ""
        action = ""
        action_input = {}
        observation = ""

        # Extract Thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|$)", response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract Action
        action_match = re.search(r"Action:\s*(\S+)", response)
        if action_match:
            action = action_match.group(1).strip()

        # Extract Action Input
        input_match = re.search(r"Action Input:\s*(\{.*?\}|\[.*?\])", response, re.DOTALL)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                action_input = {"raw": input_match.group(1)}

        # Extract Observation (predicted)
        obs_match = re.search(r"Observation:\s*(.+?)(?=Thought:|Action:|$)", response, re.DOTALL)
        if obs_match:
            observation = obs_match.group(1).strip()

        # Validate action
        if action and action != "finish":
            # Try to match with available tools
            action_lower = action.lower()
            matched_tool = None

            for tool in available_tools:
                if tool.lower() == action_lower or tool.lower() in action_lower:
                    matched_tool = tool
                    break

            if matched_tool:
                action = matched_tool
            elif available_tools:
                # Fuzzy match: find tool with most word overlap
                best_match = None
                best_score = 0
                action_words = set(action_lower.replace("_", " ").split())

                for tool in available_tools:
                    tool_words = set(tool.lower().replace("_", " ").split())
                    overlap = len(action_words & tool_words)
                    if overlap > best_score:
                        best_score = overlap
                        best_match = tool

                if best_match and best_score > 0:
                    action = best_match

        if not thought and not action:
            return None

        return ReActStep(
            step_id=step_id,
            thought=thought or f"Step {step_id + 1}",
            action=action or "unknown",
            action_input=action_input,
            observation=observation,
        )

    def _generate_fallback_plan(
        self,
        request: PlanRequest,
    ) -> ReActTrace:
        """Generate fallback plan without LLM using heuristics."""
        tools = request.tools
        available_tools = [t.name if hasattr(t, "name") else str(t) for t in tools]

        if not available_tools:
            return ReActTrace(
                steps=[],
                final_thought="No tools available",
                success=False,
            )

        # Simple heuristic: match goal keywords to tool names
        goal_words = set(request.goal.lower().replace(",", " ").split())
        steps = []

        # Score and sort tools by relevance
        tool_scores = []
        for tool in available_tools:
            tool_words = set(tool.lower().replace("_", " ").split())
            score = len(goal_words & tool_words)

            # Boost common action verbs
            if any(w in tool.lower() for w in ["read", "get", "fetch", "load"]):
                if any(w in request.goal.lower() for w in ["read", "get", "load", "fetch"]):
                    score += 2
            if any(w in tool.lower() for w in ["write", "save", "store", "send"]):
                if any(w in request.goal.lower() for w in ["write", "save", "store", "send"]):
                    score += 2
            if any(w in tool.lower() for w in ["process", "transform", "convert"]):
                if any(w in request.goal.lower() for w in ["process", "convert", "transform"]):
                    score += 2

            tool_scores.append((tool, score))

        tool_scores.sort(key=lambda x: x[1], reverse=True)

        # Select top tools up to max_steps
        num_steps = min(len(tool_scores), self.config.max_steps, request.max_steps)
        selected_tools = [t[0] for t in tool_scores[:num_steps] if t[1] > 0]

        # Ensure minimum steps
        if len(selected_tools) < request.min_steps:
            for tool, _ in tool_scores:
                if tool not in selected_tools:
                    selected_tools.append(tool)
                if len(selected_tools) >= request.min_steps:
                    break

        # Create steps
        for i, tool in enumerate(selected_tools):
            step = ReActStep(
                step_id=i,
                thought=f"Use {tool} to help accomplish the task",
                action=tool,
                action_input={},
                observation=f"Expected: {tool} completes successfully",
                confidence=0.6,
            )
            steps.append(step)

        return ReActTrace(
            steps=steps,
            final_thought=f"Plan generated using {len(steps)} tools",
            success=len(steps) > 0,
        )

    def plan(self, request: PlanRequest) -> PlanResult:
        """
        Generate a plan using ReAct reasoning.

        Args:
            request: PlanRequest with goal, tools, and constraints

        Returns:
            PlanResult with steps and reasoning trace in metadata
        """
        self._total_plans += 1

        # Get available tool names
        available_tools = [t.name if hasattr(t, "name") else str(t) for t in request.tools]

        # Try LLM-based planning
        if self.llm_client is not None:
            trace = self._plan_with_llm(request, available_tools)
        else:
            trace = self._generate_fallback_plan(request)

        # Ensure we have enough steps
        if len(trace.steps) < request.min_steps:
            # Supplement with fallback
            fallback_trace = self._generate_fallback_plan(request)
            existing_tools = {s.action for s in trace.steps}

            for step in fallback_trace.steps:
                if step.action not in existing_tools:
                    step.step_id = len(trace.steps)
                    trace.steps.append(step)
                    existing_tools.add(step.action)
                if len(trace.steps) >= request.min_steps:
                    break

        # Convert to PlanResult
        plan_steps = [step.to_plan_step() for step in trace.steps]

        if trace.success and plan_steps:
            self._successful_plans += 1

        return PlanResult(
            steps=plan_steps,
            success=trace.success and len(plan_steps) > 0,
            error_message=None if trace.success else "Failed to generate plan",
            metadata={
                "reasoning_trace": trace.reasoning_trace,
                "final_thought": trace.final_thought,
                "planner": self.name,
                "num_iterations": len(trace.steps),
            },
        )

    def _plan_with_llm(
        self,
        request: PlanRequest,
        available_tools: list[str],
    ) -> ReActTrace:
        """Generate plan using LLM with ReAct loop."""
        steps: list[ReActStep] = []
        max_iter = min(
            self.react_config.max_iterations,
            request.max_steps + 2,  # Allow some buffer
        )

        for i in range(max_iter):
            # Render prompt with history
            prompt = self._render_prompt(request, steps)

            # Call LLM
            response = self._call_llm(prompt)
            if not response:
                break

            # Parse response
            step = self._parse_react_step(response, len(steps), available_tools)
            if step is None:
                break

            # Check for finish action
            if step.action.lower() == "finish":
                return ReActTrace(
                    steps=steps,
                    final_thought=step.thought,
                    success=True,
                )

            steps.append(step)

            # Check if we have enough steps
            if len(steps) >= request.max_steps:
                break

        return ReActTrace(
            steps=steps,
            final_thought="Plan generation completed" if steps else "No steps generated",
            success=len(steps) > 0,
        )


# Alias for compatibility
ReActPlannerConfig = ReActConfig
