from __future__ import annotations

import json
import logging
from typing import Any

from sage.libs.agentic.agents.planning.hierarchical_planner import HierarchicalPlanner
from sage.libs.agentic.agents.planning.react_planner import ReActConfig, ReActPlanner
from sage.libs.agentic.agents.planning.schemas import PlannerConfig
from sage.libs.agentic.agents.planning.simple_llm_planner import SimpleLLMPlanner
from sage.libs.agentic.agents.planning.tot_planner import ToTConfig
from sage.libs.agentic.agents.planning.tot_planner import TreeOfThoughtsPlanner as ToTPlanner

from .llm_adapter import GeneratorToClientAdapter
from .planner_adapter import SageLibsPlannerAdapter

logger = logging.getLogger(__name__)


class PlannerRouter:
    """
    Routes user queries to the appropriate planner based on intent classification.
    """

    def __init__(self, generator, default_planner="llm"):
        self.generator = generator
        self.llm_client = GeneratorToClientAdapter(generator)
        self.default_planner_type = default_planner

        # Initialize planners
        # 1. Simple LLM Planner (Baseline)
        self.simple_planner = SimpleLLMPlanner(generator=generator)

        # 2. ReAct Planner (Reasoning)
        self.react_planner = SageLibsPlannerAdapter(
            ReActPlanner, ReActConfig(max_iterations=5), self.llm_client
        )

        # 3. ToT Planner (Complex/Exploratory)
        self.tot_planner = SageLibsPlannerAdapter(
            ToTPlanner, ToTConfig(max_depth=3, branch_factor=3), self.llm_client
        )

        # 4. Hierarchical Planner (Long-horizon)
        self.hierarchical_planner = SageLibsPlannerAdapter(
            HierarchicalPlanner, PlannerConfig(), self.llm_client
        )

    def _classify_intent(self, user_query: str) -> str:
        """
        Classify the user query into one of the planner types.
        """
        prompt = """
You are an expert intent classifier for an AI agent.
Analyze the user's query and select the most suitable planning strategy.

Strategies:
1. "simple": For direct questions, simple tasks, or when no tools are needed. (e.g., "Hello", "What is 2+2?")
2. "react": For tasks requiring multi-step reasoning and tool usage. (e.g., "Search for X and summarize it")
3. "tot": For complex problems requiring exploration of multiple possibilities or creative writing. (e.g., "Write a novel outline", "Solve a complex riddle")
4. "hierarchical": For very long, complex tasks with many sub-tasks. (e.g., "Plan a 3-day trip including flights, hotels, and restaurants")

User Query: "{query}"

Return ONLY the strategy name (simple, react, tot, hierarchical) in JSON format: {{"strategy": "..."}}
"""
        try:
            response = self.llm_client.chat(
                [
                    {"role": "system", "content": "You are an intent classifier."},
                    {"role": "user", "content": prompt.format(query=user_query)},
                ],
                temperature=0.1,
            )

            # Parse JSON
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data.get("strategy", "simple").lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}. Using default.")

        return "simple"

    def plan(
        self,
        profile_system_prompt: str,
        user_query: str,
        tools: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Route to the appropriate planner.
        """
        strategy = self._classify_intent(user_query)
        logger.info(f"Selected planning strategy: {strategy}")

        if strategy == "react":
            return self.react_planner.plan(profile_system_prompt, user_query, tools)
        elif strategy == "tot":
            return self.tot_planner.plan(profile_system_prompt, user_query, tools)
        elif strategy == "hierarchical":
            return self.hierarchical_planner.plan(profile_system_prompt, user_query, tools)
        else:
            return self.simple_planner.plan(profile_system_prompt, user_query, tools)
