"""
简单测试来验证JobManager的基本功能

注意：这个测试因为导入JobManager会触发sage.common的完整导入链（包括vLLM），
所以即使测试本身很快，导入阶段也会比较慢（~30秒）
"""

import pytest

# 标记为slow，因为导入JobManager会触发vLLM等重依赖的加载
pytestmark = pytest.mark.slow

from sage.kernel.runtime.job_manager import JobManager


def test_jobmanager_can_be_imported():
    """测试JobManager可以被成功导入"""
    assert JobManager is not None


def test_jobmanager_singleton():
    """测试JobManager的单例模式"""
    # 创建两个实例
    jm1 = JobManager()
    jm2 = JobManager()

    # 验证它们是同一个实例
    assert jm1 is jm2


def test_jobmanager_basic_attributes():
    """测试JobManager的基本属性"""
    jm = JobManager()

    # 验证基本属性存在
    assert hasattr(jm, "jobs")
    assert hasattr(jm, "logger")
    assert hasattr(jm, "server")
    assert hasattr(jm, "session_id")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
