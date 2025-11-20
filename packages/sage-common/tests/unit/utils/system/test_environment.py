"""
Unit tests for sage.common.utils.system.environment

Tests environment detection and resource monitoring utilities.
"""

import os
from unittest.mock import MagicMock, patch

from sage.common.utils.system.environment import (
    detect_execution_environment,
    detect_gpu_resources,
    get_system_resources,
    is_docker_environment,
    is_kubernetes_environment,
    is_ray_available,
    is_ray_cluster_active,
    is_slurm_environment,
    recommend_backend,
)


class TestDetectExecutionEnvironment:
    """Tests for detect_execution_environment()"""

    @patch("sage.common.utils.system.environment.is_ray_cluster_active")
    def test_detect_ray_environment(self, mock_ray_active):
        """Test detecting Ray environment"""
        mock_ray_active.return_value = True

        result = detect_execution_environment()

        assert result == "ray"

    @patch("sage.common.utils.system.environment.is_ray_cluster_active")
    @patch("sage.common.utils.system.environment.is_kubernetes_environment")
    def test_detect_kubernetes_environment(self, mock_k8s, mock_ray):
        """Test detecting Kubernetes environment"""
        mock_ray.return_value = False
        mock_k8s.return_value = True

        result = detect_execution_environment()

        assert result == "kubernetes"

    @patch("sage.common.utils.system.environment.is_ray_cluster_active")
    @patch("sage.common.utils.system.environment.is_kubernetes_environment")
    @patch("sage.common.utils.system.environment.is_docker_environment")
    def test_detect_docker_environment(self, mock_docker, mock_k8s, mock_ray):
        """Test detecting Docker environment"""
        mock_ray.return_value = False
        mock_k8s.return_value = False
        mock_docker.return_value = True

        result = detect_execution_environment()

        assert result == "docker"

    @patch("sage.common.utils.system.environment.is_ray_cluster_active")
    @patch("sage.common.utils.system.environment.is_kubernetes_environment")
    @patch("sage.common.utils.system.environment.is_docker_environment")
    @patch("sage.common.utils.system.environment.is_slurm_environment")
    def test_detect_slurm_environment(self, mock_slurm, mock_docker, mock_k8s, mock_ray):
        """Test detecting SLURM environment"""
        mock_ray.return_value = False
        mock_k8s.return_value = False
        mock_docker.return_value = False
        mock_slurm.return_value = True

        result = detect_execution_environment()

        assert result == "slurm"

    @patch("sage.common.utils.system.environment.is_ray_cluster_active")
    @patch("sage.common.utils.system.environment.is_kubernetes_environment")
    @patch("sage.common.utils.system.environment.is_docker_environment")
    @patch("sage.common.utils.system.environment.is_slurm_environment")
    def test_detect_local_environment(self, mock_slurm, mock_docker, mock_k8s, mock_ray):
        """Test detecting local environment"""
        mock_ray.return_value = False
        mock_k8s.return_value = False
        mock_docker.return_value = False
        mock_slurm.return_value = False

        result = detect_execution_environment()

        assert result == "local"


class TestIsRayAvailable:
    """Tests for is_ray_available()"""

    @patch("importlib.import_module")
    def test_ray_available(self, mock_import):
        """Test when Ray is available"""
        mock_import.return_value = MagicMock()

        result = is_ray_available()

        assert result is True
        mock_import.assert_called_once_with("ray")

    @patch("importlib.import_module")
    def test_ray_not_available(self, mock_import):
        """Test when Ray is not available"""
        mock_import.side_effect = ImportError("No module named 'ray'")

        result = is_ray_available()

        assert result is False


class TestIsRayClusterActive:
    """Tests for is_ray_cluster_active()"""

    @patch("sage.common.utils.system.environment.is_ray_available")
    @patch("importlib.import_module")
    def test_ray_cluster_active(self, mock_import, mock_available):
        """Test when Ray cluster is active"""
        mock_available.return_value = True
        mock_ray = MagicMock()
        mock_ray.is_initialized.return_value = True
        mock_import.return_value = mock_ray

        result = is_ray_cluster_active()

        assert result is True

    @patch("sage.common.utils.system.environment.is_ray_available")
    def test_ray_not_available(self, mock_available):
        """Test when Ray is not available"""
        mock_available.return_value = False

        result = is_ray_cluster_active()

        assert result is False


class TestIsKubernetesEnvironment:
    """Tests for is_kubernetes_environment()"""

    @patch("os.path.exists")
    def test_k8s_service_account_exists(self, mock_exists):
        """Test detecting K8s via service account"""
        mock_exists.return_value = True

        result = is_kubernetes_environment()

        assert result is True
        mock_exists.assert_called_with("/var/run/secrets/kubernetes.io/serviceaccount")

    @patch("os.path.exists")
    @patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"})
    def test_k8s_env_variable(self, mock_exists):
        """Test detecting K8s via environment variable"""
        mock_exists.return_value = False

        result = is_kubernetes_environment()

        assert result is True


class TestIsDockerEnvironment:
    """Tests for is_docker_environment()"""

    @patch("os.path.exists")
    def test_docker_env_file(self, mock_exists):
        """Test detecting Docker via .dockerenv"""
        mock_exists.return_value = True

        result = is_docker_environment()

        assert result is True
        mock_exists.assert_called_with("/.dockerenv")


class TestIsSlurmEnvironment:
    """Tests for is_slurm_environment()"""

    @patch.dict(os.environ, {"SLURM_JOB_ID": "12345"})
    def test_slurm_job_id(self):
        """Test detecting SLURM via job ID"""
        result = is_slurm_environment()

        assert result is True

    @patch.dict(os.environ, {"SLURM_CLUSTER_NAME": "test-cluster"}, clear=True)
    def test_slurm_cluster_name(self):
        """Test detecting SLURM via cluster name"""
        result = is_slurm_environment()

        assert result is True


class TestGetSystemResources:
    """Tests for get_system_resources()"""

    @patch("psutil.cpu_count")
    @patch("psutil.cpu_percent")
    @patch("psutil.cpu_freq")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_get_system_resources(
        self, mock_disk, mock_memory, mock_freq, mock_cpu_percent, mock_cpu_count
    ):
        """Test getting system resources"""
        # Mock CPU
        mock_cpu_count.side_effect = lambda logical=True: 8 if logical else 4
        mock_cpu_percent.return_value = 25.0
        mock_freq_data = MagicMock()
        mock_freq_data.current = 2400.0
        mock_freq_data.min = 800.0
        mock_freq_data.max = 3600.0
        mock_freq.return_value = mock_freq_data

        # Mock memory
        mock_mem = MagicMock()
        mock_mem.total = 16 * 1024**3
        mock_mem.available = 8 * 1024**3
        mock_mem.percent = 50.0
        mock_mem.used = 8 * 1024**3
        mock_mem.free = 8 * 1024**3
        mock_memory.return_value = mock_mem

        # Mock disk
        mock_disk_data = MagicMock()
        mock_disk_data.total = 500 * 1024**3
        mock_disk_data.used = 250 * 1024**3
        mock_disk_data.free = 250 * 1024**3
        mock_disk.return_value = mock_disk_data

        result = get_system_resources()

        # Check structure
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "platform" in result

        # Check CPU
        assert result["cpu"]["count"] == 8
        assert result["cpu"]["physical_count"] == 4

        # Check memory
        assert result["memory"]["total"] == 16 * 1024**3

        # Check disk
        assert result["disk"]["total"] == 500 * 1024**3


class TestDetectGPUResources:
    """Tests for detect_gpu_resources()"""

    @patch("subprocess.run")
    def test_detect_nvidia_gpu(self, mock_run):
        """Test detecting NVIDIA GPU"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "GPU 0: Tesla V100\n"
        mock_run.return_value = mock_result

        result = detect_gpu_resources()

        assert result["available"] is True
        assert result["count"] >= 0

    @patch("subprocess.run")
    def test_no_gpu_available(self, mock_run):
        """Test when no GPU is available"""
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

        result = detect_gpu_resources()

        assert result["available"] is False
        assert result["count"] == 0


class TestRecommendBackend:
    """Tests for recommend_backend()"""

    @patch("sage.common.utils.system.environment.detect_execution_environment")
    @patch("sage.common.utils.system.environment.get_system_resources")
    @patch("sage.common.utils.system.environment.detect_gpu_resources")
    def test_recommend_ray_backend(self, mock_gpu, mock_resources, mock_env):
        """Test recommending Ray backend"""
        mock_env.return_value = "ray"
        mock_resources.return_value = {
            "cpu": {"count": 16},
            "memory": {"total": 64 * 1024**3},
            "disk": {"total": 1024 * 1024**3},
        }
        mock_gpu.return_value = {"available": True, "count": 2}

        result = recommend_backend()

        assert "environment" in result
        assert "primary_backend" in result
        assert result["environment"] == "ray"

    @patch("sage.common.utils.system.environment.detect_execution_environment")
    @patch("sage.common.utils.system.environment.get_system_resources")
    @patch("sage.common.utils.system.environment.detect_gpu_resources")
    def test_recommend_local_backend(self, mock_gpu, mock_resources, mock_env):
        """Test recommending local backend"""
        mock_env.return_value = "local"
        mock_resources.return_value = {
            "cpu": {"count": 4},
            "memory": {"total": 8 * 1024**3},
            "disk": {"total": 256 * 1024**3},
        }
        mock_gpu.return_value = {"available": False, "count": 0}

        result = recommend_backend()

        assert "environment" in result
        assert "primary_backend" in result
        assert result["environment"] == "local"
