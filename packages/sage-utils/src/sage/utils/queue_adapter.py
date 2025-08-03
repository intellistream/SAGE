"""
Queue Backend Adapter

Provides a unified interface for different queue backends and information
about available queue implementations.

Updated with intelligent auto-fallback system for distributed environments.
"""

import os
import sys
import importlib.util
from typing import Dict, Any, List, Optional
import logging
from typing import Optional, Any
import threading

logger = logging.getLogger(__name__)

# Import the new auto-fallback system
try:
    from .queue_auto_fallback import get_optimal_queue_backend, get_queue_backend_info_detailed, QueueBackendType
    AUTO_FALLBACK_AVAILABLE = True
except ImportError:
    AUTO_FALLBACK_AVAILABLE = False


def get_queue_backend_info() -> Dict[str, Any]:
    """
    Get information about available queue backends.
    
    Returns:
        Dict containing backend information:
        - current_backend: The currently active backend
        - sage_available: Whether SAGE queue extension is available
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
    
    # Check if SAGE queue extension is available
    try:
        import sage_ext.sage_queue.python.sage_queue as sage_queue_module
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        
        info["sage_available"] = True
        info["current_backend"] = "sage_queue"
        info["backends"].append("sage_queue")
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


class QueueWrapper:
    """包装标准队列以提供SageQueue兼容接口"""
    
    def __init__(self, queue_instance):
        self._queue = queue_instance
        self._lock = threading.Lock()
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """添加元素到队列"""
        self._queue.put(item, block=block, timeout=timeout)
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞添加元素"""
        try:
            self._queue.put_nowait(item)
        except AttributeError:
            # Ray Queue可能没有put_nowait方法，使用put with timeout=0
            try:
                self._queue.put(item, block=False)
            except:
                # 如果还是失败，用put with very short timeout
                self._queue.put(item, timeout=0.001)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列获取元素"""
        return self._queue.get(block=block, timeout=timeout)
    
    def get_nowait(self) -> Any:
        """非阻塞获取元素"""
        try:
            return self._queue.get_nowait()
        except AttributeError:
            # Ray Queue可能没有get_nowait方法，使用get with timeout=0
            try:
                return self._queue.get(block=False)
            except:
                # 如果还是失败，用get with very short timeout
                return self._queue.get(timeout=0.001)
    
    def qsize(self) -> int:
        """返回队列大小"""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._queue.empty()
    
    def full(self) -> bool:
        """检查队列是否满"""
        return self._queue.full()
    
    def get_stats(self) -> dict:
        """返回队列统计信息（兼容性方法）"""
        return {
            'size': self.qsize(),
            'empty': self.empty(),
            'full': self.full()
        }
    
    def close(self) -> None:
        """关闭队列（兼容性方法）"""
        pass


def get_recommended_queue_backend() -> str:
    """
    Get the recommended queue backend based on availability and performance.
    
    Returns:
        String name of recommended backend
    """
    # Use new auto-fallback system if available
    if AUTO_FALLBACK_AVAILABLE:
        return get_optimal_queue_backend()
    
    # Fallback to original logic
    info = get_queue_backend_info()
    
    # Check if we're in a distributed environment (Ray)
    try:
        import ray
        if ray.is_initialized():
            # In Ray environment, prefer Ray queue for distributed support
            if "ray_queue" in info["backends"]:
                return "ray_queue"
            # Fallback to python_queue if Ray queue not available
            return "python_queue"
    except ImportError:
        pass
    
    # For local/non-distributed environments
    if info["sage_available"] and info.get("extension_status") == "working":
        return "sage_queue"
    elif "ray_queue" in info["backends"]:
        return "ray_queue" 
    else:
        return "python_queue"


def create_queue(backend: Optional[str] = None, **kwargs):
    """
    Create a queue using the specified or recommended backend.
    
    Args:
        backend: Backend to use ('sage_queue', 'sage', 'ray_queue', 'ray', 'python_queue', 'auto')   
    Returns:
        Queue instance
    """
    if backend is None or backend == "auto":
        backend = get_recommended_queue_backend()
    
    # Map legacy/short names to full backend names
    backend_mapping = {
        'sage': 'sage_queue',
        'ray': 'ray_queue', 
        'python': 'python_queue'
    }
    backend = backend_mapping.get(backend, backend)
    
    logger.debug(f"Creating queue with backend: {backend}, kwargs: {kwargs}")
    
    if backend == "sage_queue":
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            # Check if SAGE queue supports distributed (it doesn't currently)
            try:
                import ray
                if ray.is_initialized():
                    logger.warning("SAGE queue doesn't support distributed environments, falling back to Ray queue")
                    # Fallback to Ray queue in distributed environment
                    return create_queue(backend="ray_queue", **kwargs)
            except ImportError:
                pass
            
            return SageQueue(**kwargs)
        except ImportError as e:
            logger.warning(f"SAGE queue not available ({e}), falling back to Ray queue")
            # Fallback to Ray queue if SAGE queue not available
            return create_queue(backend="ray_queue", **kwargs)
        except Exception as e:
            logger.error(f"Error creating SAGE queue ({e}), falling back to Ray queue")
            return create_queue(backend="ray_queue", **kwargs)
    
    elif backend == "ray_queue":
        try:
            # Ensure Ray is initialized before creating Ray queue
            import ray
            if not ray.is_initialized():
                try:
                    # Initialize Ray with better configurations
                    ray.init(
                        ignore_reinit_error=True,
                        object_store_memory=1000000000,  # 1GB for object store
                        num_cpus=None,  # Use all available CPUs
                        log_to_driver=False,  # Reduce log verbosity
                        local_mode=False  # Use cluster mode for better performance
                    )
                    logger.info("Initialized Ray for queue creation with optimized settings")
                except Exception as e:
                    logger.warning(f"Failed to initialize Ray ({e}), falling back to Python queue")
                    return create_queue(backend="python_queue", **kwargs)
            
            from ray.util.queue import Queue as RayQueue
            # Filter kwargs that ray queue doesn't support
            ray_kwargs = {k: v for k, v in kwargs.items() if k in ['maxsize']}
            ray_queue = RayQueue(**ray_kwargs)
            return QueueWrapper(ray_queue)
        except ImportError as e:
            logger.warning(f"Ray not available ({e}), falling back to Python queue")
            # Fallback to Python queue if Ray not available
            return create_queue(backend="python_queue", **kwargs)
        except Exception as e:
            logger.error(f"Error creating Ray queue ({e}), falling back to Python queue")
            return create_queue(backend="python_queue", **kwargs)
    
    elif backend == "python_queue":
        import queue
        # Filter kwargs that python queue doesn't support
        queue_kwargs = {k: v for k, v in kwargs.items() if k in ['maxsize']}
        python_queue = queue.Queue(**queue_kwargs)
        return QueueWrapper(python_queue)
    
    else:
        raise ValueError(f"Unknown backend: {backend}")


def get_queue_backends() -> List[str]:
    """Get list of available queue backends."""
    info = get_queue_backend_info()
    return info["backends"]


def is_sage_queue_available() -> bool:
    """Check if SAGE queue extension is available and working."""
    info = get_queue_backend_info()
    return info["sage_available"] and info.get("extension_status") == "working"
