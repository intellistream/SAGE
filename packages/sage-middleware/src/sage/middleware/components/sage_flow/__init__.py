# Backward-compatible import surface for SAGE-Flow component

# Re-export python package so imports like
#   from sage.middleware.components.sage_flow.sage_flow import StreamEnvironment
# continue to work even after restructuring under python/
from .python.sage_flow import *  # noqa: F401,F403
