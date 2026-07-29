"""SAGE Platform - Service Abstractions

Layer: L2 (Platform Services - Service Module)

Base classes for SAGE services.

This module provides the BaseService abstract class that all SAGE services
should inherit from. It provides:
- Service context integration
- Logger access
- Service-to-service communication helpers

Architecture:
- Uses TYPE_CHECKING import for sage.kernel types (acceptable for type hints)
- Provides runtime service infrastructure
"""

from .base_service import BaseService

__all__ = [
    "BaseService",
]
