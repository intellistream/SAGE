"""
Hierarchical Planner

Implements multi-step hierarchical planning with tool selection and dependency management.
Generates 5-10 step plans using LLM, validates dependencies, and assigns tools.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from jinja2 import Template

from .base import BasePlanner
from .dependency_graph import DependencyGraph
from .schemas import (
    PlannerConfig,
    PlanRequest,
    PlanResult,
    PlanStep,
)
from .utils.repair import create_fallback_plan, extract_and_repair_plan
from .utils.validators import (
    suggest_plan_improvements,
)

logger = logging.getLogger(__name__)


class HierarchicalPlanner(BasePlanner):
    """
    Hierarchical planner using LLM for multi-step task decomposition.

    Features:
    - 5-10 step plan generation
    - Dependency graph validation
    - Tool selection integration
    - Plan repair and validation
    - Retries on failure

    Architecture:
    - Uses Jinja2 template for prompting
    - Integrates with ToolSelector for tool assignment
    - Validates dependencies via DependencyGraph
    - Repairs malformed LLM outputs
    """

    name: str = "hierarchical_planner"

    def __init__(
        self,
        config: PlannerConfig,
        llm_client: Any = None,
        tool_selector: Optional[Any] = None,
        **kwargs: Any,
    ):
        """
        Initialize hierarchical planner.

        Args:
            config: Planner configuration
            llm_client: LLM client for plan generation (UnifiedInferenceClient)
            tool_selector: Optional tool selector for enriching steps
            **kwargs: Additional arguments
        """
        super().__init__(config)

        self.llm_client = llm_client
        self.tool_selector = tool_selector

        # Load prompt template
        self.template = self._load_template()

        # Statistics
        self._total_plans = 0
        self._failed_plans = 0
        self._repaired_plans = 0

    @classmethod
    def from_config(
        cls,
        config: PlannerConfig,
        llm_client: Any = None,
        tool_selector: Optional[Any] = None,
        **kwargs: Any,
    ) -> "HierarchicalPlanner":
        """
        Create planner from configuration.

        Args:
            config: Planner configuration
            llm_client: LLM client instance
            tool_selector: Optional tool selector
            **kwargs: Additional resources

        Returns:
            Initialized HierarchicalPlanner instance
        """
        return cls(config=config, llm_client=llm_client, tool_selector=tool_selector, **kwargs)

    def _load_template(self) -> Template:
        """
        Load Jinja2 template for plan generation.

        Returns:
            Loaded Jinja2 Template
        """
        template_path = Path(__file__).parent / "prompt_templates" / "planner_v2.j2"

        try:
            with open(template_path, encoding="utf-8") as f:
                template_str = f.read()
            return Template(template_str)
        except Exception as e:
            logger.warning(f"Failed to load template from {template_path}: {e}")
            # Fallback to minimal template
            fallback_template = """Generate a plan with {{ min_steps }}-{{ max_steps }} steps for: {{ goal }}
Available tools: {% for tool in tools %}{{ tool.name }}{% if not loop.last %}, {% endif %}{% endfor %}
Return JSON array of steps with id, action, tool_id, inputs, depends_on, expected_outputs, description."""
            return Template(fallback_template)

    def _render_prompt(self, request: PlanRequest) -> str:
        """
        Render prompt from template and request.

        Args:
            request: PlanRequest containing goal, tools, constraints

        Returns:
            Rendered prompt string
        """
        try:
            return self.template.render(
                goal=request.goal,
                context=request.context,
                tools=request.tools,
                constraints=request.constraints,
                min_steps=request.min_steps,
                max_steps=request.max_steps,
            )
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            # Fallback to simple prompt
            return (
                f"Generate a {request.min_steps}-{request.max_steps} step plan for: {request.goal}"
            )

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM to generate plan.

        Args:
            prompt: Rendered prompt string

        Returns:
            LLM response text

        Raises:
            RuntimeError: If LLM client not configured or call fails
        """
        if self.llm_client is None:
            raise RuntimeError("LLM client not configured for hierarchical planner")

        try:
            # Prepare messages in chat format
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert task planner. Generate structured, executable plans.",
                },
                {"role": "user", "content": prompt},
            ]

            # Call LLM (supports UnifiedInferenceClient interface)
            response = self.llm_client.chat(
                messages=messages, temperature=self.config.llm_temperature, max_tokens=2000
            )

            # Handle different return formats
            if isinstance(response, tuple):
                # (text, logprobs) format
                return response[0]
            elif isinstance(response, str):
                return response
            else:
                logger.warning(f"Unexpected LLM response type: {type(response)}")
                return str(response)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"Failed to generate plan via LLM: {e}") from e

    def _parse_llm_output(self, output: str, request: PlanRequest) -> list[PlanStep]:
        """
        Parse and repair LLM output into plan steps.

        Args:
            output: Raw LLM output text
            request: Original plan request

        Returns:
            List of parsed PlanStep instances
        """
        # Extract and repair plan using utility functions
        step_dicts = extract_and_repair_plan(output)

        if step_dicts is None:
            logger.warning("Failed to parse LLM output, using fallback plan")
            self._repaired_plans += 1
            step_dicts = create_fallback_plan(request.goal, num_steps=request.min_steps)

        # Convert to PlanStep objects
        steps = []
        for step_dict in step_dicts:
            try:
                step = PlanStep(**step_dict)
                steps.append(step)
            except Exception as e:
                logger.warning(f"Failed to create PlanStep from {step_dict}: {e}")
                continue

        return steps

    def _validate_and_repair_dependencies(self, steps: list[PlanStep]) -> list[PlanStep]:
        """
        Validate dependencies and repair if needed.

        Args:
            steps: List of plan steps

        Returns:
            List of steps with validated/repaired dependencies
        """
        if not self.config.enable_dependency_check:
            return steps

        # Build dependency graph
        try:
            graph = DependencyGraph(steps)

            # Check if validation needed
            if not graph.validate(max_steps=self.config.max_steps):
                logger.warning("Plan has invalid dependencies, attempting repair")
                self._repaired_plans += 1

                if self.config.enable_repair:
                    repaired_steps = graph.repair_dependencies()
                    return repaired_steps
                else:
                    logger.error("Repair disabled, returning original steps")
                    return steps

            return steps

        except Exception as e:
            logger.error(f"Dependency validation failed: {e}")
            if self.config.enable_repair:
                # Best-effort: remove all dependencies
                return [step.model_copy(update={"depends_on": []}) for step in steps]
            return steps

    def _enrich_with_tool_selection(
        self, steps: list[PlanStep], request: PlanRequest
    ) -> list[PlanStep]:
        """
        Enrich plan steps with tool selection.

        Uses tool selector to assign appropriate tools to steps.

        Args:
            steps: List of plan steps
            request: Original plan request

        Returns:
            Steps enriched with tool assignments
        """
        if self.tool_selector is None:
            logger.debug("No tool selector configured, skipping tool enrichment")
            return steps

        enriched_steps = []

        for step in steps:
            # Skip if tool already assigned
            if step.tool_id:
                enriched_steps.append(step)
                continue

            # Create query for tool selection
            try:
                from sage.libs.agentic.agents.action.tool_selection.schemas import (
                    ToolSelectionQuery,
                )

                query = ToolSelectionQuery(
                    sample_id=f"plan_step_{step.id}",
                    instruction=step.action,
                    context={"description": step.description or ""},
                    candidate_tools=[t.tool_id for t in request.tools],
                )

                # Select top tool
                predictions = self.tool_selector.select(query, top_k=1)

                if predictions:
                    selected_tool = predictions[0].tool_id
                    enriched_step = step.model_copy(update={"tool_id": selected_tool})
                    enriched_steps.append(enriched_step)
                else:
                    enriched_steps.append(step)

            except Exception as e:
                logger.warning(f"Tool selection failed for step {step.id}: {e}")
                enriched_steps.append(step)

        return enriched_steps

    def plan(self, request: PlanRequest) -> PlanResult:
        """
        Generate hierarchical plan for the given request.

        Workflow:
        1. Render prompt from template
        2. Call LLM to generate plan
        3. Parse and repair LLM output
        4. Validate dependencies
        5. Enrich with tool selection (optional)
        6. Validate final plan
        7. Return PlanResult

        Args:
            request: PlanRequest with goal, tools, constraints

        Returns:
            PlanResult with generated steps or error
        """
        self._total_plans += 1

        # Retry loop
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(f"Planning attempt {attempt + 1}/{self.config.max_retries + 1}")

                # Step 1: Render prompt
                prompt = self._render_prompt(request)
                logger.debug(f"Rendered prompt: {prompt[:200]}...")

                # Step 2: Call LLM
                llm_output = self._call_llm(prompt)
                logger.debug(f"LLM output: {llm_output[:200]}...")

                # Step 3: Parse output
                steps = self._parse_llm_output(llm_output, request)

                if not steps:
                    raise ValueError("No valid steps parsed from LLM output")

                logger.info(f"Parsed {len(steps)} steps from LLM output")

                # Step 4: Validate dependencies
                steps = self._validate_and_repair_dependencies(steps)

                # Step 5: Enrich with tool selection
                steps = self._enrich_with_tool_selection(steps, request)

                # Step 6: Create result
                result = PlanResult(
                    steps=steps,
                    success=True,
                    metadata={
                        "planner": self.name,
                        "attempt": attempt + 1,
                        "num_steps": len(steps),
                        "llm_temperature": self.config.llm_temperature,
                    },
                )

                # Step 7: Validate final plan
                if self.validate_plan(result):
                    logger.info(f"Successfully generated plan with {len(steps)} steps")

                    # Add improvement suggestions
                    suggestions = suggest_plan_improvements(steps)
                    if suggestions:
                        result.metadata["suggestions"] = suggestions

                    return result
                else:
                    logger.warning(f"Plan validation failed on attempt {attempt + 1}")
                    if attempt < self.config.max_retries:
                        continue
                    else:
                        # Return best-effort result
                        result.metadata["validation_warning"] = "Plan validation failed"
                        return result

            except Exception as e:
                logger.error(f"Planning attempt {attempt + 1} failed: {e}")

                if attempt >= self.config.max_retries:
                    # Final attempt failed, return error result
                    self._failed_plans += 1

                    return PlanResult(
                        steps=[],
                        success=False,
                        error_message=f"Planning failed after {attempt + 1} attempts: {str(e)}",
                        metadata={"planner": self.name, "attempts": attempt + 1},
                    )

        # Should not reach here
        self._failed_plans += 1
        return PlanResult(
            steps=[],
            success=False,
            error_message="Planning failed: maximum retries exceeded",
            metadata={"planner": self.name},
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get planner statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_plans": self._total_plans,
            "failed_plans": self._failed_plans,
            "repaired_plans": self._repaired_plans,
            "success_rate": (self._total_plans - self._failed_plans) / max(self._total_plans, 1),
            "repair_rate": self._repaired_plans / max(self._total_plans, 1),
        }
