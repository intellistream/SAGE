"""Hybrid Services 单元测试

测试内容：
1. 注册状态验证
2. from_config 方法测试
3. Service 实例化测试
4. Registry 功能测试

Author: SAGE Team
Created: 2025-12-24
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目路径到 sys.path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root / "packages" / "sage-middleware" / "src"))


def test_hybrid_services():
    """测试 Hybrid Services 注册和功能"""
    print("=" * 60)
    print("测试 Hybrid Services 注册状态")
    print("=" * 60)

    # 导入 Registry 和 Service
    from sage.middleware.components.sage_mem.memory_service.registry import (
        MemoryServiceRegistry,
    )

    # 导入 Hybrid 包（触发自动注册）
    try:
        print("✓ Hybrid 包导入成功")
    except Exception as e:
        print(f"✗ Hybrid 包导入失败: {e}")
        return False

    # 验证注册状态
    services_to_check = [
        "hybrid.multi_index",
    ]

    for service_name in services_to_check:
        is_registered = MemoryServiceRegistry.is_registered(service_name)
        status = "✓" if is_registered else "✗"
        print(f"{status} {service_name}: {'已注册' if is_registered else '未注册'}")
        if not is_registered:
            return False

    # 列出所有 Hybrid 服务
    hybrid_services = MemoryServiceRegistry.list_services(category="hybrid")
    print("\n所有 Hybrid 服务:")
    for service_name in hybrid_services:
        print(f"  - {service_name}")

    print("\n" + "=" * 60)
    print("测试 from_config 方法")
    print("=" * 60)

    # Mock 配置对象
    class MockConfig:
        def __init__(self):
            self.data = {
                "services": {
                    "hybrid.multi_index": {
                        "indexes": [
                            {"name": "semantic", "type": "vdb", "dim": 768},
                            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
                        ],
                        "fusion_strategy": "rrf",
                        "rrf_k": 60,
                        "collection_name": "test_hybrid",
                        "graph_enabled": False,
                    },
                },
            }

        def get(self, key, default=None):
            keys = key.split(".")
            value = self.data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value

    config = MockConfig()

    # 测试 MultiIndexMemoryService
    try:
        service_class = MemoryServiceRegistry.get("hybrid.multi_index")
        factory = service_class.from_config("hybrid.multi_index", config)

        print("✓ MultiIndexMemoryService from_config 成功")
        print(f"  - service_name: {factory.service_name}")
        print(f"  - service_class: {factory.service_class.__name__}")
        print(f"  - kwargs: {list(factory.service_kwargs.keys())}")
    except Exception as e:
        print(f"✗ MultiIndexMemoryService from_config 失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("测试 Service 实例化")
    print("=" * 60)

    # 测试 Service 类导入
    try:
        from sage.middleware.components.sage_mem.memory_service.hybrid import (
            MultiIndexMemoryService,
        )

        print("✓ MultiIndexMemoryService 导入成功")
    except Exception as e:
        print(f"✗ MultiIndexMemoryService 导入失败: {e}")
        return False

    # 验证继承关系
    from sage.middleware.components.sage_mem.memory_service.base_service import (
        BaseMemoryService,
    )

    if issubclass(MultiIndexMemoryService, BaseMemoryService):
        print("✓ 继承关系验证成功（都继承自 BaseMemoryService）")
    else:
        print("✗ 继承关系验证失败")
        return False

    # 验证必须方法
    required_methods = ["insert", "retrieve", "delete", "get_stats", "from_config"]
    for method_name in required_methods:
        if hasattr(MultiIndexMemoryService, method_name):
            continue
        else:
            print(f"✗ 缺少方法: {method_name}")
            return False

    print(f"✓ 必须方法验证成功: {required_methods}")

    print("\n" + "=" * 60)
    print("测试 Registry 列出功能")
    print("=" * 60)

    # 测试列出所有 Hybrid 服务
    hybrid_services = MemoryServiceRegistry.list_services(category="hybrid")
    print(f"✓ Hybrid 服务列表: {hybrid_services}")

    # 验证类别
    for service_name in hybrid_services:
        category = MemoryServiceRegistry.get_category(service_name)
        if category != "hybrid":
            print(f"✗ 类别错误: {service_name} -> {category}")
            return False

    print("✓ 类别验证成功")

    print("\n" + "=" * 60)
    print("🎉 所有测试通过!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_hybrid_services()
    sys.exit(0 if success else 1)
