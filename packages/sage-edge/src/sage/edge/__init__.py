"""SAGE Edge - L6 aggregator shell.

Purpose: mount one or more domain gateways (starting with `sage.llm.gateway`) while
keeping the OpenAI-compatible paths stable at `/v1/*` by default.
"""

from sage.edge._version import __version__
from sage.edge.app import create_app

__all__ = ["__version__", "create_app"]
__layer__ = "L6"
