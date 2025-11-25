from sage.platform.service import BaseService
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager


class VectorHashMemoryService(BaseService):
    def __init__(self, dim: int, nbits: int):
        """
        基于 Faiss LSH 的向量哈希桶服务

        Args:
            dim: 向量维度
            nbits: LSH 哈希位数
        """
        super().__init__()

        self.dim = dim
        self.nbits = nbits
        self.manager = MemoryManager()

        # 创建 VDB collection（失败时 manager 内部已记录日志）
        collection_config = {
            "name": "VectorHashMemory",
            "backend_type": "VDB",
            "description": "for vector hash memory with LSH index",
        }
        self.collection = self.manager.create_collection(collection_config)
        if self.collection is None:
            raise RuntimeError("Failed to create VectorHashMemory collection")

        # 创建 LSH 索引（失败时 collection 内部已记录日志）
        index_config = {
            "name": "lsh_index",
            "dim": dim,
            "backend_type": "FAISS",
            "description": "LSH index for vector hashing",
            "index_parameter": {
                "index_type": "LSH",
                "nbits": nbits,
            },
        }
        result = self.collection.create_index(config=index_config)
        if not result:
            raise RuntimeError("Failed to create LSH index")

    def insert(self, entry: str, vector, metadata: dict | None = None):
        """
        插入文本和对应的向量到 LSH 索引

        Args:
            entry: 原始文本数据
            vector: 预先生成的向量（numpy.ndarray）
            metadata: 元数据（可选）

        Returns:
            bool: 插入是否成功
        """
        result = self.collection.insert("lsh_index", entry, vector, metadata=metadata)
        return result is not None

    def delete(self, entry: str):
        """
        删除指定的文本条目

        Args:
            entry: 要删除的文本数据

        Returns:
            bool: 删除是否成功
        """
        result = self.collection.delete(entry)
        return result is not None

    def retrieve(self, query=None, vector=None, metadata: dict | None = None, topk: int = 5, threshold: float = 0.7):
        """
        使用查询向量检索相似的数据

        Args:
            query: 查询参数（为统一接口保留，但 VectorHashMemory 不使用）
            vector: 查询向量（numpy.ndarray）
            metadata: 元数据（为统一接口保留）
            topk: 返回的最大结果数
            threshold: 相似度阈值

        Returns:
            list[dict[str, Any]]: 检索结果列表，每个元素包含 text 和 metadata
        """
        if vector is None:
            return []
        
        results = self.collection.retrieve(
            vector,
            "lsh_index",
            topk=topk,
            threshold=threshold,
            with_metadata=True,
        )
        return results if results else []

if __name__ == "__main__":
    import numpy as np
    from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

    def test_vector_hash_memory():
        print("\n" + "=" * 70)
        print("向量哈希记忆服务测试")
        print("=" * 70 + "\n")

        # 1. 创建服务
        print("📝 步骤1: 创建 VectorHashMemoryService")
        dim = 128
        nbits = 64
        service = VectorHashMemoryService(dim=dim, nbits=nbits)
        print(f"   ✅ 创建成功 (dim={dim}, nbits={nbits})\n")

        # 2. 插入数据
        print("=" * 70)
        print("📝 步骤2: 插入数据")
        print("=" * 70)
        
        # 创建 embedding 模型
        embedding_model = apply_embedding_model("mockembedder")
        
        texts = [
            "机器学习是人工智能的一个分支",
            "深度学习使用神经网络进行训练",
            "自然语言处理用于理解人类语言",
        ]
        
        print(f"插入 {len(texts)} 条数据:")
        for i, text in enumerate(texts, 1):
            # 生成并归一化向量
            vector = embedding_model.encode(text)
            vector = vector / np.linalg.norm(vector)
            
            # 插入数据
            success = service.insert(text, vector)
            status = "✅ 成功" if success else "❌ 失败"
            print(f"  {i}. {status} - {text}")
        print()

        # 3. 检索数据
        print("=" * 70)
        print("📝 步骤3: 检索数据")
        print("=" * 70)
        
        query_text = "什么是深度学习和神经网络"
        print(f"查询文本: \"{query_text}\"")
        
        # 生成查询向量
        query_vector = embedding_model.encode(query_text)
        query_vector = query_vector / np.linalg.norm(query_vector)
        
        # 检索（使用关键字参数以匹配新接口）
        results = service.retrieve(vector=query_vector, topk=2, threshold=0.5)
        
        print(f"\n检索结果 (Top {len(results)}):")
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. text: {result['text']}")
                print(f"     metadata: {result.get('metadata', {})}")
        else:
            print("  (未找到结果)")

        print("\n" + "=" * 70)
        print("✅ 测试完成！")
        print("=" * 70 + "\n")

    test_vector_hash_memory()
