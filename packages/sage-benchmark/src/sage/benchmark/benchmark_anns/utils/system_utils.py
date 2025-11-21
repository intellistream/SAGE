"""
CPU affinity and system utilities
"""
import os


def bind_to_core(core_id):
    """
    Bind the current process to a specific CPU core.
    
    Args:
        core_id: The ID of the core to bind to. Use -1 for default OS scheduling.
    
    Returns:
        The core ID the process is bound to, or -1 if OS scheduling is used.
    """
    if core_id == -1:  # OS scheduling
        return -1
    
    max_cpus = os.cpu_count()
    if max_cpus is None:
        raise RuntimeError("Could not determine the number of CPUs.")
    
    cpu_id = core_id % max_cpus
    
    try:
        pid = os.getpid()
        os.sched_setaffinity(pid, {cpu_id})  # Set CPU affinity
        return cpu_id
    except AttributeError:
        # sched_setaffinity not available (e.g., macOS)
        print(f"Warning: CPU affinity not supported on this system")
        return -1
    except Exception as e:
        print(f"Error setting CPU affinity: {e}")
        return -1
