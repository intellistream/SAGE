import json
import os

from sage.middleware.components.neuromem.memory_manager import MemoryManager


def test_neuromem_manager():
    # 创建MemoryManager实例，使用默认路径
    manager = MemoryManager()

    # 创建一个新的内存集合
    config = {
        "name": "test_collection",
        "backend_type": "VDB",
        "description": "VDB测试集合",
    }

    # 测试一：创建集合并进行简单的检索
    vdb_collection = manager.create_collection(config)

    index_config = {
        "name": "test_index",
        "embedding_model": "default",
        "dim": 384,
        "backend_type": "FAISS",
        "description": "默认测试索引",
        "index_parameter": {},
    }
    vdb_collection.create_index(config=index_config)

    vdb_collection.insert(
        index_name="test_index",
        raw_data="将军，您的恩情我们一辈子也还不完！",
        metadata={"priority": "high"},
    )
    vdb_collection.insert(
        index_name="test_index",
        raw_data="我从丹东来带走一片雪白~",
        metadata={"priority": "low", "tag": "poem"},
    )
    vdb_collection.insert(
        index_name="test_index",
        raw_data="想吃广东菜",
        metadata={"priority": "low", "tag": "food"},
    )

    results = vdb_collection.retrieve(
        index_name="test_index",
        raw_data="广东菜",
        with_metadata=True,
        threshold=0.3,  # 使用较低的阈值，确保能找到相关匹配
    )
    assert any("想吃广东菜" in r["text"] for r in results), "找不到匹配的文本"
    print(f"✅ 测试一：创建集合通过！")

    # 测试二：查看集合是否存在
    assert manager.has_collection("test_collection"), "has_collection有误"
    assert not manager.has_collection("kv_collection"), "has_collection有误"
    print(f"✅ 测试二：集合存在性通过！")

    # 测试三：删除集合
    # 创建一个新的内存集合
    config = {
        "name": "delete_collection",
        "backend_type": "VDB",
        "description": "VDB测试集合",
    }
    vdb_collection = manager.create_collection(config)

    assert manager.has_collection("delete_collection"), "has_collection有误"
    manager.delete_collection("delete_collection")
    assert not manager.has_collection("delete_collection"), "delete_collection有误"
    print(f"✅ 测试三：删除集合通过！")

    # 测试四：列举所有集合
    all_collections = manager.list_collection()
    assert any(
        c["name"] == "test_collection" for c in all_collections
    ), "list_collection有误"
    print(f"✅ 测试四：列举所有集合通过！")

    # 测试五：持久化测试
    manager.store_collection()
    del manager
    manager = MemoryManager()
    vdb_collection = manager.get_collection("test_collection")
    results = vdb_collection.retrieve(
        index_name="test_index",
        raw_data="广东菜",
        with_metadata=True,
        threshold=0.3,  # 使用较低的阈值，确保能找到相关匹配
    )
    assert any("想吃广东菜" in r["text"] for r in results), "找不到匹配的文本"
    print(f"✅ 测试五：持久化测试通过！")

    # 清理测试环境
    manager.delete_collection("test_collection")


if __name__ == "__main__":
    import shutil

    test_neuromem_manager()

    # 清理测试过程中生成的data目录
    data_dir = "data"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
        print(f"✅ 已清理测试数据目录: {data_dir}")
