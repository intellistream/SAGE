"""
from sage.common.utils.logging.custom_logger import CustomLogger
VDB Service API 使用示例
展示如何正确使用VDB微服务的API接口进行向量存储和相似性搜索
"""

import numpy as np
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.api.vdb_api import VDBServiceAPI
from sage.middleware.services.vdb import create_vdb_service_factory


def test_vdb_service_api():
    """测试VDB服务API的正确使用方式"""
    self.logger.info("🚀 VDB Service API Demo")
    self.logger.info("=" * 50)

    # 创建环境
    env = LocalEnvironment("vdb_service_demo")

    # 注册VDB服务 - FAISS后端
    vdb_factory = create_vdb_service_factory(
        service_name="demo_vdb_service",
        embedding_dimension=384,
        index_type="IndexFlatL2",  # 精确搜索
        max_vectors=100000,
        similarity_threshold=0.8,
    )
    env.register_service_factory("demo_vdb_service", vdb_factory)

    self.logger.info("✅ VDB Service registered with FAISS backend")
    self.logger.info("   - Index: IndexFlatL2 (精确L2距离)")
    self.logger.info("   - Dimension: 384")
    self.logger.info("   - Max vectors: 100,000")
    self.logger.info("   - Similarity threshold: 0.8")

    # 在实际应用中，你需要启动环境并获取服务代理
    # env.submit()  # 启动环境
    # vdb_service = env.get_service_proxy("demo_vdb_service")

    # 这里我们演示API接口的预期使用方式
    demonstrate_vdb_api_usage()


def demonstrate_vdb_api_usage():
    """演示VDB服务API的标准使用模式"""
    self.logger.info("\n📝 VDB Service API Usage Patterns:")
    self.logger.info("-" * 40)

    # 展示API接口
    self.logger.info("💡 VDB Service API Interface:")
    self.logger.info("   class VDBServiceAPI:")
    self.logger.info("     - add_vectors(documents: List[Dict]) -> List[str]")
    self.logger.info("     - search(query_vector, top_k, threshold) -> List[Dict]")
    self.logger.info("     - get_vector(doc_id: str) -> Optional[Dict]")
    self.logger.info("     - delete_vectors(doc_ids: List[str]) -> bool")
    self.logger.info("     - update_vector(doc_id: str, document: Dict) -> bool")
    self.logger.info("     - count() -> int")
    self.logger.info("     - save_index(path: str) -> bool")
    self.logger.info("     - load_index(path: str) -> bool")

    self.logger.info("\n📋 Standard Usage Example:")
    usage_code = """
# 1. 获取服务代理
vdb_service = env.get_service_proxy("demo_vdb_service")

# 2. 准备向量文档
documents = [
    {
        "id": "doc_001",
        "vector": np.random.random(384).tolist(),  # 384维向量
        "text": "Python是一种高级编程语言",
        "metadata": {
            "category": "programming", 
            "language": "python",
            "topic": "introduction"
        }
    },
    {
        "id": "doc_002", 
        "vector": np.random.random(384).tolist(),
        "text": "机器学习是人工智能的一个分支",
        "metadata": {
            "category": "ai",
            "topic": "machine_learning"
        }
    }
]

# 3. 添加向量到数据库
doc_ids = vdb_service.add_vectors(documents)
self.logger.info(f"Added documents: {doc_ids}")

# 4. 向量相似性搜索
query_vector = np.random.random(384).tolist()
search_results = vdb_service.search(
    query_vector=query_vector,
    top_k=5,
    similarity_threshold=0.8
)

# 5. 获取特定文档
document = vdb_service.get_vector("doc_001")

# 6. 更新文档
updated_doc = {
    "id": "doc_001",
    "vector": np.random.random(384).tolist(),
    "text": "Python是一种强大的编程语言，广泛用于数据科学",
    "metadata": {"category": "programming", "updated": True}
}
success = vdb_service.update_vector("doc_001", updated_doc)

# 7. 管理操作
total_count = vdb_service.count()
saved = vdb_service.save_index("/path/to/index")
"""
    self.logger.info(usage_code)

    # 模拟执行结果
    self.logger.info("🎯 Expected Results:")
    operations = [
        ("add_vectors(documents)", "['doc_001', 'doc_002']"),
        ("search(query_vector, top_k=5)", "[{'id': 'doc_001', 'score': 0.92, ...}]"),
        ("get_vector('doc_001')", "{'id': 'doc_001', 'vector': [...], 'text': '...'}"),
        ("update_vector('doc_001', updated_doc)", "True"),
        ("count()", "2"),
        ("save_index('/path/to/index')", "True"),
    ]

    for operation, result in operations:
        self.logger.info(f"   {operation:<35} -> {result}")


def demonstrate_semantic_search_patterns():
    """演示语义搜索的高级模式"""
    self.logger.info("\n🔍 Semantic Search Patterns:")
    self.logger.info("-" * 40)

    search_patterns = '''
# 1. 多模态文档搜索
class DocumentSearchEngine:
    def __init__(self, vdb_service: VDBServiceAPI):
        self.vdb = vdb_service
    
    def index_document(self, doc_id: str, title: str, content: str, 
                      title_embedding: List[float], content_embedding: List[float]):
        """索引文档的标题和内容"""
        # 索引标题
        title_doc = {
            "id": f"{doc_id}_title",
            "vector": title_embedding,
            "text": title,
            "metadata": {"type": "title", "parent_doc": doc_id}
        }
        
        # 索引内容
        content_doc = {
            "id": f"{doc_id}_content", 
            "vector": content_embedding,
            "text": content,
            "metadata": {"type": "content", "parent_doc": doc_id}
        }
        
        return self.vdb.add_vectors([title_doc, content_doc])
    
    def semantic_search(self, query_embedding: List[float], doc_type=None):
        """语义搜索"""
        results = self.vdb.search(
            query_vector=query_embedding,
            top_k=20,
            similarity_threshold=0.7
        )
        
        # 按文档类型过滤
        if doc_type:
            results = [r for r in results if r["metadata"]["type"] == doc_type]
        
        return results

# 2. 分层检索
class HierarchicalRetrieval:
    def __init__(self, vdb_service: VDBServiceAPI):
        self.vdb = vdb_service
    
    def coarse_to_fine_search(self, query_vector: List[float]):
        """粗到细的检索策略"""
        # 第一阶段：粗粒度搜索（更多结果，较低阈值）
        coarse_results = self.vdb.search(
            query_vector=query_vector,
            top_k=100,
            similarity_threshold=0.6
        )
        
        # 第二阶段：细粒度重排序（基于更复杂的相似性计算）
        fine_results = self.rerank_results(query_vector, coarse_results)
        
        return fine_results[:10]  # 返回top 10
    
    def rerank_results(self, query_vector, candidates):
        """重排序候选结果"""
        # 这里可以使用更复杂的相似性计算
        # 例如：考虑metadata权重、时间衰减等
        return sorted(candidates, key=lambda x: x["score"], reverse=True)

# 3. 实时更新索引
class RealTimeIndex:
    def __init__(self, vdb_service: VDBServiceAPI):
        self.vdb = vdb_service
        self.pending_updates = []
    
    def add_document_async(self, document: Dict):
        """异步添加文档"""
        self.pending_updates.append(('add', document))
        
        # 批量处理
        if len(self.pending_updates) >= 100:
            self.flush_updates()
    
    def flush_updates(self):
        """批量执行更新"""
        add_docs = [doc for action, doc in self.pending_updates if action == 'add']
        
        if add_docs:
            self.vdb.add_vectors(add_docs)
        
        self.pending_updates.clear()
'''
    self.logger.info(search_patterns)


def demonstrate_vector_management():
    """演示向量管理的最佳实践"""
    self.logger.info("\n🗂️ Vector Management Best Practices:")
    self.logger.info("-" * 40)

    management_patterns = '''
# 1. 向量版本管理
class VectorVersionManager:
    def __init__(self, vdb_service: VDBServiceAPI):
        self.vdb = vdb_service
    
    def add_versioned_vector(self, base_id: str, vector: List[float], 
                           text: str, version: int = 1):
        """添加带版本的向量"""
        doc_id = f"{base_id}_v{version}"
        document = {
            "id": doc_id,
            "vector": vector,
            "text": text,
            "metadata": {
                "base_id": base_id,
                "version": version,
                "is_latest": True
            }
        }
        
        # 将旧版本标记为非最新
        old_versions = self.get_all_versions(base_id)
        for old_doc in old_versions:
            old_doc["metadata"]["is_latest"] = False
            self.vdb.update_vector(old_doc["id"], old_doc)
        
        return self.vdb.add_vectors([document])
    
    def get_latest_version(self, base_id: str):
        """获取最新版本"""
        # 这需要结合metadata搜索功能
        pass

# 2. 索引优化
class IndexOptimizer:
    def __init__(self, vdb_service: VDBServiceAPI):
        self.vdb = vdb_service
    
    def optimize_index(self):
        """优化索引性能"""
        # 保存当前索引
        backup_path = f"/backup/index_{int(time.time())}"
        self.vdb.save_index(backup_path)
        
        # 重建索引（如果支持）
        # self.vdb.rebuild_index()
        
        self.logger.info(f"Index optimized, backup saved to {backup_path}")
    
    def cleanup_old_vectors(self, retention_days: int = 30):
        """清理旧向量"""
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        
        # 这需要结合timestamp metadata
        # old_docs = self.find_vectors_before(cutoff_time)
        # self.vdb.delete_vectors([doc["id"] for doc in old_docs])

# 3. 监控和度量
class VDBMonitor:
    def __init__(self, vdb_service: VDBServiceAPI):
        self.vdb = vdb_service
    
    def get_health_metrics(self):
        """获取健康度量"""
        return {
            "total_vectors": self.vdb.count(),
            "index_size": "计算索引大小",
            "average_query_time": "查询平均耗时",
            "memory_usage": "内存使用情况"
        }
'''
    self.logger.info(management_patterns)

    # 模拟向量数据
    self.logger.info("\n📝 VDB Operations Demo:")

    # 生成示例向量
    vectors = []
    for i in range(5):
        vector = np.random.random(384).tolist()
        vectors.append(
            {
                "id": f"doc_{i}",
                "vector": vector,
                "text": f"这是第{i}个文档的内容",
                "metadata": {"source": "demo", "type": "document", "index": i},
            }
        )

    self.logger.info(f"  add_vectors({len(vectors)} docs) -> ✅ Added 5 vectors")

    # 搜索示例
    query_vector = np.random.random(384).tolist()
    self.logger.info(f"  search_vectors(query, top_k=3) -> 📖 Found 3 similar documents")
    self.logger.info(f"    - doc_2 (distance: 0.89)")
    self.logger.info(f"    - doc_1 (distance: 0.91)")
    self.logger.info(f"    - doc_4 (distance: 0.93)")

    # 其他操作
    self.logger.info(f"  get_vector('doc_1') -> 📖 Retrieved document")
    self.logger.info(f"  count() -> 📊 5 vectors")
    self.logger.info(f"  delete_vectors(['doc_0']) -> 🗑️  Deleted 1 vector")
    self.logger.info(f"  list_vectors(filter={{'type': 'document'}}) -> 📋 4 documents")

    self.logger.info("\n💡 VDB Service Features:")
    self.logger.info("   - FAISS高性能向量检索")
    self.logger.info("   - 多种索引类型 (Flat, HNSW, IVF, PQ)")
    self.logger.info("   - 元数据过滤")
    self.logger.info("   - 向量持久化")
    self.logger.info("   - 相似度搜索")


def test_vdb_index_types():
    """演示不同的FAISS索引类型"""
    self.logger.info("\n🔧 FAISS Index Types:")

    index_configs = {
        "IndexFlatL2": {"description": "精确L2距离搜索，适合小数据集", "config": {}},
        "IndexHNSWFlat": {
            "description": "HNSW图索引，快速近似搜索",
            "config": {"HNSW_M": 32, "HNSW_EF_CONSTRUCTION": 200, "HNSW_EF_SEARCH": 50},
        },
        "IndexIVFFlat": {
            "description": "IVF倒排索引，适合大数据集",
            "config": {"IVF_NLIST": 100, "IVF_NPROBE": 10},
        },
        "IndexIVFPQ": {
            "description": "IVF+PQ量化，内存高效",
            "config": {"IVF_NLIST": 100, "IVF_NPROBE": 10, "PQ_M": 8, "PQ_NBITS": 8},
        },
    }

    for index_type, info in index_configs.items():
        vdb_factory = create_vdb_service_factory(
            service_name=f"vdb_{index_type.lower()}",
            embedding_dimension=384,
            index_type=index_type,
            faiss_config=info["config"],
        )
        self.logger.info(f"✅ {index_type}: {info['description']}")


def test_vdb_applications():
    """演示VDB服务的应用场景"""
    self.logger.info("\n🎯 VDB Service Applications:")

    applications = [
        {
            "name": "语义搜索",
            "config": {
                "embedding_dimension": 768,
                "index_type": "IndexHNSWFlat",
                "faiss_config": {"HNSW_M": 64},
            },
            "description": "搜索语义相似的文档",
        },
        {
            "name": "推荐系统",
            "config": {
                "embedding_dimension": 256,
                "index_type": "IndexIVFPQ",
                "faiss_config": {"IVF_NLIST": 1000, "PQ_M": 16},
            },
            "description": "基于用户向量推荐相似物品",
        },
        {
            "name": "图像检索",
            "config": {"embedding_dimension": 2048, "index_type": "IndexFlatL2"},
            "description": "查找视觉相似的图像",
        },
        {
            "name": "知识库检索",
            "config": {
                "embedding_dimension": 384,
                "index_type": "IndexIVFFlat",
                "faiss_config": {"IVF_NLIST": 500},
            },
            "description": "RAG应用中的知识检索",
        },
    ]

    for app in applications:
        self.logger.info(f"  📚 {app['name']}: {app['description']}")
        self.logger.info(f"      配置: {app['config']}")


if __name__ == "__main__":
    test_vdb_service_api()
    demonstrate_semantic_search_patterns()
    demonstrate_vector_management()
    self.logger.info("\n🎯 VDB Service API demo completed!")
    self.logger.info("\n📚 Next: Check Memory service API examples")
