"""Agentic layer - Agent framework and workflow optimization.

This module provides high-level agent abstractions and workflow optimization:
- agents: LangChain-style agent framework with pre-built bots
- workflow: Workflow optimization framework for agentic systems

These are coarse-grained systems built on top of foundation utilities.
"""

from . import agents, intent, workflow

__all__ = [
    "agents",
    "intent",
    "workflow",
]
