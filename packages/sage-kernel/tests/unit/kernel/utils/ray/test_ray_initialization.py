"""
测试Ray初始化功能和runtime_env配置
"""

import os
import sys

import pytest

from sage.kernel.utils.ray.ray_utils import (
    RAY_AVAILABLE,
    ensure_ray_initialized,
    get_sage_kernel_runtime_env,
)

# 添加正确的项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sage_kernel_src = os.path.join(current_dir, "../../../../../src")
sys.path.insert(0, os.path.abspath(sage_kernel_src))


@pytest.mark.skipif(not RAY_AVAILABLE, reason="Ray not available")
class TestRayInitialization:
    """测试Ray初始化功能"""

    def test_get_sage_kernel_runtime_env(self):
        """测试获取Sage内核运行环境配置"""
        runtime_env = get_sage_kernel_runtime_env()

        assert isinstance(runtime_env, dict)
        assert "py_modules" in runtime_env
        assert "env_vars" in runtime_env
        assert "PYTHONPATH" in runtime_env["env_vars"]

        # 验证py_modules路径存在
        assert len(runtime_env["py_modules"]) > 0
        sage_src_path = runtime_env["py_modules"][0]
        assert os.path.exists(sage_src_path)
        assert sage_src_path.endswith("/src")

    def test_ensure_ray_initialized_with_default_env(self):
        """测试使用默认环境初始化Ray"""
        import ray

        # 如果Ray已经初始化，先关闭
        if ray.is_initialized():
            ray.shutdown()

        # 测试初始化
        ensure_ray_initialized()

        assert ray.is_initialized()

        # 验证Ray Actor可以导入sage模块
        @ray.remote
        def test_sage_import():
            try:
                from sage.platform.queue import RayQueueDescriptor  # noqa: F401

                return True
            except ImportError as e:
                return str(e)

        # Add project source to PYTHONPATH before importing sage modules
        # noqa: E402 - import must occur after sys.path modification

        result = ray.get(test_sage_import.remote())
        assert result is True, f"无法在Ray Actor中导入sage模块: {result}"

    def test_ensure_ray_initialized_with_custom_env(self):
        """测试使用自定义环境初始化Ray"""
        import ray

        # 如果Ray已经初始化，先关闭
        if ray.is_initialized():
            ray.shutdown()

        # 创建自定义runtime_env
        custom_env = {"env_vars": {"TEST_VAR": "test_value"}}

        # 测试初始化
        ensure_ray_initialized(runtime_env=custom_env)

        assert ray.is_initialized()

        # 验证自定义环境变量
        @ray.remote
        def check_env_var():
            import os

            return os.environ.get("TEST_VAR")

        result = ray.get(check_env_var.remote())
        assert result == "test_value"

    def teardown_method(self):
        """清理测试环境"""
        import ray

        if ray.is_initialized():
            ray.shutdown()
