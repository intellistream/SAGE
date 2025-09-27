#!/usr/bin/env python3

from sage.middleware.components.neuromem.memory_manager import MemoryManager

def debug_similarity_scores():
    print("开始调试相似度分数...")
    
    # 创建MemoryManager实例
    manager = MemoryManager()

    # 创建一个新的内存集合
    config = {
        "name": "debug_collection",
        "backend_type": "VDB",
        "description": "调试用集合",
    }

    vdb_collection = manager.create_collection(config)

    index_config = {
        "name": "debug_index",
        "embedding_model": "default",
        "dim": 384,
        "backend_type": "FAISS",
        "description": "调试索引",
        "index_parameter": {},
    }
    vdb_collection.create_index(config=index_config)

    # 插入测试数据
    print("插入测试数据...")
    vdb_collection.insert(
        index_name="debug_index",
        raw_data="想吃广东菜",
        metadata={"priority": "low", "tag": "food"},
    )
    
    # 先用默认阈值搜索
    print("进行默认阈值搜索...")
    results_default = vdb_collection.retrieve(
        index_name="debug_index",
        raw_data="广东菜",
        with_metadata=True,
    )
    
    print(f"默认阈值(0.7)找到 {len(results_default)} 个结果")
    
    # 用非常低的阈值搜索
    print("进行低阈值(0.05)搜索...")
    results = vdb_collection.retrieve(
        index_name="debug_index",
        raw_data="广东菜",
        with_metadata=True,
        threshold=0.05,  # 使用非常低的阈值
    )
    
    print(f"找到 {len(results)} 个结果:")
    for i, result in enumerate(results):
        print(f"  {i+1}. 文本: {result.get('text', 'N/A')}")
        print(f"      分数: {result.get('score', 'N/A')}")
        print(f"      元数据: {result.get('metadata', 'N/A')}")
        print()
    
    # 清理
    manager.delete_collection("debug_collection")
    print("调试完成")

if __name__ == "__main__":
    debug_similarity_scores()