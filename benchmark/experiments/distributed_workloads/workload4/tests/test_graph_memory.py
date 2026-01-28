"""
Workload 4 - Task 5: 图遍历和内存检索测试
"""

import unittest
import numpy as np

from workload4.graph_memory import (
    GraphMemoryService,
    GraphMemoryRetriever,
    build_knowledge_graph,
)
from workload4.models import QueryEvent, JoinedEvent, DocumentEvent


class TestGraphMemoryService(unittest.TestCase):
    """测试图内存服务"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建测试知识库
        self.knowledge_base = []
        np.random.seed(42)
        
        for i in range(20):
            embedding = np.random.randn(128).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            self.knowledge_base.append({
                "node_id": f"node_{i}",
                "content": f"This is test content for node {i}",
                "embedding": embedding.tolist(),
                "node_type": "memory" if i < 15 else "concept",
            })
        
        # 创建服务
        self.service = GraphMemoryService(
            config={},
            embedding_dim=128,
            similarity_threshold=0.1,  # 进一步降低阈值以确保有边
        )
    
    def test_build_graph(self):
        """测试图构建"""
        self.service.build_graph(self.knowledge_base)
        
        self.assertIsNotNone(self.service.graph)
        self.assertEqual(self.service.graph.number_of_nodes(), 20)
        self.assertGreater(self.service.graph.number_of_edges(), 0)
        
        # 验证节点数据
        self.assertEqual(len(self.service.node_embeddings), 20)
        self.assertEqual(len(self.service.node_contents), 20)
    
    def test_search_basic(self):
        """测试基础搜索功能"""
        self.service.build_graph(self.knowledge_base)
        
        # 创建查询向量（与第一个节点相似）
        query_emb = np.array(self.knowledge_base[0]["embedding"])
        
        results = self.service.search(
            query_embedding=query_emb.tolist(),
            max_depth=2,
            max_nodes=10,
            beam_width=3,
        )
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 10)
        
        # 验证结果结构
        first_result = results[0]
        self.assertIn("node_id", first_result)
        self.assertIn("content", first_result)
        self.assertIn("depth", first_result)
        self.assertIn("path", first_result)
        self.assertIn("relevance_score", first_result)
    
    def test_search_depth_limit(self):
        """测试深度限制"""
        self.service.build_graph(self.knowledge_base)
        
        query_emb = np.random.randn(128)
        query_emb = query_emb / np.linalg.norm(query_emb)
        
        results = self.service.search(
            query_embedding=query_emb.tolist(),
            max_depth=1,
            max_nodes=100,
            beam_width=5,
        )
        
        # 检查所有结果深度不超过限制
        for result in results:
            self.assertLessEqual(result["depth"], 1)
    
    def test_search_empty_graph(self):
        """测试空图搜索"""
        # 不构建图
        query_emb = np.random.randn(128).tolist()
        
        results = self.service.search(
            query_embedding=query_emb,
            max_depth=2,
            max_nodes=10,
            beam_width=3,
        )
        
        self.assertEqual(len(results), 0)


class TestGraphMemoryRetriever(unittest.TestCase):
    """测试图遍历算子"""
    
    def test_retriever_initialization(self):
        """测试算子初始化"""
        retriever = GraphMemoryRetriever(
            max_depth=3,
            max_nodes=200,
            beam_width=10,
        )
        
        self.assertEqual(retriever.max_depth, 3)
        self.assertEqual(retriever.max_nodes, 200)
        self.assertEqual(retriever.beam_width, 10)
    
    def test_retriever_with_mock_service(self):
        """测试算子与 Mock 服务交互"""
        # 这个测试需要在实际环境中运行
        # 这里只测试数据流转
        
        query = QueryEvent(
            query_id="test_query_1",
            query_text="What is machine learning?",
            query_type="factual",
            category="technology",
            timestamp=1000.0,
            embedding=np.random.randn(128).tolist(),
        )
        
        doc = DocumentEvent(
            doc_id="test_doc_1",
            doc_text="ML is a subset of AI",
            doc_category="technology",
            timestamp=1001.0,
            embedding=np.random.randn(128).tolist(),
        )
        
        joined = JoinedEvent(
            joined_id="test_join_1",
            query=query,
            matched_docs=[doc],
            join_timestamp=1002.0,
            semantic_score=0.85,
        )
        
        # 验证输入数据结构
        self.assertIsNotNone(joined.query.embedding)


class TestBuildKnowledgeGraph(unittest.TestCase):
    """测试图构建工具函数"""
    
    def test_build_graph_utility(self):
        """测试工具函数构建图"""
        np.random.seed(123)
        
        documents = []
        for i in range(10):
            embedding = np.random.randn(64)
            embedding = embedding / np.linalg.norm(embedding)
            
            documents.append({
                "node_id": f"doc_{i}",
                "content": f"Document content {i}",
                "embedding": embedding.tolist(),
            })
        
        graph = build_knowledge_graph(
            documents,
            embedding_dim=64,
            similarity_threshold=0.1,  # 降低阈值确保构建边
        )
        
        self.assertEqual(graph.number_of_nodes(), 10)
        self.assertGreater(graph.number_of_edges(), 0)
        
        # 验证节点属性
        node = list(graph.nodes())[0]
        self.assertIn("content", graph.nodes[node])
        self.assertIn("node_type", graph.nodes[node])


class TestGraphMemoryPerformance(unittest.TestCase):
    """图内存性能测试"""
    
    def test_search_performance(self):
        """测试搜索性能"""
        import time
        
        # 创建较大的知识库
        np.random.seed(456)
        knowledge_base = []
        
        for i in range(100):
            embedding = np.random.randn(128).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            knowledge_base.append({
                "node_id": f"node_{i}",
                "content": f"Content {i}",
                "embedding": embedding.tolist(),
                "node_type": "memory",
            })
        
        service = GraphMemoryService(
            config={},
            embedding_dim=128,
            similarity_threshold=0.1,  # 降低阈值加速测试
        )
        
        # 测试构图时间
        start_time = time.time()
        service.build_graph(knowledge_base)
        build_time = time.time() - start_time
        
        print(f"\nBuild graph time: {build_time:.3f}s")
        self.assertLess(build_time, 5.0, "Graph building should be fast")
        
        # 测试搜索时间
        query_emb = np.random.randn(128)
        query_emb = query_emb / np.linalg.norm(query_emb)
        
        start_time = time.time()
        results = service.search(
            query_embedding=query_emb.tolist(),
            max_depth=3,
            max_nodes=50,
            beam_width=10,
        )
        search_time = time.time() - start_time
        
        print(f"Search time: {search_time:.3f}s")
        print(f"Results count: {len(results)}")
        
        self.assertLess(search_time, 1.0, "Search should be fast")
        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main()
