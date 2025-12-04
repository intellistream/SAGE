"""
SAGE Common Config

Configuration management utilities.
"""

from .network import (
    HF_MIRROR_CN,
    NetworkRegion,
    configure_hf_mirror,
    detect_china_mainland,
    ensure_hf_mirror_configured,
    get_hf_endpoint,
    get_network_region,
)
from .output_paths import (
    SageOutputPaths,
    find_sage_project_root,
    get_benchmarks_dir,
    get_cache_dir,
    get_coverage_dir,
    get_log_file,
    get_logs_dir,
    get_output_dir,
    get_output_file,
    get_ray_temp_dir,
    get_reports_dir,
    get_sage_paths,
    get_states_dir,
    get_states_file,
    get_temp_dir,
    get_test_context_dir,
    get_test_env_dir,
    get_test_temp_dir,
    initialize_sage_paths,
    migrate_existing_outputs,
    setup_sage_environment,
)
from .ports import (
    DEFAULT_BENCHMARK_LLM_PORT,
    DEFAULT_EMBEDDING_PORT,
    DEFAULT_LLM_PORT,
    SagePorts,
)
from .user_paths import (
    SageUserPaths,
    get_user_cache_dir,
    get_user_config_dir,
    get_user_data_dir,
    get_user_paths,
    get_user_state_dir,
)

__all__ = [
    # Output paths
    "SageOutputPaths",
    "find_sage_project_root",
    "get_benchmarks_dir",
    "get_cache_dir",
    "get_coverage_dir",
    "get_log_file",
    "get_logs_dir",
    "get_output_dir",
    "get_output_file",
    "get_ray_temp_dir",
    "get_reports_dir",
    "get_sage_paths",
    "get_states_dir",
    "get_states_file",
    "get_temp_dir",
    "get_test_context_dir",
    "get_test_env_dir",
    "get_test_temp_dir",
    "initialize_sage_paths",
    "migrate_existing_outputs",
    "setup_sage_environment",
    # Ports
    "SagePorts",
    "DEFAULT_LLM_PORT",
    "DEFAULT_EMBEDDING_PORT",
    "DEFAULT_BENCHMARK_LLM_PORT",
    # Network detection and HuggingFace mirror
    "HF_MIRROR_CN",
    "detect_china_mainland",
    "get_hf_endpoint",
    "configure_hf_mirror",
    "ensure_hf_mirror_configured",
    "get_network_region",
    "NetworkRegion",
    # User paths (XDG standard)
    "SageUserPaths",
    "get_user_paths",
    "get_user_config_dir",
    "get_user_data_dir",
    "get_user_state_dir",
    "get_user_cache_dir",
]
