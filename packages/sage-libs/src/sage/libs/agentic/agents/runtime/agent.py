from __future__ import annotations

import logging
from typing import Any, Generator

from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
from sage.libs.agentic.agents.planning.simple_llm_planner import SimpleLLMPlanner
from sage.libs.agentic.agents.profile.profile import BaseProfile

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Production-Ready Agent Runtime (L3)

    Orchestrates the agent execution loop:
    1. Plan generation (using Planner)
    2. Step-by-step execution
    3. Tool validation and error handling
    4. Observation collection
    """

    def __init__(
        self,
        profile: BaseProfile,
        planner: SimpleLLMPlanner,
        tools: MCPRegistry,
        max_steps: int = 10,
    ):
        self.profile = profile
        self.planner = planner
        self.tools = tools
        self.max_steps = max_steps

    def step(self, user_query: str) -> Generator[dict[str, Any], None, None]:
        """
        Execute the agent loop for a given query.

        Yields structured observations:
        - {"type": "plan", "steps": [...]}
        - {"type": "action", "tool": "...", "args": "..."}
        - {"type": "observation", "content": "..."}
        - {"type": "error", "content": "..."}
        - {"type": "reply", "content": "..."}
        """
        logger.info(f"AgentRuntime starting execution for query: {user_query}")

        # 1. Generate Plan
        try:
            tools_desc = self.tools.describe()
            plan = self.planner.plan(
                profile_system_prompt=self.profile.render_system_prompt(),
                user_query=user_query,
                tools=tools_desc,
            )
            yield {"type": "plan", "steps": plan}
            logger.info(f"Plan generated with {len(plan)} steps")
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            yield {"type": "error", "content": f"Planning failed: {str(e)}"}
            return

        # 2. Execute Steps
        for i, step in enumerate(plan):
            if i >= self.max_steps:
                logger.warning("Max steps reached, stopping execution")
                break

            step_type = step.get("type")

            if step_type == "reply":
                content = step.get("text", "")
                yield {"type": "reply", "content": content}
                logger.info("Agent replied")
                break  # Usually reply is the last step

            elif step_type == "tool":
                tool_name = step.get("name")
                tool_args = step.get("arguments", {})

                yield {"type": "action", "tool": tool_name, "args": tool_args}
                logger.info(f"Executing tool: {tool_name}")

                # Safety Check: Validate arguments against schema
                # Note: MCPRegistry.call might do this, but we can add explicit check if needed.
                # For now, we rely on the tool's own validation or MCPRegistry.

                try:
                    result = self.tools.call(tool_name, tool_args)
                    yield {"type": "observation", "content": result}
                    logger.info(f"Tool {tool_name} executed successfully")
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    yield {"type": "error", "content": f"Tool execution failed: {str(e)}"}
                    # Continue to next step? Or stop?
                    # Usually we continue, maybe the next step can recover or the LLM can re-plan (if we had re-planning).
                    # For this simple runtime, we continue.

            else:
                logger.warning(f"Unknown step type: {step_type}")

    def execute(self, user_query: str) -> dict[str, Any]:
        """
        Execute the agent loop and return the final result.
        """
        final_reply = ""
        observations = []

        for event in self.step(user_query):
            if event["type"] == "reply":
                final_reply = event["content"]
            elif event["type"] == "observation":
                observations.append(event["content"])
            elif event["type"] == "error":
                observations.append(f"Error: {event['content']}")

        return {"reply": final_reply, "observations": observations}
