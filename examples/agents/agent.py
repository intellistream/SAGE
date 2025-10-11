"""
Agent module for examples.

This module re-exports functionality from tutorials for backward compatibility.
"""

# Re-export from tutorials
from examples.tutorials.agents.basic_agent import iter_queries, main

# Re-export dependencies for patching in tests
import importlib
import json
import os
import sys
from typing import Any, Dict, Iterable

from sage.common.utils.config.loader import load_config
from sage.libs.agents.action.mcp_registry import MCPRegistry
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.runtime.agent import AgentRuntime
from sage.libs.rag.generator import OpenAIGenerator
from sage.tools.utils.env import (
    get_api_key,
    load_environment_file,
    should_use_real_api,
)

__all__ = [
    "iter_queries",
    "main",
    # Dependencies
    "importlib",
    "json",
    "os",
    "sys",
    "load_config",
    "MCPRegistry",
    "LLMPlanner",
    "BaseProfile",
    "AgentRuntime",
    "OpenAIGenerator",
    "get_api_key",
    "load_environment_file",
    "should_use_real_api",
]
