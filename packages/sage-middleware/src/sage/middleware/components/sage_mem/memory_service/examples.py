"""MemoryService Registry 使用示例

演示如何使用新的 Registry 系统创建和注册 MemoryService
"""

from __future__ import annotations

from typing import Any

import numpy as np

from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.memory_service import (
    BaseMemoryService,
    MemoryServiceRegistry,
)

# ========== 示例1: 创建一个简单的 MemoryService ==========


class SimpleVectorMemoryService(BaseMemoryService):
    """简单的向量记忆服务示例"""

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory"""
        # 读取配置
        dim = config.get(f"services.{service_name}.dim", 768)
        index_type = config.get(f"services.{service_name}.index_type", "IndexFlatL2")

        # 返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            dim=dim,
            index_type=index_type,
        )

    def __init__(self, dim: int = 768, index_type: str = "IndexFlatL2"):
        super().__init__()
        self.dim = dim
        self.index_type = index_type
        self.memories: dict[str, dict] = {}  # 简单的内存存储
        self.next_id = 0

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入记忆"""
        # 生成 ID
        memory_id = f"mem_{self.next_id}"
        self.next_id += 1

        # 存储记忆
        self.memories[memory_id] = {
            "text": entry,
            "vector": vector if vector is not None else np.random.rand(self.dim),
            "metadata": metadata or {},
        }

        return memory_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆"""
        # 简单的检索逻辑（返回所有记忆）
        results = []
        for mem_id, mem_data in list(self.memories.items())[:top_k]:
            results.append(
                {
                    "text": mem_data["text"],
                    "metadata": mem_data["metadata"],
                    "score": 0.95,  # 模拟相似度
                    "id": mem_id,
                }
            )
        return results

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self.memories:
            del self.memories[item_id]
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "total_count": len(self.memories),
            "index_type": self.index_type,
            "dim": self.dim,
        }


# ========== 示例2: 注册和使用 Service ==========


def example_register_and_use():
    """演示注册和使用 Service"""
    print("=" * 60)
    print("示例2: 注册和使用 Service")
    print("=" * 60)

    # 1. 注册 Service
    MemoryServiceRegistry.register("partitional.simple_vector", SimpleVectorMemoryService)
    print("✓ 注册 partitional.simple_vector")

    # 2. 列出已注册的服务
    all_services = MemoryServiceRegistry.list_services()
    print(f"✓ 已注册的服务: {all_services}")

    # 3. 获取 Service 类
    service_class = MemoryServiceRegistry.get("partitional.simple_vector")
    print(f"✓ 获取 Service 类: {service_class.__name__}")

    # 4. 创建 Service 实例（直接创建，不通过 from_config）
    service = service_class(dim=1024, index_type="IndexHNSWFlat")
    print(f"✓ 创建 Service 实例: dim={service.dim}, index_type={service.index_type}")

    # 5. 使用 Service
    # 插入记忆
    memory_id1 = service.insert("Hello, world!", vector=np.random.rand(1024))
    memory_id2 = service.insert("SAGE is awesome!", vector=np.random.rand(1024))
    print(f"✓ 插入 2 条记忆: {memory_id1}, {memory_id2}")

    # 检索记忆
    results = service.retrieve(query="Hello", top_k=5)
    print(f"✓ 检索结果: {len(results)} 条")
    for i, result in enumerate(results):
        print(f"  [{i + 1}] {result['text']} (score: {result['score']}, id: {result['id']})")

    # 获取统计信息
    stats = service.get_stats()
    print(f"✓ 统计信息: {stats}")

    # 删除记忆
    success = service.delete(memory_id1)
    print(f"✓ 删除记忆 {memory_id1}: {success}")

    # 再次获取统计信息
    stats = service.get_stats()
    print(f"✓ 更新后的统计信息: {stats}")


# ========== 示例3: 按类别列出服务 ==========


def example_list_by_category():
    """演示按类别列出服务"""
    print("\n" + "=" * 60)
    print("示例3: 按类别列出服务")
    print("=" * 60)

    # 注册多个服务
    MemoryServiceRegistry.clear()
    MemoryServiceRegistry.register("partitional.vector_memory", SimpleVectorMemoryService)
    MemoryServiceRegistry.register("partitional.key_value_memory", SimpleVectorMemoryService)
    MemoryServiceRegistry.register("hierarchical.graph_memory", SimpleVectorMemoryService)
    MemoryServiceRegistry.register("hybrid.multi_index", SimpleVectorMemoryService)

    print("✓ 注册 4 个服务")

    # 列出所有服务
    all_services = MemoryServiceRegistry.list_services()
    print(f"✓ 所有服务 ({len(all_services)}): {all_services}")

    # 按类别列出服务
    for category in ["partitional", "hierarchical", "hybrid"]:
        services = MemoryServiceRegistry.list_services(category=category)
        print(f"✓ {category.capitalize()} 服务 ({len(services)}): {services}")

    # 列出所有类别
    categories = MemoryServiceRegistry.list_categories()
    print(f"✓ 所有类别: {categories}")


# ========== 示例4: from_config 使用 ==========


def example_from_config():
    """演示 from_config 使用"""
    print("\n" + "=" * 60)
    print("示例4: from_config 使用")
    print("=" * 60)

    # 模拟 RuntimeConfig
    class MockConfig:
        def __init__(self):
            self.data = {
                "services": {
                    "partitional.simple_vector": {
                        "dim": 1536,
                        "index_type": "IndexIVFFlat",
                    }
                }
            }

        def get(self, key, default=None):
            keys = key.split(".")
            value = self.data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    config = MockConfig()

    # 从配置创建 ServiceFactory
    service_class = SimpleVectorMemoryService
    factory = service_class.from_config("partitional.simple_vector", config)

    print("✓ ServiceFactory 创建成功")
    print(f"  - service_name: {factory.service_name}")
    print(f"  - service_class: {factory.service_class.__name__}")
    print(f"  - service_kwargs: {factory.service_kwargs}")

    # 通过 Factory 创建 Service 实例（模拟）
    service = factory.service_class(**factory.service_kwargs)
    print("✓ Service 实例创建成功")
    print(f"  - dim: {service.dim}")
    print(f"  - index_type: {service.index_type}")


# ========== 主函数 ==========


def main():
    """运行所有示例"""
    example_register_and_use()
    example_list_by_category()
    example_from_config()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
