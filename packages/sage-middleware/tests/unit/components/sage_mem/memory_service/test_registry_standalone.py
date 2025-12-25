"""独立测试脚本 - 验证 MemoryService Registry 功能

直接导入，避免触发其他模块的 C++ 依赖
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

# 直接加载模块文件，避免触发 __init__.py
middleware_src = (
    Path(__file__).parents[5]
    / "src"
    / "sage"
    / "middleware"
    / "components"
    / "sage_mem"
    / "memory_service"
)

# 加载 base_service
base_service_path = middleware_src / "base_service.py"
spec = spec_from_file_location("base_service", base_service_path)
base_service_module = module_from_spec(spec)
spec.loader.exec_module(base_service_module)
BaseMemoryService = base_service_module.BaseMemoryService

# 加载 registry
registry_path = middleware_src / "registry.py"
spec = spec_from_file_location("registry", registry_path)
registry_module = module_from_spec(spec)
spec.loader.exec_module(registry_module)
MemoryServiceRegistry = registry_module.MemoryServiceRegistry


# Mock Service 用于测试
class MockService(BaseMemoryService):
    @classmethod
    def from_config(cls, service_name, config):
        return None  # Mock implementation

    def insert(
        self, entry, vector=None, metadata=None, *, insert_mode="passive", insert_params=None
    ):
        return "mock_id"

    def retrieve(self, query=None, vector=None, metadata=None, top_k=10):
        return []

    def delete(self, item_id):
        return True

    def get_stats(self):
        return {"total_count": 0}


def test_registry():
    """测试 Registry 基本功能"""
    print("=" * 60)
    print("测试 MemoryService Registry")
    print("=" * 60)

    # 清空 Registry
    MemoryServiceRegistry.clear()
    print("✓ Registry 已清空")

    # 测试注册
    MemoryServiceRegistry.register("partitional.vector_memory", MockService)
    MemoryServiceRegistry.register("hierarchical.graph_memory", MockService)
    MemoryServiceRegistry.register("hybrid.multi_index", MockService)
    print("✓ 注册 3 个服务成功")

    # 测试列出所有服务
    all_services = MemoryServiceRegistry.list_services()
    print(f"✓ 所有服务: {all_services}")
    assert len(all_services) == 3

    # 测试按类别列出服务
    partitional = MemoryServiceRegistry.list_services(category="partitional")
    print(f"✓ Partitional 服务: {partitional}")
    assert partitional == ["partitional.vector_memory"]

    hierarchical = MemoryServiceRegistry.list_services(category="hierarchical")
    print(f"✓ Hierarchical 服务: {hierarchical}")
    assert hierarchical == ["hierarchical.graph_memory"]

    hybrid = MemoryServiceRegistry.list_services(category="hybrid")
    print(f"✓ Hybrid 服务: {hybrid}")
    assert hybrid == ["hybrid.multi_index"]

    # 测试获取服务
    service_class = MemoryServiceRegistry.get("partitional.vector_memory")
    print(f"✓ 获取服务类: {service_class.__name__}")
    assert service_class == MockService

    # 测试检查注册状态
    assert MemoryServiceRegistry.is_registered("partitional.vector_memory") is True
    assert MemoryServiceRegistry.is_registered("nonexistent.service") is False
    print("✓ 注册状态检查正常")

    # 测试获取类别
    category = MemoryServiceRegistry.get_category("partitional.vector_memory")
    print(f"✓ 获取类别: {category}")
    assert category == "partitional"

    # 测试列出所有类别
    categories = MemoryServiceRegistry.list_categories()
    print(f"✓ 所有类别: {categories}")
    assert set(categories) == {"partitional", "hierarchical", "hybrid"}

    # 测试注销
    success = MemoryServiceRegistry.unregister("partitional.vector_memory")
    print(f"✓ 注销服务成功: {success}")
    assert success is True
    assert len(MemoryServiceRegistry.list_services()) == 2

    # 测试清空
    MemoryServiceRegistry.clear()
    print("✓ Registry 清空成功")
    assert len(MemoryServiceRegistry.list_services()) == 0

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    test_registry()
