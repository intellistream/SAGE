"""
System Utilities Package

Provides system-level utility functions for SAGE framework.
These utilities handle network, process, and environment operations
independently of business logic classes.
"""

from .network_utils import (
    is_port_occupied,
    wait_for_port_release,
    find_port_processes,
    aggressive_port_cleanup,
    check_port_binding_permission,
    send_tcp_health_check,
    allocate_free_port,
    get_host_ip,
    test_tcp_connection
)

from .process_utils import (
    find_processes_by_name,
    get_process_info,
    terminate_process,
    terminate_processes_by_name,
    kill_process_with_sudo,
    verify_sudo_password,
    get_process_children,
    terminate_process_tree,
    wait_for_process_termination,
    get_system_process_summary,
    is_process_running,
    SudoManager,
    create_sudo_manager,
    check_process_ownership
)

from .environment_utils import (
    detect_execution_environment,
    is_ray_available,
    is_ray_cluster_active,
    get_ray_cluster_info,
    is_kubernetes_environment,
    is_docker_environment,
    is_slurm_environment,
    get_system_resources,
    detect_gpu_resources,
    get_network_interfaces,
    recommend_backend,
    get_environment_capabilities,
    validate_environment_for_backend
)

__all__ = [
    # Network utilities
    'is_port_occupied',
    'wait_for_port_release',
    'find_port_processes',
    'aggressive_port_cleanup',
    'check_port_binding_permission',
    'send_tcp_health_check',
    'allocate_free_port',
    'get_host_ip',
    'test_tcp_connection',
    
    # Process utilities
    'find_processes_by_name',
    'get_process_info',
    'terminate_process',
    'terminate_processes_by_name',
    'kill_process_with_sudo',
    'verify_sudo_password',
    'get_process_children',
    'terminate_process_tree',
    'wait_for_process_termination',
    'get_system_process_summary',
    'is_process_running',
    'SudoManager',
    'create_sudo_manager',
    'check_process_ownership',
    
    # Environment utilities
    'detect_execution_environment',
    'is_ray_available',
    'is_ray_cluster_active',
    'get_ray_cluster_info',
    'is_kubernetes_environment',
    'is_docker_environment',
    'is_slurm_environment',
    'get_system_resources',
    'detect_gpu_resources',
    'get_network_interfaces',
    'recommend_backend',
    'get_environment_capabilities',
    'validate_environment_for_backend'
]
