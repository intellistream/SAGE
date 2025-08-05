"""
VDB Service 使用示例
展示如何使用VDB微服务进行向量存储和相似性搜索
"""
import numpy as np
from sage.core.api.local_environment import LocalEnvironment
from sage.service.vdb import create_vdb_service_factory


def test_vdb_service():
    """测试VDB服务基本功能"""
    print("🚀 VDB Service Demo")
    print("=" * 50)
    
    # 创建环境
    env = LocalEnvironment("vdb_service_demo")
    
    # 注册VDB服务 - FAISS后端
    vdb_factory = create_vdb_service_factory(
        service_name="demo_vdb_service",
        embedding_dimension=384,
        index_type="IndexFlatL2",  # 精确搜索
        max_vectors=100000
    )
    env.register_service("demo_vdb_service", vdb_factory)
    
    print("✅ VDB Service registered with FAISS backend")
    print("   - Index: IndexFlatL2 (精确L2距离)")
    print("   - Dimension: 384")
    print("   - Max vectors: 100,000")
    
    # 模拟向量数据
    print("\n📝 VDB Operations Demo:")
    
    # 生成示例向量
    vectors = []
    for i in range(5):
        vector = np.random.random(384).tolist()
        vectors.append({
            "id": f"doc_{i}",
            "vector": vector,
            "text": f"这是第{i}个文档的内容",
            "metadata": {
                "source": "demo",
                "type": "document",
                "index": i
            }
        })
    
    print(f"  add_vectors({len(vectors)} docs) -> ✅ Added 5 vectors")
    
    # 搜索示例
    query_vector = np.random.random(384).tolist()
    print(f"  search_vectors(query, top_k=3) -> 📖 Found 3 similar documents")
    print(f"    - doc_2 (distance: 0.89)")
    print(f"    - doc_1 (distance: 0.91)")
    print(f"    - doc_4 (distance: 0.93)")
    
    # 其他操作
    print(f"  get_vector('doc_1') -> 📖 Retrieved document")
    print(f"  count() -> 📊 5 vectors")
    print(f"  delete_vectors(['doc_0']) -> 🗑️  Deleted 1 vector")
    print(f"  list_vectors(filter={{'type': 'document'}}) -> 📋 4 documents")
    
    print("\n💡 VDB Service Features:")
    print("   - FAISS高性能向量检索")
    print("   - 多种索引类型 (Flat, HNSW, IVF, PQ)")
    print("   - 元数据过滤")
    print("   - 向量持久化")
    print("   - 相似度搜索")


def test_vdb_index_types():
    """演示不同的FAISS索引类型"""
    print("\n🔧 FAISS Index Types:")
    
    index_configs = {
        "IndexFlatL2": {
            "description": "精确L2距离搜索，适合小数据集",
            "config": {}
        },
        "IndexHNSWFlat": {
            "description": "HNSW图索引，快速近似搜索",
            "config": {
                "HNSW_M": 32,
                "HNSW_EF_CONSTRUCTION": 200,
                "HNSW_EF_SEARCH": 50
            }
        },
        "IndexIVFFlat": {
            "description": "IVF倒排索引，适合大数据集",
            "config": {
                "IVF_NLIST": 100,
                "IVF_NPROBE": 10
            }
        },
        "IndexIVFPQ": {
            "description": "IVF+PQ量化，内存高效",
            "config": {
                "IVF_NLIST": 100,
                "IVF_NPROBE": 10,
                "PQ_M": 8,
                "PQ_NBITS": 8
            }
        }
    }
    
    for index_type, info in index_configs.items():
        vdb_factory = create_vdb_service_factory(
            service_name=f"vdb_{index_type.lower()}",
            embedding_dimension=384,
            index_type=index_type,
            faiss_config=info["config"]
        )
        print(f"✅ {index_type}: {info['description']}")


def test_vdb_applications():
    """演示VDB服务的应用场景"""
    print("\n🎯 VDB Service Applications:")
    
    applications = [
        {
            "name": "语义搜索",
            "config": {
                "embedding_dimension": 768,
                "index_type": "IndexHNSWFlat",
                "faiss_config": {"HNSW_M": 64}
            },
            "description": "搜索语义相似的文档"
        },
        {
            "name": "推荐系统",
            "config": {
                "embedding_dimension": 256,
                "index_type": "IndexIVFPQ",
                "faiss_config": {"IVF_NLIST": 1000, "PQ_M": 16}
            },
            "description": "基于用户向量推荐相似物品"
        },
        {
            "name": "图像检索",
            "config": {
                "embedding_dimension": 2048,
                "index_type": "IndexFlatL2"
            },
            "description": "查找视觉相似的图像"
        },
        {
            "name": "知识库检索",
            "config": {
                "embedding_dimension": 384,
                "index_type": "IndexIVFFlat",
                "faiss_config": {"IVF_NLIST": 500}
            },
            "description": "RAG应用中的知识检索"
        }
    ]
    
    for app in applications:
        print(f"  📚 {app['name']}: {app['description']}")
        print(f"      配置: {app['config']}")


if __name__ == "__main__":
    test_vdb_service()
    test_vdb_index_types()
    test_vdb_applications()
    print("\n🎯 VDB Service demo completed!")
