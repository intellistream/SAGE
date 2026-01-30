"""
Workload 4 Pipeline 测试

测试 Pipeline 的构建、服务注册和执行。
"""

import tempfile
from pathlib import Path

import pytest

try:
    from ..config import Workload4Config
    from ..pipeline import (
        Workload4Pipeline,
        create_workload4_pipeline,
        register_all_services,
        register_embedding_service,
        register_graph_memory_service,
        register_llm_service,
        register_vdb_services,
        run_workload4,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline import (
        Workload4Pipeline,
        create_workload4_pipeline,
        register_all_services,
        register_embedding_service,
        register_graph_memory_service,
        register_llm_service,
        register_vdb_services,
        run_workload4,
    )

    from config import Workload4Config


# =============================================================================
# Service Registration Tests
# =============================================================================


def test_register_embedding_service_local():
    """测试 Embedding Service 注册（Local环境）"""
    from sage.kernel.api.local_environment import LocalEnvironment

    env = LocalEnvironment(name="test_embedding")
    config = Workload4Config()

    success = register_embedding_service(env, config)
    assert success, "Embedding service registration should succeed"

    # 验证 service 已注册
    # Note: Service 通过 ServiceFactory 注册，可以通过 call_service 访问
    # 实际的服务列表存储在 ServiceFactory 中


def test_register_vdb_services_local():
    """测试 VDB Services 注册（Local环境）"""
    from sage.kernel.api.local_environment import LocalEnvironment

    env = LocalEnvironment(name="test_vdb")
    config = Workload4Config()

    results = register_vdb_services(env, config)

    assert "vdb1" in results, "Should register vdb1"
    assert "vdb2" in results, "Should register vdb2"
    assert results["vdb1"], "vdb1 registration should succeed"
    assert results["vdb2"], "vdb2 registration should succeed"


def test_register_graph_memory_service_local():
    """测试 Graph Memory Service 注册（Local环境）"""
    from sage.kernel.api.local_environment import LocalEnvironment

    env = LocalEnvironment(name="test_graph")
    config = Workload4Config()

    success = register_graph_memory_service(env, config)
    assert success, "Graph memory service registration should succeed"


def test_register_llm_service_local():
    """测试 LLM Service 注册（Local环境）"""
    from sage.kernel.api.local_environment import LocalEnvironment

    env = LocalEnvironment(name="test_llm")
    config = Workload4Config()

    success = register_llm_service(env, config)
    assert success, "LLM service registration should succeed"


def test_register_all_services_local():
    """测试所有 Services 注册（Local环境）"""
    from sage.kernel.api.local_environment import LocalEnvironment

    env = LocalEnvironment(name="test_all_services")
    config = Workload4Config()

    results = register_all_services(env, config)

    expected_services = ["embedding", "vdb1", "vdb2", "graph_memory", "llm"]

    for service_name in expected_services:
        assert service_name in results, f"Should have result for {service_name}"
        assert results[service_name], f"{service_name} registration should succeed"


# =============================================================================
# Pipeline Build Tests
# =============================================================================


def test_pipeline_init():
    """测试 Pipeline 初始化"""
    config = Workload4Config(num_tasks=10, duration=60)
    pipeline = Workload4Pipeline(config)

    assert pipeline.config == config
    assert pipeline.env is None, "Environment should not be created yet"
    assert pipeline.metrics is None, "Metrics should not be collected yet"


@pytest.mark.skip(reason="Requires full environment setup - Source instantiation issue")
def test_pipeline_build_local():
    """测试 Pipeline 构建（Local环境）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Workload4Config(
            num_tasks=5,
            duration=30,
            use_remote=False,  # Local 环境
            metrics_output_dir=tmpdir,
        )

        pipeline = Workload4Pipeline(config)
        pipeline.build(name="test_build_local")

        assert pipeline.env is not None, "Environment should be created"
        assert pipeline.env.name == "test_build_local"


def test_pipeline_build_config_override():
    """测试 Pipeline 构建时的配置覆盖"""
    config = Workload4Config(num_tasks=10)

    assert config.num_tasks == 10

    # 修改配置
    config.num_tasks = 20
    config.query_qps = 50.0

    pipeline = Workload4Pipeline(config)

    assert pipeline.config.num_tasks == 20
    assert pipeline.config.query_qps == 50.0


# =============================================================================
# Convenience Functions Tests
# =============================================================================


def test_create_workload4_pipeline():
    """测试便捷函数：create_workload4_pipeline"""
    pipeline = create_workload4_pipeline(num_tasks=15, duration=90)

    assert isinstance(pipeline, Workload4Pipeline)
    assert pipeline.config.num_tasks == 15
    assert pipeline.config.duration == 90


def test_create_workload4_pipeline_with_config():
    """测试便捷函数：使用已有 config"""
    config = Workload4Config(num_tasks=25, query_qps=30.0)
    pipeline = create_workload4_pipeline(config=config, duration=120)

    assert pipeline.config.num_tasks == 25
    assert pipeline.config.query_qps == 30.0
    assert pipeline.config.duration == 120  # Override


def test_create_workload4_pipeline_unknown_key():
    """测试便捷函数：未知配置键"""
    # 不应该崩溃，只是打印警告
    pipeline = create_workload4_pipeline(unknown_key="value")

    assert isinstance(pipeline, Workload4Pipeline)


# =============================================================================
# Integration Tests (需要环境)
# =============================================================================


@pytest.mark.skip(reason="Requires full environment setup")
def test_pipeline_run_local_minimal():
    """测试 Pipeline 最小执行（Local环境）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Workload4Config(
            num_tasks=2,
            duration=10,
            use_remote=False,
            query_qps=1.0,
            doc_qps=1.0,
            metrics_output_dir=tmpdir,
        )

        pipeline = Workload4Pipeline(config)
        pipeline.build(name="test_run_minimal")

        metrics = pipeline.run()

        assert metrics is not None
        assert metrics.end_to_end_time > 0


@pytest.mark.skip(reason="Requires full environment setup")
def test_run_workload4_convenience():
    """测试便捷函数：run_workload4"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metrics = run_workload4(
            num_tasks=3,
            duration=15,
            use_remote=False,
            metrics_output_dir=tmpdir,
        )

        assert metrics is not None
        assert metrics.end_to_end_time > 0


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_pipeline_run_before_build():
    """测试在 build 之前调用 run"""
    config = Workload4Config()
    pipeline = Workload4Pipeline(config)

    with pytest.raises(RuntimeError, match="Pipeline not built"):
        pipeline.run()


def test_config_validation():
    """测试配置验证"""
    config = Workload4Config()

    # 正常配置应该通过验证
    assert config.validate()

    # 配置在 __post_init__ 中自动验证，无法创建无效配置
    # 测试 validate() 方法本身
    try:
        # 手动创建无效配置并绕过 __post_init__
        invalid_config = Workload4Config.__new__(Workload4Config)
        invalid_config.query_qps = -1
        invalid_config.validate()
        assert False, "Should raise AssertionError"
    except AssertionError as e:
        assert "query_qps" in str(e)


# =============================================================================
# 运行测试
# =============================================================================


if __name__ == "__main__":
    # 基础测试（不需要完整环境）
    print("=" * 80)
    print("Running Basic Tests")
    print("=" * 80)

    test_pipeline_init()
    print("✓ test_pipeline_init")

    test_pipeline_build_config_override()
    print("✓ test_pipeline_build_config_override")

    test_create_workload4_pipeline()
    print("✓ test_create_workload4_pipeline")

    test_create_workload4_pipeline_with_config()
    print("✓ test_create_workload4_pipeline_with_config")

    test_create_workload4_pipeline_unknown_key()
    print("✓ test_create_workload4_pipeline_unknown_key")

    test_pipeline_run_before_build()
    print("✓ test_pipeline_run_before_build")

    test_config_validation()
    print("✓ test_config_validation")

    print("\n" + "=" * 80)
    print("Service Registration Tests")
    print("=" * 80)

    test_register_embedding_service_local()
    print("✓ test_register_embedding_service_local")

    test_register_vdb_services_local()
    print("✓ test_register_vdb_services_local")

    test_register_graph_memory_service_local()
    print("✓ test_register_graph_memory_service_local")

    test_register_llm_service_local()
    print("✓ test_register_llm_service_local")

    test_register_all_services_local()
    print("✓ test_register_all_services_local")

    print("\n" + "=" * 80)
    print("Pipeline Build Tests")
    print("=" * 80)

    test_pipeline_build_local()
    print("✓ test_pipeline_build_local")

    print("\n" + "=" * 80)
    print("All Tests Passed!")
    print("=" * 80)
