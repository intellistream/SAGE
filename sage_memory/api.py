from sage_utils.embedding_methods.mockembedder import MockTextEmbedder
from sage_memory.memory_manager import MemoryManager

def create_memory(config):
    """初始化内存管理器并创建测试集合"""
    default_model = MockTextEmbedder(fixed_dim=128)
    manager = MemoryManager()
    col = manager.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=default_model,
        dim=128,
        description="operator_test vdb collection",
        # as_ray_actor=(config.get("platform", False) == "remote")
        as_ray_actor=False
    )
    col.add_metadata_field("owner")
    col.add_metadata_field("show_type")
    texts = [
        ("hello world", {"owner": "ruicheng", "show_type": "text"}),
        ("你好，世界", {"owner": "Jun", "show_type": "text"}),
        ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
    ]
    for text, metadata in texts:
        col.insert(text, metadata)
    col.create_index(index_name="vdb_index")
    return col
