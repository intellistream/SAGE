"""
Queue Backend Adapter

Provides a unified interface for different queue backends and information
about available queue implementations.
"""

import os
import sys
import importlib.util
from typing import Dict, Any, List, Optional


def get_queue_backend_info() -> Dict[str, Any]:
    """
    Get information about available queue backends.
    
    Returns:
        Dict containing backend information:
        - current_backend: The currently active backend
        - sage_available: Whether SAGE mmap_queue extension is available
        - backends: List of available backends
        - capabilities: Backend capabilities
    """
    info = {
        "current_backend": "python_queue",
        "sage_available": False,
        "backends": ["python_queue"],
        "capabilities": {
            "multiprocess": False,
            "memory_mapped": False,
            "high_performance": False
        }
    }
    
    # Check if SAGE mmap_queue extension is available
    try:
        import sage_ext.mmap_queue
        from sage_ext.mmap_queue import SageQueue
        
        info["sage_available"] = True
        info["current_backend"] = "sage_mmap_queue"
        info["backends"].append("sage_mmap_queue")
        info["capabilities"]["multiprocess"] = True
        info["capabilities"]["memory_mapped"] = True
        info["capabilities"]["high_performance"] = True
        
        # Check if C++ extension is properly built
        try:
            # Try to create a test queue to verify the extension works
            test_queue = SageQueue(name="test_backend_check", maxsize=10)
            test_queue.put("test")
            test_queue.get()
            test_queue.close()
            info["extension_status"] = "working"
        except Exception as e:
            info["extension_status"] = f"error: {str(e)}"
            info["sage_available"] = False
            info["current_backend"] = "python_queue"
            
    except ImportError as e:
        info["extension_status"] = f"not_available: {str(e)}"
    
    # Check for Ray queue availability
    try:
        from ray.util.queue import Queue as RayQueue
        info["backends"].append("ray_queue")
        info["capabilities"]["distributed"] = True
    except ImportError:
        pass
    
    return info


def get_recommended_queue_backend() -> str:
    """
    Get the recommended queue backend based on availability and performance.
    
    Returns:
        String name of recommended backend
    """
    info = get_queue_backend_info()
    
    if info["sage_available"] and info.get("extension_status") == "working":
        return "sage_mmap_queue"
    elif "ray_queue" in info["backends"]:
        return "ray_queue"
    else:
        return "python_queue"


def create_queue(backend: Optional[str] = None, **kwargs):
    """
    Create a queue using the specified or recommended backend.
    
    Args:
        backend: Backend to use ('sage_mmap_queue', 'ray_queue', 'python_queue')
        **kwargs: Backend-specific arguments
    
    Returns:
        Queue instance
    """
    if backend is None:
        backend = get_recommended_queue_backend()
    
    if backend == "sage_mmap_queue":
        try:
            from sage_ext.mmap_queue import SageQueue
            return SageQueue(**kwargs)
        except ImportError:
            raise ImportError("SAGE mmap_queue extension not available")
    
    elif backend == "ray_queue":
        try:
            from ray.util.queue import Queue as RayQueue
            return RayQueue(**kwargs)
        except ImportError:
            raise ImportError("Ray queue not available")
    
    elif backend == "python_queue":
        import queue
        return queue.Queue(**kwargs)
    
    else:
        raise ValueError(f"Unknown backend: {backend}")


def get_queue_backends() -> List[str]:
    """Get list of available queue backends."""
    info = get_queue_backend_info()
    return info["backends"]


def is_sage_queue_available() -> bool:
    """Check if SAGE mmap_queue extension is available and working."""
    info = get_queue_backend_info()
    return info["sage_available"] and info.get("extension_status") == "working"
