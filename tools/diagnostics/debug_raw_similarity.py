#!/usr/bin/env python3

from sage.middleware.components.neuromem.memory_manager import MemoryManager
import numpy as np

def debug_raw_similarity_scores():
    print("开始调试原始相似度分数...")
    
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
    
    # 获取索引和embedding模型
    index_info = vdb_collection.index_info["debug_index"]
    index = index_info["index"]
    embedding_model = vdb_collection.embedding_model_factory.get(
        index_info["embedding_model_name"]
    )
    
    # 手动编码查询文本
    print("编码查询文本...")
    query_text = "广东菜"
    query_embedding = embedding_model.encode(query_text)
    
    # 统一处理embedding格式
    if hasattr(query_embedding, "detach") and hasattr(query_embedding, "cpu"):
        query_embedding = query_embedding.detach().cpu().numpy()
    if isinstance(query_embedding, list):
        query_embedding = np.array(query_embedding)
    if not isinstance(query_embedding, np.ndarray):
        query_embedding = np.array(query_embedding)
    query_embedding = query_embedding.astype(np.float32)
    
    # 对查询向量进行L2归一化
    norm = np.linalg.norm(query_embedding)
    if norm > 0:
        query_embedding = query_embedding / norm
    
    print(f"查询向量归一化后的norm: {np.linalg.norm(query_embedding)}")
    
    # 直接调用FAISS索引搜索，不使用阈值
    print("直接调用FAISS搜索...")
    top_k_ids, distances = index.search(query_embedding, topk=5, threshold=None)
    
    print(f"原始搜索结果:")
    print(f"  IDs: {top_k_ids}")
    print(f"  Distances: {distances}")
    print(f"  最高相似度分数: {max(distances) if distances else 'N/A'}")
    
    # 测试不同阈值
    thresholds = [0.1, 0.2, 0.3, 0.5, 0.7]
    for threshold in thresholds:
        print(f"\n测试阈值 {threshold}:")
        ids, dists = index.search(query_embedding, topk=5, threshold=threshold)
        print(f"  找到 {len(ids)} 个结果")
        if ids:
            print(f"  分数: {dists}")
    
    # 清理
    manager.delete_collection("debug_collection")
    print("\n调试完成")

if __name__ == "__main__":
    debug_raw_similarity_scores()