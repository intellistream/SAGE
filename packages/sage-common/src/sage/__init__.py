"""SAGE namespace package."""

# Suppress PyTorch distributed warnings in WSL/containerized environments
# Must be set BEFORE any torch/vllm imports
import os as _os

_os.environ.setdefault("GLOO_SOCKET_IFNAME", "lo")
_os.environ.setdefault("NCCL_SOCKET_IFNAME", "lo")
_os.environ.setdefault("TORCH_DISTRIBUTED_DEBUG", "OFF")
# Suppress C++ level warnings (including c10d socket warnings)
_os.environ.setdefault("TORCH_CPP_LOG_LEVEL", "ERROR")
_os.environ.setdefault("NCCL_DEBUG", "WARN")

# This is a namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
