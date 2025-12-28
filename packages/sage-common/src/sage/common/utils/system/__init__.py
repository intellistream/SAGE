"""
SAGE System Utilities

Network and process management utilities for SAGE applications.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.common._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Network utilities
from sage.common.utils.system.network import (
    aggressive_port_cleanup,
    allocate_free_port,
    check_port_binding_permission,
    check_tcp_connection,
    find_port_processes,
    get_host_ip,
    get_process_on_port,
    is_port_available,
    is_port_occupied,
    send_tcp_health_check,
    wait_for_port_ready,
    wait_for_port_release,
)

# Process utilities
from sage.common.utils.system.process import (
    find_processes_by_name,
    get_process_info,
    kill_process_with_sudo,
    terminate_process,
    terminate_process_tree,
    terminate_processes_by_name,
)

__all__ = [
    # Network
    "is_port_occupied",
    "is_port_available",
    "check_port_binding_permission",
    "wait_for_port_release",
    "wait_for_port_ready",
    "find_port_processes",
    "get_process_on_port",
    "send_tcp_health_check",
    "allocate_free_port",
    "aggressive_port_cleanup",
    "get_host_ip",
    "check_tcp_connection",
    # Process
    "terminate_process",
    "terminate_processes_by_name",
    "kill_process_with_sudo",
    "terminate_process_tree",
    "get_process_info",
    "find_processes_by_name",
]
