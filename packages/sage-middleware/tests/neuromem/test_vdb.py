import os
import json
from sage.middleware.components.neuromem.memory_collection.vdb_collection import VDBMemoryCollection

def test_vdb_collection():
    # 创建vdb_collection，只需要一个name关键字
    config = {
        "name": "test_collection"
    }
    test_collection = VDBMemoryCollection(config=config)

    # 打开数据并批量插入
    base_dir = os.path.dirname(__file__)   
    file_path = os.path.join(base_dir, "toy_data.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = [item["text"] for item in data]
    metadatas = [item.get("metadata", {}) for item in data]

    test_collection.batch_insert_data(texts, metadatas)

    # 创建索引配置
    index_config = {
        "name": "test_index",
        "embedding_model": "default",
        "dim": 384,
        "backend_type": "FAISS",
        "description": "默认测试索引",
        "index_parameter": {}
    }
    test_collection.create_index(config=index_config)

    # 初始化索引
    test_collection.init_index("test_index", metadata_filter_func=lambda m: m.get("priority") == "low")

    # 搜索测试，使用较低的阈值
    results = test_collection.retrieve(
        raw_data="数据库事务可确保操作的原子性与一致性",
        index_name="test_index", 
        topk=3,  # 注意：这里使用topk而不是top_k
        threshold=0.5,  # 使用较低的阈值
        with_metadata=True
    )
    print("搜索结果:")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result['text']}")
        print(f"     元数据: {result['metadata']}")
    
    # 验证结果
    assert len(results) > 0, "应该找到搜索结果"
    assert any("数据库事务可确保操作的原子性与一致性" in r["text"] for r in results), "应该找到完全匹配的文本"
    print(f"\n✅ 测试通过！找到了 {len(results)} 个相关结果")
    
if __name__ == "__main__":
    test_vdb_collection()
