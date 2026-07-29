"""
SAGE - RPC Communication Module

Layer: L3 (Kernel)
Dependencies: sage.platform (L2), sage.common (L1)

This module provides RPC-based queue implementations for remote communication.
"""

from .rpc_queue import RPCQueue

__all__ = ["RPCQueue"]
