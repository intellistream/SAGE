"""
Base Agent Interface for Studio Swarm Architecture
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from sage.studio.models.agent_step import AgentStep
from sage.studio.tools.base import BaseTool


class BaseAgent(ABC):
    """
    Base class for specialized agents in the Swarm.
    Each agent has a specific role and a set of tools.
    """

    def __init__(self, name: str, role: str, tools: list[BaseTool]):
        self.name = name
        self.role = role
        self.tools = {t.name: t for t in tools}

    @abstractmethod
    async def run(self, query: str, history: list[dict] = None) -> AsyncGenerator[AgentStep, None]:
        """
        Execute the agent's task.
        Yields AgentSteps to report progress.
        """
        pass
