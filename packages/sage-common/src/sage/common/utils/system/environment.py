"""
Environment Detection Utilities

System-level environment detection and configuration utilities.
These functions help determine the appropriate backend, environment type,
and system capabilities for SAGE applications.
"""

import os
import sys
import socket
import importlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple


def detect_execution_environment() -> str:
    """
    检测当前执行环境类型
    
    Returns:
        str: 环境类型 ('local', 'ray', 'kubernetes', 'docker', 'slurm')
    """
    # 检查Ray环境
    if is_ray_available() and is_ray_cluster_active():
        return 'ray'
    
    # 检查Kubernetes环境
    if is_kubernetes_environment():
        return 'kubernetes'
    
    # 检查Docker环境
    if is_docker_environment():
        return 'docker'
    
    # 检查SLURM环境
    if is_slurm_environment():
        return 'slurm'
    
    # 默认为本地环境
    return 'local'


def is_ray_available() -> bool:
    """
    检查Ray是否可用
    
    Returns:
        bool: Ray是否可用
    """
    try:
        importlib.import_module('ray')
        return True
    except ImportError:
        return False


def is_ray_cluster_active() -> bool:
    """
    检查Ray集群是否处于活跃状态
    
    Returns:
        bool: Ray集群是否活跃
    """
    if not is_ray_available():
        return False
    
    try:
        ray = importlib.import_module('ray')
        return ray.is_initialized()
    except Exception:
        return False


def get_ray_cluster_info() -> Dict[str, Any]:
    """
    获取Ray集群信息
    
    Returns:
        Dict: Ray集群信息
    """
    if not is_ray_available():
        return {"available": False, "error": "Ray not installed"}
    
    try:
        ray = importlib.import_module('ray')
        
        if not ray.is_initialized():
            return {"available": True, "initialized": False}
        
        cluster_resources = ray.cluster_resources()
        nodes = ray.nodes()
        
        return {
            "available": True,
            "initialized": True,
            "cluster_resources": cluster_resources,
            "node_count": len(nodes),
            "nodes": nodes
        }
    except Exception as e:
        return {"available": True, "error": f"Error getting Ray info: {e}"}


def is_kubernetes_environment() -> bool:
    """
    检查是否在Kubernetes环境中运行
    
    Returns:
        bool: 是否在Kubernetes中
    """
    # 检查环境变量
    k8s_indicators = [
        'KUBERNETES_SERVICE_HOST',
        'KUBERNETES_SERVICE_PORT',
        'KUBERNETES_PORT'
    ]
    
    for indicator in k8s_indicators:
        if os.environ.get(indicator):
            return True
    
    # 检查服务账户文件
    if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
        return True
    
    return False


def is_docker_environment() -> bool:
    """
    检查是否在Docker容器中运行
    
    Returns:
        bool: 是否在Docker中
    """
    # 检查.dockerenv文件
    if os.path.exists('/.dockerenv'):
        return True
    
    # 检查cgroup信息
    try:
        with open('/proc/1/cgroup', 'r') as f:
            content = f.read()
            if 'docker' in content or 'containerd' in content:
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
        'SLURM_JOB_ID',
        'SLURM_PROCID',
        'SLURM_NODEID',
        'SLURM_CLUSTER_NAME'
    ]
    
    return any(os.environ.get(indicator) for indicator in slurm_indicators)


def get_system_resources() -> Dict[str, Any]:
    """
    获取系统资源信息
    
    Returns:
        Dict: 系统资源信息
    """
    try:
        psutil = importlib.import_module('psutil')
        
        # CPU信息
        cpu_info = {
            "count": psutil.cpu_count(),
            "physical_count": psutil.cpu_count(logical=False),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "percent": psutil.cpu_percent(interval=1)
        }
        
        # 内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": (disk.used / disk.total) * 100
        }
        
        return {
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "platform": sys.platform
        }
        
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": f"Error getting system resources: {e}"}


def detect_gpu_resources() -> Dict[str, Any]:
    """
    检测GPU资源
    
    Returns:
        Dict: GPU资源信息
    """
    gpu_info = {
        "available": False,
        "count": 0,
        "devices": []
    }
    
    # 检查NVIDIA GPU
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            gpu_info["available"] = True
            lines = result.stdout.strip().split('\n')
            gpu_info["count"] = len(lines)
            
            for i, line in enumerate(lines):
                parts = line.split(', ')
                if len(parts) >= 3:
                    gpu_info["devices"].append({
                        "id": i,
                        "name": parts[0].strip(),
                        "memory_total": int(parts[1].strip()),
                        "memory_used": int(parts[2].strip())
                    })
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    
    # 检查AMD GPU (rocm-smi)
    if not gpu_info["available"]:
        try:
            result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                gpu_info["available"] = True
                gpu_info["type"] = "AMD"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    return gpu_info


def get_network_interfaces() -> List[Dict[str, Any]]:
    """
    获取网络接口信息
    
    Returns:
        List[Dict]: 网络接口列表
    """
    try:
        psutil = importlib.import_module('psutil')
        
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {
                "name": interface,
                "addresses": []
            }
            
            for addr in addrs:
                addr_info = {
                    "family": addr.family.name if hasattr(addr.family, 'name') else str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                }
                interface_info["addresses"].append(addr_info)
            
            interfaces.append(interface_info)
        
        return interfaces
        
    except ImportError:
        return []
    except Exception as e:
        return [{"error": f"Error getting network interfaces: {e}"}]


def recommend_backend() -> Dict[str, Any]:
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
        "primary_backend": "local",
        "secondary_backends": [],
        "communication_layer": "memory",
        "reasoning": []
    }
    
    # 基于环境类型的推荐
    if env_type == "ray":
        recommendation["primary_backend"] = "ray"
        recommendation["communication_layer"] = "ray_queue"
        recommendation["reasoning"].append("Ray cluster detected, using distributed backend")
    
    elif env_type == "kubernetes":
        recommendation["primary_backend"] = "ray"
        recommendation["secondary_backends"].append("local")
        recommendation["communication_layer"] = "network"
        recommendation["reasoning"].append("Kubernetes environment, Ray recommended for scalability")
    
    elif env_type == "docker":
        recommendation["secondary_backends"].append("ray")
        recommendation["reasoning"].append("Docker environment, local backend preferred")
    
    # 基于资源的推荐
    if system_resources.get("cpu", {}).get("count", 0) > 8:
        if "ray" not in recommendation["secondary_backends"]:
            recommendation["secondary_backends"].append("ray")
        recommendation["reasoning"].append("High CPU count, Ray backend beneficial for parallelization")
    
    if gpu_resources.get("available", False):
        recommendation["gpu_support"] = True
        recommendation["communication_layer"] = "gpu_direct"
        recommendation["reasoning"].append("GPU available, GPU-direct communication recommended")
    
    # 内存建议
    memory_gb = system_resources.get("memory", {}).get("total", 0) / (1024**3)
    if memory_gb > 32:
        recommendation["memory_strategy"] = "mmap"
        recommendation["reasoning"].append("High memory available, mmap shared memory recommended")
    elif memory_gb < 8:
        recommendation["memory_strategy"] = "conservative"
        recommendation["reasoning"].append("Limited memory, conservative memory usage recommended")
    
    return recommendation


def get_environment_capabilities() -> Dict[str, Any]:
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
        "ray_info": get_ray_cluster_info(),
        "backend_recommendation": recommend_backend(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform
    }


def validate_environment_for_backend(backend_type: str) -> Dict[str, Any]:
    """
    验证环境是否支持指定的后端类型
    
    Args:
        backend_type: 后端类型 ('local', 'ray', 'distributed')
        
    Returns:
        Dict: 验证结果
    """
    validation = {
        "backend": backend_type,
        "supported": False,
        "issues": [],
        "recommendations": []
    }
    
    if backend_type == "local":
        validation["supported"] = True
        
    elif backend_type == "ray":
        if not is_ray_available():
            validation["issues"].append("Ray not installed")
            validation["recommendations"].append("Install Ray: pip install ray")
        else:
            validation["supported"] = True
            if not is_ray_cluster_active():
                validation["recommendations"].append("Initialize Ray cluster for better performance")
                
    elif backend_type == "distributed":
        if not is_ray_available():
            validation["issues"].append("Ray required for distributed backend")
            validation["recommendations"].append("Install Ray: pip install ray")
        
        network_info = get_network_interfaces()
        if not network_info or len(network_info) < 2:
            validation["issues"].append("Limited network interfaces for distributed setup")
            
        if validation["issues"]:
            validation["supported"] = False
        else:
            validation["supported"] = True
    
    return validation
