"""Hierarchical Service 单元测试

测试所有 Hierarchical 类的 MemoryService：
- hierarchical.three_tier
- hierarchical.graph_memory
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parents[7]
sys.path.insert(0, str(project_root / "packages" / "sage-middleware" / "src"))

from sage.middleware.components.sage_mem.memory_service.registry import MemoryServiceRegistry


def test_hierarchical_services_registered():
    """测试所有 Hierarchical Service 是否已注册"""
    print("=" * 60)
    print("测试 Hierarchical Services 注册状态")
    print("=" * 60)

    # 导入 hierarchical 包以触发注册
    try:
        import sage.middleware.components.sage_mem.memory_service.hierarchical  # noqa: F401

        print("✓ Hierarchical 包导入成功")
    except Exception as e:
        print(f"✗ Hierarchical 包导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 检查所有服务是否已注册
    expected_services = [
        "hierarchical.three_tier",
        "hierarchical.graph_memory",
    ]

    all_registered = True
    for service_name in expected_services:
        is_registered = MemoryServiceRegistry.is_registered(service_name)
        status = "✓" if is_registered else "✗"
        print(f"{status} {service_name}: {'已注册' if is_registered else '未注册'}")
        if not is_registered:
            all_registered = False

    # 列出所有 Hierarchical 服务
    print("\n所有 Hierarchical 服务:")
    hierarchical_services = MemoryServiceRegistry.list_services("hierarchical")
    for service in hierarchical_services:
        print(f"  - {service}")

    return all_registered


def test_service_from_config():
    """测试 from_config 方法"""
    print("\n" + "=" * 60)
    print("测试 from_config 方法")
    print("=" * 60)

    # Mock RuntimeConfig
    class MockConfig:
        def __init__(self, config_dict: dict):
            self._config = config_dict

        def get(self, key: str, default=None):
            """模拟 RuntimeConfig.get() 方法，支持点号分隔的键路径"""
            parts = key.split(".")
            value = self._config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value

    try:
        # 测试 three_tier
        config = MockConfig(
            {
                "services": {
                    "hierarchical": {
                        "three_tier": {
                            "tier_capacities": {
                                "stm": 10,
                                "mtm": 100,
                                "ltm": -1,
                            },
                            "migration_policy": "overflow",
                            "embedding_dim": 384,
                        }
                    }
                }
            }
        )

        service_class = MemoryServiceRegistry.get("hierarchical.three_tier")
        factory = service_class.from_config("hierarchical.three_tier", config)
        print("✓ ThreeTierMemoryService from_config 成功")
        print(f"  - service_name: {factory.service_name}")
        print(f"  - service_class: {factory.service_class.__name__}")
        print(f"  - kwargs: {list(factory.service_kwargs.keys())}")

        # 测试 graph_memory
        config = MockConfig(
            {
                "services": {
                    "hierarchical": {
                        "graph_memory": {
                            "graph_type": "knowledge_graph",
                            "link_policy": "bidirectional",
                            "ppr_depth": 2,
                            "ppr_damping": 0.85,
                            "enhanced_rerank": False,
                        }
                    }
                }
            }
        )

        service_class = MemoryServiceRegistry.get("hierarchical.graph_memory")
        factory = service_class.from_config("hierarchical.graph_memory", config)
        print("✓ GraphMemoryService from_config 成功")
        print(f"  - service_name: {factory.service_name}")
        print(f"  - service_class: {factory.service_class.__name__}")
        print(f"  - kwargs: {list(factory.service_kwargs.keys())}")

        return True
    except Exception as e:
        print(f"✗ from_config 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_service_creation():
    """测试 Service 实例化（简化测试，不依赖 C++ 扩展）"""
    print("\n" + "=" * 60)
    print("测试 Service 实例化")
    print("=" * 60)

    print("注意：完整的实例化测试需要 NeuroMem C++ 扩展支持")
    print("此处仅测试类是否可导入和基本属性")

    try:
        from sage.middleware.components.sage_mem.memory_service.hierarchical import (
            GraphMemoryService,
            ThreeTierMemoryService,
        )

        # 检查类属性
        print("✓ ThreeTierMemoryService 导入成功")
        print(
            f"  - 方法: {[m for m in dir(ThreeTierMemoryService) if not m.startswith('_') and callable(getattr(ThreeTierMemoryService, m))][:10]}"
        )

        print("✓ GraphMemoryService 导入成功")
        print(
            f"  - 方法: {[m for m in dir(GraphMemoryService) if not m.startswith('_') and callable(getattr(GraphMemoryService, m))][:10]}"
        )

        # 验证继承关系
        from sage.middleware.components.sage_mem.memory_service.base_service import (
            BaseMemoryService,
        )

        assert issubclass(ThreeTierMemoryService, BaseMemoryService)
        assert issubclass(GraphMemoryService, BaseMemoryService)
        print("✓ 继承关系验证成功（都继承自 BaseMemoryService）")

        # 验证必须实现的方法
        required_methods = ["insert", "retrieve", "delete", "get_stats", "from_config"]
        for cls in [ThreeTierMemoryService, GraphMemoryService]:
            for method in required_methods:
                assert hasattr(cls, method), f"{cls.__name__} 缺少方法: {method}"
        print(f"✓ 必须方法验证成功: {required_methods}")

        return True
    except Exception as e:
        print(f"✗ Service 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_registry_listing():
    """测试 Registry 列出功能"""
    print("\n" + "=" * 60)
    print("测试 Registry 列出功能")
    print("=" * 60)

    try:
        # 导入以触发注册
        import sage.middleware.components.sage_mem.memory_service.hierarchical  # noqa: F401

        # 列出所有 hierarchical 服务
        hierarchical_services = MemoryServiceRegistry.list_services("hierarchical")
        print(f"✓ Hierarchical 服务列表: {hierarchical_services}")
        assert len(hierarchical_services) == 2, "应该有 2 个 hierarchical 服务"

        # 获取类别
        for service in hierarchical_services:
            category = MemoryServiceRegistry.get_category(service)
            print(f"  - {service}: category={category}")
            assert category == "hierarchical", f"类别应该是 hierarchical，实际是 {category}"

        print("✓ 类别验证成功")

        return True
    except Exception as e:
        print(f"✗ Registry 列出测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("开始测试 Hierarchical Services\n")

    results = []

    # 测试1: 注册状态
    results.append(("注册状态测试", test_hierarchical_services_registered()))

    # 测试2: from_config
    results.append(("from_config 测试", test_service_from_config()))

    # 测试3: Service 导入
    results.append(("Service 导入测试", test_service_creation()))

    # 测试4: Registry 列出功能
    results.append(("Registry 列出测试", test_registry_listing()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
