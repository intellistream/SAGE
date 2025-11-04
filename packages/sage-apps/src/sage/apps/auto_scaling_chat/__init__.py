"""
Auto-Scaling Chat System

An intelligent chat system demonstrating SAGE's resource optimization capabilities
through automatic scaling based on user load. Shows cloud infrastructure elasticity
with load balancing and resource monitoring.

Built on SAGE framework using stream processing operators.

Features:
- Simulated user traffic generation
- Automatic scaling based on load thresholds
- Load balancing across server instances
- Resource monitoring and metrics
- Visual feedback on scaling decisions
"""

from .pipeline import run_auto_scaling_demo

__all__ = ["run_auto_scaling_demo"]
