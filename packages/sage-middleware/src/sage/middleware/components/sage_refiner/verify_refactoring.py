"""
验证Refiner重构
===============

验证从sage-libs到sage-middleware的迁移是否成功。

测试内容:
1. Middleware组件导入
2. 算法注册
3. 服务功能
4. sage-libs适配器兼容性
5. 配置加载
"""

import sys
from pathlib import Path


def test_middleware_imports():
    """测试middleware组件导入"""
    print("=" * 60)
    print("测试 1: Middleware组件导入")
    print("=" * 60)

    try:
        # 测试核心组件
        from sage.middleware.components.sage_refiner import (
            BaseRefiner,
            RefinerAlgorithm,
            RefinerConfig,
            RefineResult,
            RefinerService,
        )

        print("✓ 核心组件导入成功")

        # 测试算法
        from sage.middleware.components.sage_refiner.python.algorithms.simple import (
            SimpleRefiner,
        )

        print("✓ SimpleRefiner导入成功")

        from sage.middleware.components.sage_refiner.python.algorithms.long_refiner import (
            LongRefinerAlgorithm,
        )

        print("✓ LongRefinerAlgorithm导入成功")

        # 测试服务
        from sage.middleware.components.sage_refiner.python.context_service import (
            ContextService,
        )

        print("✓ ContextService导入成功")

        from sage.middleware.components.sage_refiner.python.adapter import (
            RefinerAdapter,
        )

        print("✓ RefinerAdapter导入成功")

        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_algorithm_registration():
    """测试算法注册"""
    print("\n" + "=" * 60)
    print("测试 2: 算法注册")
    print("=" * 60)

    try:
        from sage.middleware.components.sage_refiner import RefinerAlgorithm

        # 检查所有算法
        algorithms = [
            RefinerAlgorithm.SIMPLE,
            RefinerAlgorithm.LONG_REFINER,
            RefinerAlgorithm.NONE,
        ]

        for algo in algorithms:
            print(f"✓ 算法注册: {algo.value}")

        return True
    except Exception as e:
        print(f"✗ 算法注册检查失败: {e}")
        return False


def test_service_functionality():
    """测试服务功能"""
    print("\n" + "=" * 60)
    print("测试 3: 服务功能")
    print("=" * 60)

    try:
        from sage.middleware.components.sage_refiner import (
            RefinerConfig,
            RefinerService,
        )

        # 创建配置
        config = RefinerConfig(
            algorithm="simple",
            budget=1000,
            enable_cache=True,
            enable_metrics=True,
        )
        print("✓ 配置创建成功")

        # 创建服务
        service = RefinerService(config)
        print("✓ 服务创建成功")

        # 测试压缩
        query = "测试查询"
        documents = [
            {"text": f"文档{i}" * 100, "score": 0.9 - i * 0.1} for i in range(5)
        ]

        result = service.refine(query, documents)
        print(f"✓ 压缩成功 (压缩率: {result.metrics.compression_rate:.2f}x)")

        # 测试缓存
        result2 = service.refine(query, documents)
        stats = service.get_stats()
        print(f"✓ 缓存工作 (命中率: {stats['cache_hit_rate']:.2%})")

        # 测试算法切换
        service.switch_algorithm("none")
        print("✓ 算法切换成功")

        # 清理
        service.shutdown()
        print("✓ 服务关闭成功")

        return True
    except Exception as e:
        print(f"✗ 服务功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_libs_adapter_compatibility():
    """测试sage-libs适配器兼容性"""
    print("\n" + "=" * 60)
    print("测试 4: sage-libs适配器兼容性")
    print("=" * 60)

    try:
        from sage.libs.rag.longrefiner import LongRefinerAdapter

        print("✓ LongRefinerAdapter导入成功")

        # 检查是否使用了middleware服务
        import inspect

        source = inspect.getsource(LongRefinerAdapter._init_refiner)

        if "RefinerService" in source:
            print("✓ LongRefinerAdapter已重构使用RefinerService")
        else:
            print("⚠ LongRefinerAdapter可能仍使用旧实现")

        return True
    except Exception as e:
        print(f"✗ 适配器兼容性测试失败: {e}")
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("测试 5: 配置加载")
    print("=" * 60)

    try:
        from sage.middleware.components.sage_refiner import RefinerConfig

        # 测试从字典创建
        config_dict = {
            "algorithm": "simple",
            "budget": 2048,
            "enable_cache": True,
            "max_cache_size": 50,
        }
        config = RefinerConfig.from_dict(config_dict)
        print("✓ 从字典创建配置成功")

        # 测试转换回字典
        exported = config.to_dict()
        assert exported["budget"] == 2048
        print("✓ 配置导出成功")

        # 测试YAML配置示例存在
        yaml_path = Path(__file__).parent / "config_examples.yaml"
        if yaml_path.exists():
            print(f"✓ 配置示例文件存在: {yaml_path}")
        else:
            print(f"⚠ 配置示例文件不存在: {yaml_path}")

        return True
    except Exception as e:
        print(f"✗ 配置加载测试失败: {e}")
        return False


def test_documentation():
    """测试文档完整性"""
    print("\n" + "=" * 60)
    print("测试 6: 文档完整性")
    print("=" * 60)

    base_path = Path(__file__).parent

    docs = {
        "README.md": "用户文档",
        "ARCHITECTURE.md": "架构说明",
        "DEVELOPER_GUIDE.md": "开发指南",
        "REFACTORING_SUMMARY.md": "重构总结",
        "config_examples.yaml": "配置示例",
    }

    all_exist = True
    for filename, desc in docs.items():
        doc_path = base_path / filename
        if doc_path.exists():
            size = doc_path.stat().st_size
            print(f"✓ {desc}: {filename} ({size} bytes)")
        else:
            print(f"✗ {desc}缺失: {filename}")
            all_exist = False

    return all_exist


def test_file_structure():
    """测试文件结构"""
    print("\n" + "=" * 60)
    print("测试 7: 文件结构")
    print("=" * 60)

    base_path = Path(__file__).parent

    required_files = [
        "__init__.py",
        "python/__init__.py",
        "python/base.py",
        "python/config.py",
        "python/service.py",
        "python/context_service.py",
        "python/adapter.py",
        "python/algorithms/__init__.py",
        "python/algorithms/simple.py",
        "python/algorithms/long_refiner.py",
        "python/algorithms/long_refiner_impl/__init__.py",
        "python/algorithms/long_refiner_impl/refiner.py",
        "python/algorithms/refiner_template.py",
        "examples/basic_usage.py",
        "tests/test_refiner.py",
    ]

    all_exist = True
    for filepath in required_files:
        full_path = base_path / filepath
        if full_path.exists():
            print(f"✓ {filepath}")
        else:
            print(f"✗ 缺失: {filepath}")
            all_exist = False

    return all_exist


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("SAGE Refiner 重构验证")
    print("=" * 60)

    tests = [
        ("Middleware导入", test_middleware_imports),
        ("算法注册", test_algorithm_registration),
        ("服务功能", test_service_functionality),
        ("sage-libs兼容性", test_libs_adapter_compatibility),
        ("配置加载", test_config_loading),
        ("文档完整性", test_documentation),
        ("文件结构", test_file_structure),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 异常: {e}")
            import traceback

            traceback.print_exc()
            results[name] = False

    # 输出总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有验证通过！重构成功！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
