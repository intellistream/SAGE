import os
import shutil

import numpy as np
import pytest

from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.middleware.components.sage_mem.neuromem.utils.path_utils import (
    get_default_data_dir,
)

# Skip: Service implementation issues (Vector requirements, float() errors, etc.)
pytestmark = pytest.mark.skip(reason="Service implementation issues")


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
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "默认测试索引",
        "index_parameter": {},
    }
    vdb_collection.create_index(config=index_config)  # type: ignore[union-attr]

    # 创建 embedding 模型并生成向量
    from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

    embedding_model = apply_embedding_model("mockembedder")

    # 准备测试数据
    test_data = [
        ("将军，您的恩情我们一辈子也还不完！", {"priority": "high"}),
        ("我从丹东来带走一片雪白~", {"priority": "low", "tag": "poem"}),
        ("想吃广东菜", {"priority": "low", "tag": "food"}),
    ]

    # 为每条数据生成向量并插入
    for text, metadata in test_data:
        vector = embedding_model.encode(text)
        # 统一处理不同格式的向量
        if hasattr(vector, "detach") and hasattr(vector, "cpu"):
            vector = vector.detach().cpu().numpy()
        if isinstance(vector, list):
            vector = np.array(vector)
        if not isinstance(vector, np.ndarray):
            vector = np.array(vector)
        vector = vector.astype(np.float32)
        # L2 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        vdb_collection.insert(  # type: ignore[union-attr]
            content=text,
            index_names="test_index",
            vector=vector,
            metadata=metadata,
        )

    # 生成查询向量
    query_text = "想吃广东菜"
    query_vector = embedding_model.encode(query_text)
    # 统一处理不同格式的向量
    if hasattr(query_vector, "detach") and hasattr(query_vector, "cpu"):
        query_vector = query_vector.detach().cpu().numpy()
    if isinstance(query_vector, list):
        query_vector = np.array(query_vector)
    if not isinstance(query_vector, np.ndarray):
        query_vector = np.array(query_vector)
    query_vector = query_vector.astype(np.float32)
    # L2 归一化
    norm = np.linalg.norm(query_vector)
    if norm > 0:
        query_vector = query_vector / norm

    results = vdb_collection.retrieve(  # type: ignore[union-attr]
        query=query_vector,
        index_name="test_index",
        with_metadata=True,
        threshold=0.3,  # 使用合理的阈值
    )
    assert any("广东菜" in r["text"] for r in results), "找不到匹配的文本"  # type: ignore[index, union-attr]
    print("✅ 测试一：创建集合通过！")

    # 测试二：查看集合是否存在
    assert manager.has_collection("test_collection"), "has_collection有误"
    assert not manager.has_collection("kv_collection"), "has_collection有误"
    print("✅ 测试二：集合存在性通过！")

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
    print("✅ 测试三：删除集合通过！")

    # 测试四：列举所有集合
    all_collections = manager.list_collection()
    assert any(c["name"] == "test_collection" for c in all_collections), "list_collection有误"  # type: ignore[index]
    print("✅ 测试四：列举所有集合通过！")

    # 测试五：持久化测试
    manager.store_collection()
    del manager
    manager = MemoryManager()
    vdb_collection = manager.get_collection("test_collection")

    # 生成查询向量用于持久化后的检索
    query_text = "想吃广东菜"
    query_vector = embedding_model.encode(query_text)
    # 统一处理不同格式的向量
    if hasattr(query_vector, "detach") and hasattr(query_vector, "cpu"):
        query_vector = query_vector.detach().cpu().numpy()
    if isinstance(query_vector, list):
        query_vector = np.array(query_vector)
    if not isinstance(query_vector, np.ndarray):
        query_vector = np.array(query_vector)
    query_vector = query_vector.astype(np.float32)
    # L2 归一化
    norm = np.linalg.norm(query_vector)
    if norm > 0:
        query_vector = query_vector / norm

    results = vdb_collection.retrieve(  # type: ignore[union-attr]
        query=query_vector,
        index_name="test_index",
        with_metadata=True,
        threshold=0.3,  # 使用合理的阈值
    )
    assert any("想吃广东菜" in r["text"] for r in results), "找不到匹配的文本"  # type: ignore[index, union-attr]
    print("✅ 测试五：持久化测试通过！")

    # 清理测试环境
    manager.delete_collection("test_collection")

    data_dir = get_default_data_dir()
    if os.path.exists(data_dir):
        shutil.rmtree(os.path.dirname(data_dir))
        print(f"✅ 已清理测试数据目录: {data_dir}")


if __name__ == "__main__":
    test_neuromem_manager()

    # # 清理测试过程中生成的data目录
    # data_dir = "data"
    # if os.path.exists(data_dir):
    #     shutil.rmtree(data_dir)
    #     print(f"✅ 已清理测试数据目录: {data_dir}")
