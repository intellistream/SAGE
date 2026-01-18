"""SAGE Agentic Module - Agent Framework Interfaces.

This module provides the **interface layer** (abstract base classes and factory)
for agent implementations. Concrete implementations are in the external package
`isage-agentic`.

Architecture:
    sage.libs.agentic (this module) - Interface layer (ABCs, factory, types)
    isage-agentic (external PyPI)   - Implementations (ReActAgent, PlanExecute, etc.)

Installation:
    pip install isage-agentic    # Install implementations
    # or
    pip install isage-libs[agentic]

Usage:
    from sage.libs.agentic.interface import (
        BaseAgent, AgentConfig, AgentOutput,
        create, register, registered,
    )

    # Create agent (requires isage-agentic installed)
    agent = create("react", config=AgentConfig(...))
    output = agent.run("What is the weather?")

External implementations auto-register when imported.
See: https://github.com/intellistream/sage-agentic
"""

# Re-export interface
from .interface import *  # noqa: F401, F403
