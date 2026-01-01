"""
Tool Use Agent Package
======================

A modular Agent Pipeline with tool calling capabilities, integrating:
- sage-mem: Hierarchical memory service (STM/MTM/LTM)
- sage-refiner: Context compression service
- sage-db: Vector search service (RAG)
- ReAct planning: Reasoning + Acting with reflection

Pipeline Architecture:
    UserQuerySource -> ToolSelector -> ToolExecutor -> ResponseGenerator -> ResponseSink

Usage:
    from examples.tutorials.L3_libs.agents.tool_use_agent import run_tool_use_demo
    run_tool_use_demo()

Or via command line:
    python -m examples.tutorials.L3_libs.agents.tool_use_agent.pipeline
"""

from .pipeline import run_interactive_mode, run_tool_use_demo

__all__ = [
    "run_tool_use_demo",
    "run_interactive_mode",
]
