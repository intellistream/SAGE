"""
Environment Detection Utilities

System-level environment detection and configuration utilities.
Legacy runtime support has been removed. Runtime recommendations are based on local,
container/orchestrated, and distributed Flownet-style execution targets.
"""

import importlib
import os
import subprocess
import sys
from typing import Any


def detect_execution_environment() -> str:
    """
    检测当前执行环境类型

    Returns:
        str: 环境类型 ('local', 'kubernetes', 'docker', 'slurm')
    """
    if is_kubernetes_environment():
        return "kubernetes"

    if is_docker_environment():
        return "docker"

    if is_slurm_environment():
        return "slurm"

    return "local"


def get_runtime_engine_info() -> dict[str, Any]:
    """
    获取当前运行时引擎信息

    Returns:
        Dict: 运行时引擎信息
    """
    return {
        "engine": "flownet",
        "engine_version": "unknown",
        "initialized": True,
    }


def is_kubernetes_environment() -> bool:
    """
    检查是否在Kubernetes环境中运行

    Returns:
        bool: 是否在Kubernetes中
    """
    k8s_indicators = [
        "KUBERNETES_SERVICE_HOST",
        "KUBERNETES_SERVICE_PORT",
        "KUBERNETES_PORT",
    ]

    for indicator in k8s_indicators:
        if os.environ.get(indicator):
            return True

    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
        return True

    return False


def is_docker_environment() -> bool:
    """
    检查是否在Docker容器中运行

    Returns:
        bool: 是否在Docker中
    """
    if os.path.exists("/.dockerenv"):
        return True

    try:
        with open("/proc/1/cgroup") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except FileNotFoundError:
        pass

    return False


def is_slurm_environment() -> bool:
    """
    检查是否在SLURM环境中运行

    Returns:
        bool: 是否在SLURM中
    """
    slurm_indicators = [
        "SLURM_JOB_ID",
        "SLURM_PROCID",
        "SLURM_NODEID",
        "SLURM_CLUSTER_NAME",
    ]

    return any(os.environ.get(indicator) for indicator in slurm_indicators)


def get_system_resources() -> dict[str, Any]:
    """
    获取系统资源信息

    Returns:
        Dict: 系统资源信息
    """
    try:
        psutil = importlib.import_module("psutil")

        cpu_info = {
            "count": psutil.cpu_count(),
            "physical_count": psutil.cpu_count(logical=False),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "percent": psutil.cpu_percent(interval=1),
        }

        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free,
        }

        disk = psutil.disk_usage("/")
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": (disk.used / disk.total) * 100,
        }

        return {
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "platform": sys.platform,
        }

    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": f"Error getting system resources: {e}"}


def detect_gpu_resources() -> dict[str, Any]:
    """
    检测GPU资源

    Returns:
        Dict: GPU资源信息
    """
    gpu_info = {"available": False, "count": 0, "devices": []}

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            gpu_info["available"] = True
            lines = result.stdout.strip().split("\n")
            gpu_info["count"] = len(lines)

            for i, line in enumerate(lines):
                parts = line.split(", ")
                if len(parts) >= 3:
                    gpu_info["devices"].append(
                        {
                            "id": i,
                            "name": parts[0].strip(),
                            "memory_total": int(parts[1].strip()),
                            "memory_used": int(parts[2].strip()),
                        }
                    )
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    if not gpu_info["available"]:
        try:
            result = subprocess.run(["rocm-smi"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                gpu_info["available"] = True
                gpu_info["type"] = "AMD"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    return gpu_info


def get_network_interfaces() -> list[dict[str, Any]]:
    """
    获取网络接口信息

    Returns:
        List[Dict]: 网络接口列表
    """
    try:
        psutil = importlib.import_module("psutil")

        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {"name": interface, "addresses": []}

            for addr in addrs:
                addr_info = {
                    "family": (
                        addr.family.name if hasattr(addr.family, "name") else str(addr.family)
                    ),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                }
                interface_info["addresses"].append(addr_info)

            interfaces.append(interface_info)

        return interfaces

    except ImportError:
        return []
    except Exception as e:
        return [{"error": f"Error getting network interfaces: {e}"}]


def recommend_backend() -> dict[str, Any]:
    """
    根据环境推荐最佳后端配置

    Returns:
        Dict: 推荐的后端配置
    """
    env_type = detect_execution_environment()
    system_resources = get_system_resources()
    gpu_resources = detect_gpu_resources()

    recommendation = {
        "environment": env_type,
        "primary_backend": "flownet",
        "secondary_backends": ["local"],
        "communication_layer": "rpc_queue",
        "reasoning": ["Flownet runtime is the default distributed execution backend."],
    }

    if env_type == "kubernetes":
        recommendation["communication_layer"] = "network"
        recommendation["reasoning"].append(
            "Kubernetes environment detected, network transport preferred."
        )

    elif env_type == "docker":
        recommendation["reasoning"].append("Docker environment detected.")

    if gpu_resources.get("available", False):
        recommendation["gpu_support"] = True
        recommendation["communication_layer"] = "gpu_direct"
        recommendation["reasoning"].append("GPU available, GPU-direct communication recommended")

    memory_gb = system_resources.get("memory", {}).get("total", 0) / (1024**3)
    if memory_gb > 32:
        recommendation["memory_strategy"] = "mmap"
        recommendation["reasoning"].append("High memory available, mmap shared memory recommended")
    elif memory_gb < 8:
        recommendation["memory_strategy"] = "conservative"
        recommendation["reasoning"].append("Limited memory, conservative memory usage recommended")

    return recommendation


def get_environment_capabilities() -> dict[str, Any]:
    """
    获取当前环境的完整能力评估

    Returns:
        Dict: 环境能力信息
    """
    return {
        "environment_type": detect_execution_environment(),
        "system_resources": get_system_resources(),
        "gpu_resources": detect_gpu_resources(),
        "network_interfaces": get_network_interfaces(),
        "runtime_engine": get_runtime_engine_info(),
        "backend_recommendation": recommend_backend(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
    }


def validate_environment_for_backend(backend_type: str) -> dict[str, Any]:
    """
    验证环境是否支持指定的后端类型

    Args:
        backend_type: 后端类型 ('local', 'flownet', 'distributed')

    Returns:
        Dict: 验证结果
    """
    validation = {
        "backend": backend_type,
        "supported": False,
        "issues": [],
        "recommendations": [],
    }

    if backend_type == "local":
        validation["supported"] = True

    elif backend_type in {"flownet", "distributed"}:
        network_info = get_network_interfaces()
        if not network_info:
            validation["issues"].append("No network interfaces detected")
        validation["supported"] = len(validation["issues"]) == 0
        if validation["supported"]:
            validation["recommendations"].append(
                "Use RPC queue descriptors and node runtime management for distributed execution."
            )

    return validation
