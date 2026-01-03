from __future__ import annotations

import logging
from typing import Any

from sage.libs.agentic.agents.planning.schemas import PlannerConfig, PlanRequest, ToolMetadata

logger = logging.getLogger(__name__)


class SageLibsPlannerAdapter:
    """
    Adapts sage-libs planners (ReAct, ToT, Hierarchical) to the AgentRuntime interface.
    """

    def __init__(self, planner_cls, config: PlannerConfig, llm_client):
        self.planner = planner_cls(config=config, llm_client=llm_client)

    def plan(
        self,
        profile_system_prompt: str,
        user_query: str,
        tools: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Convert inputs to PlanRequest, call planner, and convert PlanResult to list[dict].
        """
        # 1. Convert tools dict to List[ToolMetadata]
        tool_metadata_list = []
        for name, meta in tools.items():
            tool_metadata_list.append(
                ToolMetadata(
                    tool_id=name,
                    name=name,
                    description=meta.get("description", ""),
                    category=meta.get("category", "general"),
                    input_schema=meta.get("input_schema", {}),
                )
            )

        # 2. Create PlanRequest
        request = PlanRequest(
            goal=user_query,
            context={"system_prompt": profile_system_prompt},
            tools=tool_metadata_list,
            max_steps=10,  # Default
            min_steps=1,
        )

        # 3. Call planner
        try:
            result = self.planner.plan(request)
        except Exception as e:
            logger.error(f"Planner {self.planner.name} failed: {e}")
            return [{"type": "reply", "text": f"Planning failed: {str(e)}"}]

        # 4. Convert PlanResult to list[dict]
        # AgentRuntime expects: [{"type": "tool", "name": "...", "arguments": {...}}, ...]
        runtime_steps = []

        if not result.steps:
            return [{"type": "reply", "text": "No plan generated."}]

        for step in result.steps:
            if step.action == "finish":
                # Some planners might use a 'finish' action
                continue

            # Check if it's a tool call
            # In sage-libs, 'action' is usually the tool name
            # 'inputs' are arguments

            # Heuristic: if action matches a tool name, it's a tool call
            if step.action in tools:
                runtime_steps.append(
                    {"type": "tool", "name": step.action, "arguments": step.inputs}
                )
            else:
                # Treat as thought or unknown action?
                # AgentRuntime doesn't support "thought" steps explicitly in the loop yet,
                # but we can log them or ignore them.
                # If it's a reply-like action?
                pass

        # If no tool steps, maybe it's a direct reply?
        if not runtime_steps:
            # Try to find a final thought or result
            final_thought = getattr(result, "final_thought", None) or "Plan completed."
            runtime_steps.append({"type": "reply", "text": final_thought})
        else:
            # Append a final reply step if not present?
            # AgentRuntime loop executes steps. If the last step is a tool, it will execute it.
            # Then what? The loop continues?
            # AgentRuntime loop: for step in plan: execute.
            # If plan is static, it executes all steps.
            pass

        return runtime_steps
