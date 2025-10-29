"""
SageFlow Middleware Service

This module provides the middleware service interface for SageFlow,
wrapping the Python bindings from the sageFlow C++ core.
"""

# Micro-service wrapper
from .python.micro_service.sage_flow_service import SageFlowService

# Core Python bindings
from .python.sage_flow import SageFlow

__all__ = ["SageFlow", "SageFlowService"]
