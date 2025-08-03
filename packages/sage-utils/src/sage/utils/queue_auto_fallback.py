"""
Queue Auto-Fallback System

Intelligent queue backend selection with automatic fallback based on:
1. Environment (local vs distributed)
2. Backend availability 
3. Performance requirements
4. Error handling
"""

import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from sage.utils.system.environment_utils import detect_execution_environment, is_ray_available

logger = logging.getLogger(__name__)

class QueueBackendType(Enum):
    """Queue backend types in priority order"""
    SAGE_QUEUE = "sage_queue"       # High performance, local only
    RAY_QUEUE = "ray_queue"         # Distributed support
    PYTHON_QUEUE = "python_queue"   # Basic fallback

@dataclass
class BackendCapabilities:
    """Capabilities of a queue backend"""
    supports_distributed: bool = False
    supports_multiprocess: bool = False
    high_performance: bool = False
    memory_mapped: bool = False
    requires_ray: bool = False
    requires_extension: bool = False

class QueueBackendSelector:
    """Intelligent queue backend selector with fallback support"""
    
    def __init__(self):
        self.backend_capabilities = {
            QueueBackendType.SAGE_QUEUE: BackendCapabilities(
                supports_distributed=False,  # SAGE queue doesn't support distributed
                supports_multiprocess=True,
                high_performance=True,
                memory_mapped=True,
                requires_extension=True
            ),
            QueueBackendType.RAY_QUEUE: BackendCapabilities(
                supports_distributed=True,
                supports_multiprocess=True,
                high_performance=True,
                requires_ray=True
            ),
            QueueBackendType.PYTHON_QUEUE: BackendCapabilities(
                supports_distributed=False,
                supports_multiprocess=False,
                high_performance=False
            )
        }
        
        self._cached_availability = {}
    
    def check_backend_availability(self, backend: QueueBackendType) -> Dict[str, Any]:
        """Check if a backend is available and working"""
        if backend in self._cached_availability:
            return self._cached_availability[backend]
        
        result = {
            "available": False,
            "working": False,
            "error": None,
            "capabilities": self.backend_capabilities[backend]
        }
        
        try:
            if backend == QueueBackendType.SAGE_QUEUE:
                result.update(self._check_sage_queue())
            elif backend == QueueBackendType.RAY_QUEUE:
                result.update(self._check_ray_queue())
            elif backend == QueueBackendType.PYTHON_QUEUE:
                result.update(self._check_python_queue())
                
        except Exception as e:
            result["error"] = str(e)
            logger.debug(f"Error checking {backend.value}: {e}")
        
        self._cached_availability[backend] = result
        return result
    
    def _check_sage_queue(self) -> Dict[str, Any]:
        """Check SAGE queue availability"""
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            
            # Try to create a test queue
            test_queue = SageQueue(name="test_availability", maxsize=10)
            test_queue.put("test")
            test_queue.get()
            test_queue.close()
            
            return {"available": True, "working": True}
        except ImportError as e:
            return {"available": False, "working": False, "error": f"Import error: {e}"}
        except Exception as e:
            return {"available": True, "working": False, "error": f"Runtime error: {e}"}
    
    def _check_ray_queue(self) -> Dict[str, Any]:
        """Check Ray queue availability"""
        try:
            import ray
            from ray.util.queue import Queue as RayQueue
            
            # Initialize Ray if not already done
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True)
            
            # Try to create a test queue
            test_queue = RayQueue(maxsize=10)
            test_queue.put("test")
            test_queue.get()
            
            return {"available": True, "working": True}
        except ImportError as e:
            return {"available": False, "working": False, "error": f"Import error: {e}"}
        except Exception as e:
            return {"available": True, "working": False, "error": f"Runtime error: {e}"}
    
    def _check_python_queue(self) -> Dict[str, Any]:
        """Check Python queue availability (always available)"""
        try:
            import queue
            test_queue = queue.Queue(maxsize=10)
            test_queue.put("test")
            test_queue.get()
            return {"available": True, "working": True}
        except Exception as e:
            return {"available": False, "working": False, "error": str(e)}
    
    def select_optimal_backend(self, requirements: Optional[Dict[str, bool]] = None) -> QueueBackendType:
        """
        Select the optimal queue backend based on requirements and availability
        
        Args:
            requirements: Dict of requirements like {'distributed': True, 'high_performance': True}
        
        Returns:
            The best available backend type
        """
        if requirements is None:
            requirements = {}
        
        # Determine if we need distributed support
        env_type = detect_execution_environment()
        needs_distributed = requirements.get('distributed', env_type in ['ray', 'kubernetes', 'slurm'])
        needs_high_performance = requirements.get('high_performance', True)
        
        # Priority order for selection
        if needs_distributed:
            # In distributed environment, Ray queue is preferred
            priority_order = [QueueBackendType.RAY_QUEUE, QueueBackendType.PYTHON_QUEUE]
        else:
            # In local environment, SAGE queue is preferred if available
            priority_order = [QueueBackendType.SAGE_QUEUE, QueueBackendType.RAY_QUEUE, QueueBackendType.PYTHON_QUEUE]
        
        # Select first available and working backend
        for backend in priority_order:
            availability = self.check_backend_availability(backend)
            capabilities = availability["capabilities"]
            
            # Check if backend meets requirements
            if needs_distributed and not capabilities.supports_distributed:
                continue
            if needs_high_performance and not capabilities.high_performance:
                # Allow fallback for high performance requirement
                pass
            
            if availability["available"] and availability["working"]:
                logger.info(f"Selected queue backend: {backend.value}")
                return backend
        
        # Fallback to Python queue as last resort
        logger.warning("No optimal backend found, falling back to python_queue")
        return QueueBackendType.PYTHON_QUEUE
    
    def get_fallback_chain(self, preferred_backend: QueueBackendType) -> List[QueueBackendType]:
        """Get the fallback chain for a preferred backend"""
        env_type = detect_execution_environment()
        is_distributed = env_type in ['ray', 'kubernetes', 'slurm']
        
        if preferred_backend == QueueBackendType.SAGE_QUEUE:
            if is_distributed:
                return [QueueBackendType.RAY_QUEUE, QueueBackendType.PYTHON_QUEUE]
            else:
                return [QueueBackendType.RAY_QUEUE, QueueBackendType.PYTHON_QUEUE]
        elif preferred_backend == QueueBackendType.RAY_QUEUE:
            if is_distributed:
                return [QueueBackendType.PYTHON_QUEUE]
            else:
                return [QueueBackendType.SAGE_QUEUE, QueueBackendType.PYTHON_QUEUE]
        else:
            return []  # Python queue has no fallbacks
    
    def clear_cache(self):
        """Clear availability cache"""
        self._cached_availability.clear()

# Global instance
_backend_selector = QueueBackendSelector()

def get_optimal_queue_backend(requirements: Optional[Dict[str, bool]] = None) -> str:
    """Get the optimal queue backend name"""
    backend = _backend_selector.select_optimal_backend(requirements)
    return backend.value

def get_queue_backend_info_detailed() -> Dict[str, Any]:
    """Get detailed information about all queue backends"""
    env_type = detect_execution_environment()
    info = {
        "environment": {
            "type": env_type,
            "distributed": env_type in ['ray', 'kubernetes', 'slurm'],
            "ray_available": is_ray_available(),
            "sage_extension_available": False
        },
        "backends": {},
        "recommended": None
    }
    
    for backend_type in QueueBackendType:
        availability = _backend_selector.check_backend_availability(backend_type)
        info["backends"][backend_type.value] = availability
        
        # Update environment info
        if backend_type == QueueBackendType.RAY_QUEUE and availability["available"]:
            info["environment"]["ray_available"] = True
        if backend_type == QueueBackendType.SAGE_QUEUE and availability["available"]:
            info["environment"]["sage_extension_available"] = True
    
    # Get recommended backend
    recommended = _backend_selector.select_optimal_backend()
    info["recommended"] = recommended.value
    
    return info
