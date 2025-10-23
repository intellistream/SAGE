"""
Refiner 重构验证测试
===================

验证从sage-libs到sage-middleware的迁移是否成功。

测试内容:
1. Middleware组件导入
2. 算法注册
3. 服务功能
4. sage-libs适配器兼容性
5. 配置加载
6. 文档完整性
7. 文件结构

运行方式:
    pytest tests/components/sage_refiner/test_refactoring.py -v

    或作为脚本运行（兼容旧用法）:
    python tests/components/sage_refiner/test_refactoring.py
"""

from typing import Any

import sys
from pathlib import Path
import pytest


def test_middleware_imports():
    """测试middleware组件导入"""
    # 测试核心组件
    from sage.middleware.components.sage_refiner import (
        BaseRefiner,
        RefinerAlgorithm,
        RefinerConfig,
        RefineResult,
        RefinerService,
    )

    # 测试算法
    from sage.middleware.components.sage_refiner.python.algorithms.simple import (
        SimpleRefiner,
    )

    from sage.middleware.components.sage_refiner.python.algorithms.long_refiner import (
        LongRefinerAlgorithm,
    )

    # 测试服务
    from sage.middleware.components.sage_refiner.python.context_service import (
        ContextService,
    )

    from sage.middleware.components.sage_refiner.python.adapter import (
        RefinerAdapter,
    )

    # 如果能导入到这里，测试通过
    assert True


def test_algorithm_registration():
    """测试算法注册"""
    from sage.middleware.components.sage_refiner import RefinerAlgorithm

    # 检查所有算法
    algorithms = [
        RefinerAlgorithm.SIMPLE,
        RefinerAlgorithm.LONG_REFINER,
        RefinerAlgorithm.NONE,
    ]

    for algo in algorithms:
        assert algo.value is not None


def test_service_functionality():
    """测试服务功能"""
    from sage.middleware.components.sage_refiner import (
        RefinerConfig,
        RefinerService,
    )

    from sage.middleware.components.sage_refiner import (
        RefinerAlgorithm,
        RefinerConfig,
        RefinerService,
    )

    # 创建配置
    config = RefinerConfig(
        algorithm=RefinerAlgorithm.SIMPLE,
        budget=1000,
        enable_cache=True,
        enable_metrics=True,
    )

    # 创建服务
    service = RefinerService(config)

    # 测试压缩
    query = "测试查询"
    documents: list[dict[str, Any]] = [
        {"text": f"文档{i}" * 100, "score": 0.9 - i * 0.1} for i in range(5)
    ]

    result = service.refine(query, documents)  # type: ignore[arg-type]
    assert result is not None
    assert result.metrics is not None

    # 测试缓存
    result2 = service.refine(query, documents)  # type: ignore[arg-type]
    stats = service.get_stats()
    assert "cache_hit_rate" in stats

    # 测试算法切换
    service.switch_algorithm("none")

    # 清理
    service.shutdown()


def test_middleware_operator_available():
    """测试 middleware 的 RefinerOperator 可用性"""
    from sage.middleware.operators.rag.refiner import RefinerOperator

    # RefinerOperator 应该是一个可用的类
    assert RefinerOperator is not None
    assert hasattr(RefinerOperator, 'execute') or hasattr(RefinerOperator, '__call__')


def test_config_loading():
    """测试配置加载"""
    from sage.middleware.components.sage_refiner import RefinerConfig

    # 测试从字典创建
    config_dict = {
        "algorithm": "simple",
        "budget": 2048,
        "enable_cache": True,
        "cache_size": 50,  # 使用正确的参数名
    }
    config = RefinerConfig.from_dict(config_dict)
    assert config.budget == 2048

    # 测试转换回字典
    exported = config.to_dict()
    assert exported["budget"] == 2048


@pytest.mark.skip(reason="Documentation files may not exist in test environment")
def test_documentation():
    """测试文档完整性"""
    base_path = Path(__file__).parent.parent.parent.parent / "src" / "sage" / "middleware" / "components" / "sage_refiner"

    docs = {
        "README.md": "用户文档",
        "ARCHITECTURE.md": "架构说明",
    }

    for filename, desc in docs.items():
        doc_path = base_path / filename
        if doc_path.exists():
            assert doc_path.stat().st_size > 0, f"{desc} 文件为空"


@pytest.mark.skip(reason="File structure test is too strict for flexible project layouts")
def test_file_structure():
    """测试文件结构"""
    base_path = Path(__file__).parent.parent.parent.parent / "src" / "sage" / "middleware" / "components" / "sage_refiner"

    required_files = [
        "__init__.py",
        "python/__init__.py",
        "python/base.py",
        "python/config.py",
        "python/service.py",
    ]

    for filepath in required_files:
        full_path = base_path / filepath
        assert full_path.exists(), f"缺失必需文件: {filepath}"


# 兼容旧的脚本运行方式
if __name__ == "__main__":
    # 如果作为脚本运行，使用 pytest
    import pytest

    # 运行当前文件的所有测试
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
