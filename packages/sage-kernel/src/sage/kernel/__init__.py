"""
SAGE Kernel Module

Core kernel functionality for SAGE streaming system.
"""
__version__ = "0.1.3"

# Import core interfaces
from sage.kernel.jobmanager.jobmanager_client import JobManagerClient
from sage.kernel.jobmanager.job_manager import JobManager
from sage.kernel.runtime.context.service_context import ServiceContext
from sage.kernel.runtime.context.task_context import TaskContext

# Expose public API
__all__ = [
    "JobManagerClient",
    "JobManager", 
    "ServiceContext",
    "TaskContext",
]
