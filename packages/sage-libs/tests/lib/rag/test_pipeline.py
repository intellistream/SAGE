"""
测试 sage.libs.rag.pipeline 模块
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# 尝试导入pipeline模块
pytest_plugins = []

try:
    from sage.libs.rag.pipeline import RAGPipeline
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Pipeline module not available: {e}")


@pytest.mark.unit
class TestRAGPipeline:
    """测试RAGPipeline类"""
    
    def test_rag_pipeline_import(self):
        """测试RAGPipeline导入"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        from sage.libs.rag.pipeline import RAGPipeline
        assert RAGPipeline is not None
    
    def test_rag_pipeline_initialization_empty(self):
        """测试RAGPipeline空初始化"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        pipeline = RAGPipeline()
        
        assert pipeline.retriever is None
        assert pipeline.generator is None
        assert pipeline.reranker is None
        assert pipeline.refiner is None
    
    def test_rag_pipeline_initialization_with_components(self):
        """测试RAGPipeline带组件初始化"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        # Mock各种组件
        mock_retriever = Mock()
        mock_generator = Mock()
        mock_reranker = Mock()
        mock_refiner = Mock()
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            generator=mock_generator,
            reranker=mock_reranker,
            refiner=mock_refiner
        )
        
        assert pipeline.retriever == mock_retriever
        assert pipeline.generator == mock_generator
        assert pipeline.reranker == mock_reranker
        assert pipeline.refiner == mock_refiner
    
    def test_run_with_all_components(self):
        """测试run方法使用所有组件"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        # Mock各种组件
        mock_retriever = Mock()
        mock_generator = Mock()
        mock_reranker = Mock()
        mock_refiner = Mock()
        
        # 配置mock行为
        mock_documents = [
            {"content": "Document 1", "score": 0.9},
            {"content": "Document 2", "score": 0.8}
        ]
        mock_retriever.retrieve.return_value = mock_documents
        
        mock_reranked_docs = [
            {"content": "Document 1", "score": 0.95},
            {"content": "Document 2", "score": 0.85}
        ]
        mock_reranker.rerank.return_value = mock_reranked_docs
        
        refined_query = "refined query"
        refined_docs = [{"content": "Refined Document 1", "score": 0.95}]
        mock_refiner.refine.return_value = (refined_query, refined_docs)
        
        mock_response = "Generated response"
        mock_generator.generate.return_value = mock_response
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            generator=mock_generator,
            reranker=mock_reranker,
            refiner=mock_refiner
        )
        
        # 执行pipeline
        query = "What is machine learning?"
        result = pipeline.run(query)
        
        # 验证组件调用
        mock_retriever.retrieve.assert_called_once_with(query)
        mock_reranker.rerank.assert_called_once_with(query, mock_documents)
        mock_refiner.refine.assert_called_once_with(query, mock_reranked_docs)
        mock_generator.generate.assert_called_once_with(refined_query, refined_docs)
        
        # 验证结果
        assert isinstance(result, dict)
        assert result["query"] == refined_query
        assert result["documents"] == refined_docs
        assert result["response"] == mock_response
    
    def test_run_with_only_generator(self):
        """测试run方法只使用generator"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        # 只有generator
        mock_generator = Mock()
        mock_response = "Generated response without retrieval"
        mock_generator.generate.return_value = mock_response
        
        pipeline = RAGPipeline(generator=mock_generator)
        
        # 执行pipeline
        query = "What is AI?"
        result = pipeline.run(query)
        
        # 验证generator被调用时documents为空列表
        mock_generator.generate.assert_called_once_with(query, [])
        
        # 验证结果
        assert result["query"] == query
        assert result["documents"] == []
        assert result["response"] == mock_response
    
    def test_run_without_generator(self):
        """测试run方法没有generator"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        # 只有retriever，没有generator
        mock_retriever = Mock()
        mock_documents = [{"content": "Document 1", "score": 0.9}]
        mock_retriever.retrieve.return_value = mock_documents
        
        pipeline = RAGPipeline(retriever=mock_retriever)
        
        # 执行pipeline
        query = "What is deep learning?"
        result = pipeline.run(query)
        
        # 验证结果
        assert result["query"] == query
        assert result["documents"] == mock_documents
        assert result["response"] == "No generator configured"
    
    def test_run_with_retriever_and_generator_only(self):
        """测试run方法只使用retriever和generator"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        # 只有retriever和generator
        mock_retriever = Mock()
        mock_generator = Mock()
        
        mock_documents = [{"content": "Retrieved document", "score": 0.9}]
        mock_retriever.retrieve.return_value = mock_documents
        
        mock_response = "Generated from retrieved docs"
        mock_generator.generate.return_value = mock_response
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            generator=mock_generator
        )
        
        # 执行pipeline
        query = "Explain neural networks"
        result = pipeline.run(query)
        
        # 验证调用
        mock_retriever.retrieve.assert_called_once_with(query)
        mock_generator.generate.assert_called_once_with(query, mock_documents)
        
        # 验证结果
        assert result["query"] == query
        assert result["documents"] == mock_documents
        assert result["response"] == mock_response
    
    def test_run_with_reranker_without_documents(self):
        """测试run方法有reranker但没有文档"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        # 有reranker但retriever返回空文档
        mock_retriever = Mock()
        mock_reranker = Mock()
        mock_generator = Mock()
        
        mock_retriever.retrieve.return_value = []  # 空文档列表
        mock_generator.generate.return_value = "Response without docs"
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            reranker=mock_reranker,
            generator=mock_generator
        )
        
        # 执行pipeline
        query = "Test query"
        result = pipeline.run(query)
        
        # 验证reranker没有被调用（因为没有文档）
        mock_retriever.retrieve.assert_called_once_with(query)
        mock_reranker.rerank.assert_not_called()
        mock_generator.generate.assert_called_once_with(query, [])
        
        # 验证结果
        assert result["documents"] == []
    
    def test_run_with_kwargs(self):
        """测试run方法传递额外参数"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        mock_retriever = Mock()
        mock_generator = Mock()
        
        mock_documents = [{"content": "Document", "score": 0.9}]
        mock_retriever.retrieve.return_value = mock_documents
        mock_generator.generate.return_value = "Response"
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            generator=mock_generator
        )
        
        # 执行pipeline带额外参数
        query = "Test query"
        result = pipeline.run(query, top_k=5, temperature=0.7)
        
        # 验证参数传递
        mock_retriever.retrieve.assert_called_once_with(query, top_k=5, temperature=0.7)
        mock_generator.generate.assert_called_once_with(query, mock_documents, top_k=5, temperature=0.7)
    
    def test_run_with_refiner_but_no_reranker(self):
        """测试run方法有refiner但没有reranker"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        mock_retriever = Mock()
        mock_refiner = Mock()
        mock_generator = Mock()
        
        mock_documents = [{"content": "Original document", "score": 0.8}]
        mock_retriever.retrieve.return_value = mock_documents
        
        refined_query = "refined query"
        refined_docs = [{"content": "Refined document", "score": 0.9}]
        mock_refiner.refine.return_value = (refined_query, refined_docs)
        
        mock_generator.generate.return_value = "Refined response"
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            refiner=mock_refiner,
            generator=mock_generator
        )
        
        # 执行pipeline
        query = "Original query"
        result = pipeline.run(query)
        
        # 验证调用序列
        mock_retriever.retrieve.assert_called_once_with(query)
        mock_refiner.refine.assert_called_once_with(query, mock_documents)
        mock_generator.generate.assert_called_once_with(refined_query, refined_docs)
        
        # 验证结果使用refined内容
        assert result["query"] == refined_query
        assert result["documents"] == refined_docs


@pytest.mark.unit
class TestRAGPipelineErrorHandling:
    """测试RAGPipeline错误处理"""
    
    def test_run_with_retriever_error(self):
        """测试retriever出错的情况"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        mock_retriever = Mock()
        mock_generator = Mock()
        
        # Mock retriever抛出异常
        mock_retriever.retrieve.side_effect = Exception("Retrieval failed")
        mock_generator.generate.return_value = "Fallback response"
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            generator=mock_generator
        )
        
        # 验证异常传播
        with pytest.raises(Exception) as exc_info:
            pipeline.run("Test query")
        
        assert "Retrieval failed" in str(exc_info.value)
    
    def test_run_with_generator_error(self):
        """测试generator出错的情况"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        mock_retriever = Mock()
        mock_generator = Mock()
        
        mock_documents = [{"content": "Document", "score": 0.9}]
        mock_retriever.retrieve.return_value = mock_documents
        
        # Mock generator抛出异常
        mock_generator.generate.side_effect = Exception("Generation failed")
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            generator=mock_generator
        )
        
        # 验证异常传播
        with pytest.raises(Exception) as exc_info:
            pipeline.run("Test query")
        
        assert "Generation failed" in str(exc_info.value)
    
    def test_run_with_reranker_error(self):
        """测试reranker出错的情况"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        mock_retriever = Mock()
        mock_reranker = Mock()
        mock_generator = Mock()
        
        mock_documents = [{"content": "Document", "score": 0.9}]
        mock_retriever.retrieve.return_value = mock_documents
        
        # Mock reranker抛出异常
        mock_reranker.rerank.side_effect = Exception("Reranking failed")
        mock_generator.generate.return_value = "Response"
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            reranker=mock_reranker,
            generator=mock_generator
        )
        
        # 验证异常传播
        with pytest.raises(Exception) as exc_info:
            pipeline.run("Test query")
        
        assert "Reranking failed" in str(exc_info.value)
    
    def test_run_with_refiner_error(self):
        """测试refiner出错的情况"""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline module not available")
        
        mock_retriever = Mock()
        mock_refiner = Mock()
        mock_generator = Mock()
        
        mock_documents = [{"content": "Document", "score": 0.9}]
        mock_retriever.retrieve.return_value = mock_documents
        
        # Mock refiner抛出异常
        mock_refiner.refine.side_effect = Exception("Refinement failed")
        mock_generator.generate.return_value = "Response"
        
        pipeline = RAGPipeline(
            retriever=mock_retriever,
            refiner=mock_refiner,
            generator=mock_generator
        )
        
        # 验证异常传播
        with pytest.raises(Exception) as exc_info:
            pipeline.run("Test query")
        
        assert "Refinement failed" in str(exc_info.value)


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """RAGPipeline集成测试"""
    
    @pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline module not available")
    def test_complete_rag_pipeline_simulation(self):
        """测试完整RAG pipeline模拟"""
        
        # 创建真实的mock组件来模拟完整流程
        class MockRetriever:
            def retrieve(self, query, **kwargs):
                # 模拟基于查询返回相关文档
                if "machine learning" in query.lower():
                    return [
                        {"content": "Machine learning is a subset of AI", "score": 0.9},
                        {"content": "ML algorithms learn from data", "score": 0.8},
                        {"content": "Deep learning uses neural networks", "score": 0.7}
                    ]
                return [{"content": "Generic document", "score": 0.5}]
        
        class MockReranker:
            def rerank(self, query, documents, **kwargs):
                # 模拟重排序 - 简单按分数排序
                sorted_docs = sorted(documents, key=lambda x: x["score"], reverse=True)
                # 添加rerank分数
                for i, doc in enumerate(sorted_docs):
                    doc["rerank_score"] = doc["score"] + 0.05 - i * 0.01
                return sorted_docs[:2]  # 返回top 2
        
        class MockRefiner:
            def refine(self, query, documents, **kwargs):
                # 模拟查询精化和文档处理
                refined_query = f"Refined: {query}"
                refined_docs = []
                for doc in documents:
                    refined_doc = doc.copy()
                    refined_doc["content"] = f"[Refined] {doc['content']}"
                    refined_docs.append(refined_doc)
                return refined_query, refined_docs
        
        class MockGenerator:
            def generate(self, query, documents, **kwargs):
                # 模拟基于文档生成回答
                doc_contents = [doc["content"] for doc in documents]
                context = " | ".join(doc_contents)
                return f"Answer to '{query}' based on: {context}"
        
        # 创建pipeline
        pipeline = RAGPipeline(
            retriever=MockRetriever(),
            reranker=MockReranker(),
            refiner=MockRefiner(),
            generator=MockGenerator()
        )
        
        # 执行测试
        query = "What is machine learning?"
        result = pipeline.run(query)
        
        # 验证完整结果
        assert isinstance(result, dict)
        assert "query" in result
        assert "documents" in result
        assert "response" in result
        
        # 验证查询被精化
        assert result["query"] == "Refined: What is machine learning?"
        
        # 验证文档被处理
        assert len(result["documents"]) == 2  # reranker限制为top 2
        for doc in result["documents"]:
            assert "[Refined]" in doc["content"]
            assert "rerank_score" in doc
        
        # 验证响应包含精化后的内容
        assert "Refined: What is machine learning?" in result["response"]
        assert "[Refined]" in result["response"]
    
    @pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline module not available")
    def test_minimal_pipeline_simulation(self):
        """测试最小化pipeline模拟（只有generator）"""
        
        class SimpleGenerator:
            def generate(self, query, documents, **kwargs):
                if documents:
                    return f"Generated answer for '{query}' using {len(documents)} documents"
                else:
                    return f"Generated answer for '{query}' without context"
        
        pipeline = RAGPipeline(generator=SimpleGenerator())
        
        result = pipeline.run("Simple question")
        
        # 验证最小pipeline结果
        assert result["query"] == "Simple question"
        assert result["documents"] == []
        assert "without context" in result["response"]
    
    @pytest.mark.skipif(not PIPELINE_AVAILABLE, reason="Pipeline module not available")
    def test_pipeline_component_interaction(self):
        """测试pipeline组件间交互"""
        
        # 追踪组件调用顺序
        call_order = []
        
        class TrackedRetriever:
            def retrieve(self, query, **kwargs):
                call_order.append("retriever")
                return [{"content": f"Retrieved for: {query}", "score": 0.8}]
        
        class TrackedReranker:
            def rerank(self, query, documents, **kwargs):
                call_order.append("reranker")
                return documents  # 不改变顺序，只记录调用
        
        class TrackedRefiner:
            def refine(self, query, documents, **kwargs):
                call_order.append("refiner")
                return query, documents  # 不改变内容，只记录调用
        
        class TrackedGenerator:
            def generate(self, query, documents, **kwargs):
                call_order.append("generator")
                return "Final response"
        
        pipeline = RAGPipeline(
            retriever=TrackedRetriever(),
            reranker=TrackedReranker(),
            refiner=TrackedRefiner(),
            generator=TrackedGenerator()
        )
        
        pipeline.run("Test query")
        
        # 验证组件调用顺序
        expected_order = ["retriever", "reranker", "refiner", "generator"]
        assert call_order == expected_order
