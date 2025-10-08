"""
SageDB Middleware Service

This module provides the middleware service interface for SageDB,
wrapping the Python bindings from the sageDB C++ core.
"""

# Core Python bindings
from .python.sage_db import SageDB
from .python.multimodal_sage_db import MultimodalSageDB

# Micro-service wrapper
from .python.micro_service.sage_db_service import SageDBService, SageDBServiceConfig

__all__ = ['SageDB', 'MultimodalSageDB', 'SageDBService', 'SageDBServiceConfig']
