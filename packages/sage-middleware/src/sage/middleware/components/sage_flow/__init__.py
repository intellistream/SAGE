# Backward-compatible import surface for SAGE-Flow component

# CRITICAL: Import python package first to ensure _sage_flow extension is loaded
# This must happen before importing sage_flow.py which depends on _sage_flow
from . import python  # noqa: F401

# Re-export python.sage_flow module contents
# This ensures _sage_flow is available when sage_flow.py executes
from .python.sage_flow import *  # noqa: F401,F403
