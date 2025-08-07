"""
Tests for sage.utils.system.environment module
=============================================

单元测试系统环境检测模块的功能，包括：
- 执行环境检测
- Ray集群信息
- 系统资源检测
- GPU资源检测
- 网络接口信息
- 后端推荐系统
"""

import pytest
import os
import sys
import subprocess
from unittest.mock import patch, MagicMock, mock_open, call

from sage.kernel.utils.system.environment import (
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


@pytest.mark.unit
class TestEnvironmentDetection:
    """环境检测测试"""
    
    @patch('sage.kernel.utils.system.environment.is_ray_cluster_active')
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    @patch('sage.kernel.utils.system.environment.is_kubernetes_environment')
    @patch('sage.kernel.utils.system.environment.is_docker_environment')
    @patch('sage.kernel.utils.system.environment.is_slurm_environment')
    def test_detect_execution_environment_ray(self, mock_slurm, mock_docker, mock_k8s, mock_ray_available, mock_ray_active):
        """测试检测Ray环境"""
        mock_ray_available.return_value = True
        mock_ray_active.return_value = True
        mock_k8s.return_value = False
        mock_docker.return_value = False
        mock_slurm.return_value = False
        
        result = detect_execution_environment()
        assert result == 'ray'
    
    @patch('sage.kernel.utils.system.environment.is_ray_cluster_active')
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    @patch('sage.kernel.utils.system.environment.is_kubernetes_environment')
    @patch('sage.kernel.utils.system.environment.is_docker_environment')
    @patch('sage.kernel.utils.system.environment.is_slurm_environment')
    def test_detect_execution_environment_kubernetes(self, mock_slurm, mock_docker, mock_k8s, mock_ray_available, mock_ray_active):
        """测试检测Kubernetes环境"""
        mock_ray_available.return_value = False
        mock_ray_active.return_value = False
        mock_k8s.return_value = True
        mock_docker.return_value = False
        mock_slurm.return_value = False
        
        result = detect_execution_environment()
        assert result == 'kubernetes'
    
    @patch('sage.kernel.utils.system.environment.is_ray_cluster_active')
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    @patch('sage.kernel.utils.system.environment.is_kubernetes_environment')
    @patch('sage.kernel.utils.system.environment.is_docker_environment')
    @patch('sage.kernel.utils.system.environment.is_slurm_environment')
    def test_detect_execution_environment_docker(self, mock_slurm, mock_docker, mock_k8s, mock_ray_available, mock_ray_active):
        """测试检测Docker环境"""
        mock_ray_available.return_value = False
        mock_ray_active.return_value = False
        mock_k8s.return_value = False
        mock_docker.return_value = True
        mock_slurm.return_value = False
        
        result = detect_execution_environment()
        assert result == 'docker'
    
    @patch('sage.kernel.utils.system.environment.is_ray_cluster_active')
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    @patch('sage.kernel.utils.system.environment.is_kubernetes_environment')
    @patch('sage.kernel.utils.system.environment.is_docker_environment')
    @patch('sage.kernel.utils.system.environment.is_slurm_environment')
    def test_detect_execution_environment_slurm(self, mock_slurm, mock_docker, mock_k8s, mock_ray_available, mock_ray_active):
        """测试检测SLURM环境"""
        mock_ray_available.return_value = False
        mock_ray_active.return_value = False
        mock_k8s.return_value = False
        mock_docker.return_value = False
        mock_slurm.return_value = True
        
        result = detect_execution_environment()
        assert result == 'slurm'
    
    @patch('sage.kernel.utils.system.environment.is_ray_cluster_active')
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    @patch('sage.kernel.utils.system.environment.is_kubernetes_environment')
    @patch('sage.kernel.utils.system.environment.is_docker_environment')
    @patch('sage.kernel.utils.system.environment.is_slurm_environment')
    def test_detect_execution_environment_local(self, mock_slurm, mock_docker, mock_k8s, mock_ray_available, mock_ray_active):
        """测试检测本地环境"""
        mock_ray_available.return_value = False
        mock_ray_active.return_value = False
        mock_k8s.return_value = False
        mock_docker.return_value = False
        mock_slurm.return_value = False
        
        result = detect_execution_environment()
        assert result == 'local'


@pytest.mark.unit
class TestRayDetection:
    """Ray检测测试"""
    
    def test_is_ray_available_true(self):
        """测试Ray可用检测"""
        with patch.dict('sys.modules', {'ray': MagicMock()}):
            result = is_ray_available()
            assert result is True
    
    def test_is_ray_available_false(self):
        """测试Ray不可用检测"""
        with patch('importlib.import_module', side_effect=ImportError("No module named 'ray'")):
            result = is_ray_available()
            assert result is False
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_is_ray_cluster_active_not_available(self, mock_ray_available):
        """测试Ray不可用时的集群状态"""
        mock_ray_available.return_value = False
        
        result = is_ray_cluster_active()
        assert result is False
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_is_ray_cluster_active_true(self, mock_ray_available):
        """测试Ray集群活跃状态"""
        mock_ray_available.return_value = True
        
        with patch('importlib.import_module') as mock_import:
            mock_ray = MagicMock()
            mock_ray.is_initialized.return_value = True
            mock_import.return_value = mock_ray
            
            result = is_ray_cluster_active()
            assert result is True
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_is_ray_cluster_active_false(self, mock_ray_available):
        """测试Ray集群非活跃状态"""
        mock_ray_available.return_value = True
        
        with patch('importlib.import_module') as mock_import:
            mock_ray = MagicMock()
            mock_ray.is_initialized.return_value = False
            mock_import.return_value = mock_ray
            
            result = is_ray_cluster_active()
            assert result is False
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_get_ray_cluster_info_not_available(self, mock_ray_available):
        """测试获取Ray集群信息 - 不可用"""
        mock_ray_available.return_value = False
        
        result = get_ray_cluster_info()
        assert result["available"] is False
        assert "Ray not installed" in result["error"]
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_get_ray_cluster_info_not_initialized(self, mock_ray_available):
        """测试获取Ray集群信息 - 未初始化"""
        mock_ray_available.return_value = True
        
        with patch('importlib.import_module') as mock_import:
            mock_ray = MagicMock()
            mock_ray.is_initialized.return_value = False
            mock_import.return_value = mock_ray
            
            result = get_ray_cluster_info()
            assert result["available"] is True
            assert result["initialized"] is False
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_get_ray_cluster_info_initialized(self, mock_ray_available):
        """测试获取Ray集群信息 - 已初始化"""
        mock_ray_available.return_value = True
        
        with patch('importlib.import_module') as mock_import:
            mock_ray = MagicMock()
            mock_ray.is_initialized.return_value = True
            mock_ray.cluster_resources.return_value = {"CPU": 8, "GPU": 2}
            mock_ray.nodes.return_value = [{"NodeID": "node1"}, {"NodeID": "node2"}]
            mock_import.return_value = mock_ray
            
            result = get_ray_cluster_info()
            assert result["available"] is True
            assert result["initialized"] is True
            assert result["cluster_resources"] == {"CPU": 8, "GPU": 2}
            assert result["node_count"] == 2
            assert len(result["nodes"]) == 2


@pytest.mark.unit
class TestContainerEnvironmentDetection:
    """容器环境检测测试"""
    
    def test_is_kubernetes_environment_service_host(self):
        """测试通过服务主机检测Kubernetes"""
        with patch.dict(os.environ, {'KUBERNETES_SERVICE_HOST': '10.0.0.1'}):
            result = is_kubernetes_environment()
            assert result is True
    
    def test_is_kubernetes_environment_service_port(self):
        """测试通过服务端口检测Kubernetes"""
        with patch.dict(os.environ, {'KUBERNETES_SERVICE_PORT': '443'}):
            result = is_kubernetes_environment()
            assert result is True
    
    def test_is_kubernetes_environment_kubernetes_port(self):
        """测试通过Kubernetes端口检测"""
        with patch.dict(os.environ, {'KUBERNETES_PORT': 'tcp://10.0.0.1:443'}):
            result = is_kubernetes_environment()
            assert result is True
    
    @patch('os.path.exists')
    def test_is_kubernetes_environment_service_account(self, mock_exists):
        """测试通过服务账户文件检测Kubernetes"""
        mock_exists.return_value = True
        
        result = is_kubernetes_environment()
        assert result is True
        mock_exists.assert_called_with('/var/run/secrets/kubernetes.io/serviceaccount')
    
    def test_is_kubernetes_environment_false(self):
        """测试非Kubernetes环境"""
        with patch.dict(os.environ, {}, clear=True), \
             patch('os.path.exists', return_value=False):
            result = is_kubernetes_environment()
            assert result is False
    
    @patch('os.path.exists')
    def test_is_docker_environment_dockerenv(self, mock_exists):
        """测试通过.dockerenv文件检测Docker"""
        mock_exists.side_effect = lambda path: path == '/.dockerenv'
        
        result = is_docker_environment()
        assert result is True
    
    @patch('os.path.exists')
    def test_is_docker_environment_cgroup_docker(self, mock_exists):
        """测试通过cgroup信息检测Docker"""
        mock_exists.side_effect = lambda path: path != '/.dockerenv'
        
        with patch('builtins.open', mock_open(read_data='12:memory:/docker/container_id')):
            result = is_docker_environment()
            assert result is True
    
    @patch('os.path.exists')
    def test_is_docker_environment_cgroup_containerd(self, mock_exists):
        """测试通过cgroup信息检测containerd"""
        mock_exists.side_effect = lambda path: path != '/.dockerenv'
        
        with patch('builtins.open', mock_open(read_data='12:memory:/containerd/container_id')):
            result = is_docker_environment()
            assert result is True
    
    @patch('os.path.exists')
    def test_is_docker_environment_false(self, mock_exists):
        """测试非Docker环境"""
        mock_exists.return_value = False
        
        with patch('builtins.open', side_effect=FileNotFoundError()):
            result = is_docker_environment()
            assert result is False
    
    def test_is_slurm_environment_job_id(self):
        """测试通过作业ID检测SLURM"""
        with patch.dict(os.environ, {'SLURM_JOB_ID': '12345'}):
            result = is_slurm_environment()
            assert result is True
    
    def test_is_slurm_environment_procid(self):
        """测试通过进程ID检测SLURM"""
        with patch.dict(os.environ, {'SLURM_PROCID': '0'}):
            result = is_slurm_environment()
            assert result is True
    
    def test_is_slurm_environment_false(self):
        """测试非SLURM环境"""
        with patch.dict(os.environ, {}, clear=True):
            result = is_slurm_environment()
            assert result is False


@pytest.mark.unit
class TestSystemResources:
    """系统资源检测测试"""
    
    @patch('importlib.import_module')
    def test_get_system_resources_success(self, mock_import):
        """测试成功获取系统资源"""
        mock_psutil = MagicMock()
        
        # 模拟CPU信息
        mock_psutil.cpu_count.side_effect = [8, 4]  # logical, physical
        mock_freq = MagicMock()
        mock_freq._asdict.return_value = {"current": 2400, "min": 800, "max": 3200}
        mock_psutil.cpu_freq.return_value = mock_freq
        mock_psutil.cpu_percent.return_value = 25.5
        
        # 模拟内存信息
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024**3  # 16GB
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_memory.percent = 50.0
        mock_memory.used = 8 * 1024**3
        mock_memory.free = 8 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory
        
        # 模拟磁盘信息
        mock_disk = MagicMock()
        mock_disk.total = 1024**4  # 1TB
        mock_disk.used = 512 * 1024**3  # 512GB
        mock_disk.free = 512 * 1024**3  # 512GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_import.return_value = mock_psutil
        
        result = get_system_resources()
        
        assert result["cpu"]["count"] == 8
        assert result["cpu"]["physical_count"] == 4
        assert result["cpu"]["percent"] == 25.5
        assert result["memory"]["total"] == 16 * 1024**3
        assert result["memory"]["percent"] == 50.0
        assert result["disk"]["total"] == 1024**4
        assert result["platform"] == sys.platform
    
    @patch('importlib.import_module')
    def test_get_system_resources_psutil_not_available(self, mock_import):
        """测试psutil不可用时的处理"""
        mock_import.side_effect = ImportError("No module named 'psutil'")
        
        result = get_system_resources()
        
        assert "error" in result
        assert "psutil not available" in result["error"]
    
    @patch('importlib.import_module')
    def test_get_system_resources_exception(self, mock_import):
        """测试获取系统资源时的异常处理"""
        mock_psutil = MagicMock()
        mock_psutil.cpu_count.side_effect = Exception("CPU error")
        mock_import.return_value = mock_psutil
        
        result = get_system_resources()
        
        assert "error" in result
        assert "Error getting system resources" in result["error"]


@pytest.mark.unit
class TestGPUDetection:
    """GPU检测测试"""
    
    @patch('subprocess.run')
    def test_detect_gpu_resources_nvidia_success(self, mock_run):
        """测试检测NVIDIA GPU成功"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "GeForce RTX 3080, 10240, 2048\nGeForce RTX 3090, 24576, 4096"
        mock_run.return_value = mock_result
        
        result = detect_gpu_resources()
        
        assert result["available"] is True
        assert result["count"] == 2
        assert len(result["devices"]) == 2
        assert result["devices"][0]["name"] == "GeForce RTX 3080"
        assert result["devices"][0]["memory_total"] == 10240
        assert result["devices"][1]["name"] == "GeForce RTX 3090"
        
        mock_run.assert_called_with(
            ['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_detect_gpu_resources_nvidia_not_found(self, mock_run):
        """测试NVIDIA GPU未找到时检测AMD"""
        # 第一次调用nvidia-smi失败
        mock_run.side_effect = [
            subprocess.SubprocessError("nvidia-smi not found"),
            MagicMock(returncode=0, stdout="AMD GPU info")
        ]
        
        result = detect_gpu_resources()
        
        assert result["available"] is True
        assert result["type"] == "AMD"
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_detect_gpu_resources_no_gpu(self, mock_run):
        """测试无GPU时的检测"""
        mock_run.side_effect = [
            subprocess.SubprocessError("nvidia-smi not found"),
            subprocess.SubprocessError("rocm-smi not found")
        ]
        
        result = detect_gpu_resources()
        
        assert result["available"] is False
        assert result["count"] == 0
        assert len(result["devices"]) == 0
    
    @patch('subprocess.run')
    def test_detect_gpu_resources_nvidia_timeout(self, mock_run):
        """测试nvidia-smi超时"""
        mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 10)
        
        result = detect_gpu_resources()
        
        assert result["available"] is False


@pytest.mark.unit
class TestNetworkInterfaces:
    """网络接口测试"""
    
    @patch('importlib.import_module')
    def test_get_network_interfaces_success(self, mock_import):
        """测试成功获取网络接口"""
        mock_psutil = MagicMock()
        
        # 模拟网络接口数据
        mock_addr = MagicMock()
        mock_addr.family.name = "AF_INET"
        mock_addr.address = "192.168.1.100"
        mock_addr.netmask = "255.255.255.0"
        mock_addr.broadcast = "192.168.1.255"
        
        mock_psutil.net_if_addrs.return_value = {
            "eth0": [mock_addr],
            "lo": [mock_addr]
        }
        mock_import.return_value = mock_psutil
        
        result = get_network_interfaces()
        
        assert len(result) == 2
        assert result[0]["name"] in ["eth0", "lo"]
        assert len(result[0]["addresses"]) == 1
        assert result[0]["addresses"][0]["family"] == "AF_INET"
        assert result[0]["addresses"][0]["address"] == "192.168.1.100"
    
    @patch('importlib.import_module')
    def test_get_network_interfaces_psutil_not_available(self, mock_import):
        """测试psutil不可用时的处理"""
        mock_import.side_effect = ImportError("No module named 'psutil'")
        
        result = get_network_interfaces()
        
        assert result == []
    
    @patch('importlib.import_module')
    def test_get_network_interfaces_exception(self, mock_import):
        """测试获取网络接口时的异常处理"""
        mock_psutil = MagicMock()
        mock_psutil.net_if_addrs.side_effect = Exception("Network error")
        mock_import.return_value = mock_psutil
        
        result = get_network_interfaces()
        
        assert len(result) == 1
        assert "error" in result[0]


@pytest.mark.unit
class TestBackendRecommendation:
    """后端推荐测试"""
    
    @patch('sage.kernel.utils.system.environment.detect_execution_environment')
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    def test_recommend_backend_ray_environment(self, mock_gpu, mock_resources, mock_env):
        """测试Ray环境的后端推荐"""
        mock_env.return_value = "ray"
        mock_resources.return_value = {"cpu": {"count": 16}, "memory": {"total": 32 * 1024**3}}
        mock_gpu.return_value = {"available": False}
        
        result = recommend_backend()
        
        assert result["environment"] == "ray"
        assert result["primary_backend"] == "ray"
        assert result["communication_layer"] == "ray_queue"
        assert any("Ray cluster detected" in reason for reason in result["reasoning"])
    
    @patch('sage.kernel.utils.system.environment.detect_execution_environment')
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    def test_recommend_backend_kubernetes_environment(self, mock_gpu, mock_resources, mock_env):
        """测试Kubernetes环境的后端推荐"""
        mock_env.return_value = "kubernetes"
        mock_resources.return_value = {"cpu": {"count": 8}, "memory": {"total": 16 * 1024**3}}
        mock_gpu.return_value = {"available": False}
        
        result = recommend_backend()
        
        assert result["environment"] == "kubernetes"
        assert result["primary_backend"] == "ray"
        assert "local" in result["secondary_backends"]
        assert result["communication_layer"] == "network"
    
    @patch('sage.kernel.utils.system.environment.detect_execution_environment')
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    def test_recommend_backend_with_gpu(self, mock_gpu, mock_resources, mock_env):
        """测试有GPU时的后端推荐"""
        mock_env.return_value = "local"
        mock_resources.return_value = {"cpu": {"count": 8}, "memory": {"total": 16 * 1024**3}}
        mock_gpu.return_value = {"available": True, "count": 2}
        
        result = recommend_backend()
        
        assert result["gpu_support"] is True
        assert result["communication_layer"] == "gpu_direct"
        assert any("GPU available" in reason for reason in result["reasoning"])
    
    @patch('sage.kernel.utils.system.environment.detect_execution_environment')
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    def test_recommend_backend_high_memory(self, mock_gpu, mock_resources, mock_env):
        """测试高内存时的后端推荐"""
        mock_env.return_value = "local"
        mock_resources.return_value = {"cpu": {"count": 4}, "memory": {"total": 64 * 1024**3}}
        mock_gpu.return_value = {"available": False}
        
        result = recommend_backend()
        
        assert result["memory_strategy"] == "mmap"
        assert any("High memory available" in reason for reason in result["reasoning"])
    
    @patch('sage.kernel.utils.system.environment.detect_execution_environment')
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    def test_recommend_backend_low_memory(self, mock_gpu, mock_resources, mock_env):
        """测试低内存时的后端推荐"""
        mock_env.return_value = "local"
        mock_resources.return_value = {"cpu": {"count": 2}, "memory": {"total": 4 * 1024**3}}
        mock_gpu.return_value = {"available": False}
        
        result = recommend_backend()
        
        assert result["memory_strategy"] == "conservative"
        assert any("Limited memory" in reason for reason in result["reasoning"])


@pytest.mark.unit
class TestEnvironmentValidation:
    """环境验证测试"""
    
    def test_validate_environment_for_backend_local(self):
        """测试本地后端环境验证"""
        result = validate_environment_for_backend("local")
        
        assert result["backend"] == "local"
        assert result["supported"] is True
        assert len(result["issues"]) == 0
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_validate_environment_for_backend_ray_available(self, mock_ray_available):
        """测试Ray后端环境验证 - 可用"""
        mock_ray_available.return_value = True
        
        with patch('sage.kernel.utils.system.environment.is_ray_cluster_active', return_value=False):
            result = validate_environment_for_backend("ray")
        
        assert result["backend"] == "ray"
        assert result["supported"] is True
        assert len(result["issues"]) == 0
        assert any("Initialize Ray cluster" in rec for rec in result["recommendations"])
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    def test_validate_environment_for_backend_ray_not_available(self, mock_ray_available):
        """测试Ray后端环境验证 - 不可用"""
        mock_ray_available.return_value = False
        
        result = validate_environment_for_backend("ray")
        
        assert result["backend"] == "ray"
        assert result["supported"] is False
        assert "Ray not installed" in result["issues"]
        assert any("Install Ray" in rec for rec in result["recommendations"])
    
    @patch('sage.kernel.utils.system.environment.is_ray_available')
    @patch('sage.kernel.utils.system.environment.get_network_interfaces')
    def test_validate_environment_for_backend_distributed(self, mock_network, mock_ray_available):
        """测试分布式后端环境验证"""
        mock_ray_available.return_value = True
        mock_network.return_value = [{"name": "eth0"}, {"name": "eth1"}]
        
        result = validate_environment_for_backend("distributed")
        
        assert result["backend"] == "distributed"
        assert result["supported"] is True


@pytest.mark.integration
class TestEnvironmentCapabilities:
    """环境能力集成测试"""
    
    @patch('sage.kernel.utils.system.environment.detect_execution_environment')
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    @patch('sage.kernel.utils.system.environment.get_network_interfaces')
    @patch('sage.kernel.utils.system.environment.get_ray_cluster_info')
    @patch('sage.kernel.utils.system.environment.recommend_backend')
    def test_get_environment_capabilities(self, mock_recommend, mock_ray_info, mock_network, mock_gpu, mock_resources, mock_env):
        """测试获取完整环境能力"""
        # 设置模拟返回值
        mock_env.return_value = "local"
        mock_resources.return_value = {"cpu": {"count": 8}}
        mock_gpu.return_value = {"available": False}
        mock_network.return_value = [{"name": "eth0"}]
        mock_ray_info.return_value = {"available": False}
        mock_recommend.return_value = {"primary_backend": "local"}
        
        result = get_environment_capabilities()
        
        # 验证结果包含所有预期字段
        assert "environment_type" in result
        assert "system_resources" in result
        assert "gpu_resources" in result
        assert "network_interfaces" in result
        assert "ray_info" in result
        assert "backend_recommendation" in result
        assert "python_version" in result
        assert "platform" in result
        
        # 验证各个函数都被调用
        mock_env.assert_called_once()
        mock_resources.assert_called_once()
        mock_gpu.assert_called_once()
        mock_network.assert_called_once()
        mock_ray_info.assert_called_once()
        mock_recommend.assert_called_once()
    
    def test_get_environment_capabilities_real_data(self):
        """测试获取真实环境能力数据"""
        result = get_environment_capabilities()
        
        # 基本结构验证
        assert isinstance(result, dict)
        assert "environment_type" in result
        assert "python_version" in result
        assert "platform" in result
        
        # Python版本格式验证
        python_version = result["python_version"]
        version_parts = python_version.split('.')
        assert len(version_parts) >= 2
        assert all(part.isdigit() for part in version_parts)


# 性能和边界测试
@pytest.mark.slow
class TestEnvironmentPerformance:
    """环境检测性能测试"""
    
    def test_detect_execution_environment_performance(self):
        """测试环境检测性能"""
        import time
        
        start_time = time.time()
        for _ in range(10):
            detect_execution_environment()
        elapsed_time = time.time() - start_time
        
        # 10次检测应该在合理时间内完成
        assert elapsed_time < 1.0  # 应在1秒内完成
    
    @patch('sage.kernel.utils.system.environment.get_system_resources')
    @patch('sage.kernel.utils.system.environment.detect_gpu_resources')
    def test_get_environment_capabilities_performance(self, mock_gpu, mock_resources):
        """测试获取环境能力的性能"""
        import time
        
        # 模拟快速返回
        mock_resources.return_value = {"cpu": {"count": 4}}
        mock_gpu.return_value = {"available": False}
        
        start_time = time.time()
        result = get_environment_capabilities()
        elapsed_time = time.time() - start_time
        
        # 应该在合理时间内完成
        assert elapsed_time < 0.5  # 应在0.5秒内完成
        assert isinstance(result, dict)
