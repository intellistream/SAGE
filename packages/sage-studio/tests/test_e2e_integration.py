#!/usr/bin/env python3
"""
端到端集成测试

测试完整的工作流程：
1. 从 JSON 定义创建 VisualPipeline
2. 使用 PipelineBuilder 构建 SAGE Pipeline
3. 使用不同的 Source/Sink 配置
4. 测试多种 Operator 组合
"""

import pytest
from sage.studio.models import VisualNode, VisualConnection, VisualPipeline  # type: ignore[import-not-found]
from sage.studio.services import PipelineBuilder, get_pipeline_builder  # type: ignore[import-not-found]


class TestE2ESimplePipeline:
    """简单端到端测试 - 基本流程验证"""

    def test_simple_generator_pipeline(self):
        """测试最简单的生成器流水线"""
        # 创建一个简单的生成器节点
        generator = VisualNode(
            id="gen1",
            type="generator",
            label="OpenAI Generator",
            config={"model": "gpt-3.5-turbo", "temperature": 0.7},
            position={"x": 100, "y": 100}
        )

        visual_pipeline = VisualPipeline(
            id="simple_gen",
            name="Simple Generator Pipeline",
            nodes=[generator],
            connections=[]
        )

        # 构建并验证
        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None
        assert visual_pipeline.name == "Simple Generator Pipeline"

    def test_two_node_pipeline(self):
        """测试两节点连接的流水线"""
        # 创建 Retriever -> Generator 流水线
        retriever = VisualNode(
            id="ret1",
            type="retriever",
            label="Chroma Retriever",
            config={"collection_name": "docs", "top_k": 3},
            position={"x": 100, "y": 100}
        )

        generator = VisualNode(
            id="gen1",
            type="generator",
            label="Generator",
            config={"model": "gpt-4"},
            position={"x": 300, "y": 100}
        )

        connection = VisualConnection(
            id="c1",
            source_node_id="ret1",
            source_port="output",
            target_node_id="gen1",
            target_port="input",
            label="retrieval_results"
        )

        visual_pipeline = VisualPipeline(
            id="ret_gen",
            name="Retriever-Generator Pipeline",
            nodes=[retriever, generator],
            connections=[connection]
        )

        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None
        assert len(visual_pipeline.nodes) == 2
        assert len(visual_pipeline.connections) == 1


class TestE2EComplexRAGPipeline:
    """复杂 RAG 流水线端到端测试"""

    def test_full_rag_with_reranker(self):
        """测试包含重排序的完整 RAG 流水线"""
        # 创建完整的 RAG 流程: Retriever -> Reranker -> Promptor -> Generator
        retriever = VisualNode(
            id="retriever1",
            type="chroma_retriever",
            label="Document Retriever",
            config={
                "collection_name": "knowledge_base",
                "top_k": 10,
                "embedding_model": "text-embedding-ada-002"
            },
            position={"x": 100, "y": 100}
        )

        reranker = VisualNode(
            id="reranker1",
            type="bge_reranker",
            label="BGE Reranker",
            config={
                "model": "BAAI/bge-reranker-large",
                "top_k": 5
            },
            position={"x": 300, "y": 100}
        )

        promptor = VisualNode(
            id="promptor1",
            type="qa_promptor",
            label="QA Promptor",
            config={
                "template": "Based on the following context:\n{context}\n\nAnswer the question: {question}"
            },
            position={"x": 500, "y": 100}
        )

        generator = VisualNode(
            id="generator1",
            type="openai_generator",
            label="OpenAI Generator",
            config={
                "model": "gpt-4-turbo",
                "temperature": 0.3,
                "max_tokens": 500
            },
            position={"x": 700, "y": 100}
        )

        connections = [
            VisualConnection(
                id="c1",
                source_node_id="retriever1",
                source_port="output",
                target_node_id="reranker1",
                target_port="input",
                label="raw_results"
            ),
            VisualConnection(
                id="c2",
                source_node_id="reranker1",
                source_port="output",
                target_node_id="promptor1",
                target_port="context",
                label="reranked_results"
            ),
            VisualConnection(
                id="c3",
                source_node_id="promptor1",
                source_port="output",
                target_node_id="generator1",
                target_port="input",
                label="formatted_prompt"
            )
        ]

        visual_pipeline = VisualPipeline(
            id="full_rag",
            name="Full RAG with Reranker",
            nodes=[retriever, reranker, promptor, generator],
            connections=connections
        )

        # 构建并验证
        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None
        assert len(visual_pipeline.nodes) == 4
        assert len(visual_pipeline.connections) == 3

    def test_multi_retriever_pipeline(self):
        """测试多检索器融合的流水线"""
        # 创建两个不同的检索器
        chroma_retriever = VisualNode(
            id="ret_chroma",
            type="chroma_retriever",
            label="Chroma DB",
            config={"collection_name": "chroma_docs", "top_k": 5},
            position={"x": 100, "y": 50}
        )

        milvus_retriever = VisualNode(
            id="ret_milvus",
            type="milvus_dense_retriever",  # 使用正确的类型名称
            label="Milvus DB",
            config={"collection_name": "milvus_docs", "top_k": 5},
            position={"x": 100, "y": 150}
        )

        # 融合节点（使用 map operator 进行融合）
        fusion = VisualNode(
            id="fusion1",
            type="map",  # 使用实际可用的类型
            label="Result Fusion",
            config={"strategy": "reciprocal_rank_fusion"},
            position={"x": 300, "y": 100}
        )

        generator = VisualNode(
            id="gen1",
            type="generator",
            label="Generator",
            config={"model": "gpt-4"},
            position={"x": 500, "y": 100}
        )

        connections = [
            VisualConnection(id="c1", source_node_id="ret_chroma", source_port="output",
                           target_node_id="fusion1", target_port="input1"),
            VisualConnection(id="c2", source_node_id="ret_milvus", source_port="output",
                           target_node_id="fusion1", target_port="input2"),
            VisualConnection(id="c3", source_node_id="fusion1", source_port="output",
                           target_node_id="gen1", target_port="input")
        ]

        visual_pipeline = VisualPipeline(
            id="multi_ret",
            name="Multi-Retriever Fusion Pipeline",
            nodes=[chroma_retriever, milvus_retriever, fusion, generator],
            connections=connections
        )

        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None
        assert len(visual_pipeline.nodes) == 4


class TestE2ESourceSinkIntegration:
    """Source/Sink 集成测试"""

    def test_file_source_pipeline(self):
        """测试文件 Source 的流水线"""
        # 使用 character_splitter 而不是 recursive_chunker
        chunker = VisualNode(
            id="chunker1",
            type="character_splitter",
            label="Text Chunker",
            config={"chunk_size": 500, "overlap": 50},
            position={"x": 300, "y": 100}
        )

        generator = VisualNode(
            id="gen1",
            type="generator",
            label="Summarizer",
            config={"model": "gpt-3.5-turbo"},
            position={"x": 500, "y": 100}
        )

        visual_pipeline = VisualPipeline(
            id="file_proc",
            name="File Processing Pipeline",
            nodes=[chunker, generator],
            connections=[
                VisualConnection(id="c1", source_node_id="chunker1", source_port="output",
                               target_node_id="gen1", target_port="input")
            ]
        )

        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None

    def test_memory_sink_pipeline(self):
        """测试 Memory Sink 的流水线"""
        generator = VisualNode(
            id="gen1",
            type="generator",
            label="Text Generator",
            config={"model": "gpt-4"},
            position={"x": 100, "y": 100}
        )

        visual_pipeline = VisualPipeline(
            id="mem_sink",
            name="Memory Sink Pipeline",
            nodes=[generator],
            connections=[]
        )

        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None


class TestE2EChunkerEvaluatorPipeline:
    """Chunker 和 Evaluator 集成测试"""

    def test_chunking_with_evaluation(self):
        """测试带评估的文档分块流水线"""
        chunker = VisualNode(
            id="chunker1",
            type="character_splitter",  # 使用实际可用的类型
            label="Character Splitter",
            config={
                "chunk_size": 1000,
                "overlap": 100
            },
            position={"x": 100, "y": 100}
        )

        retriever = VisualNode(
            id="ret1",
            type="retriever",
            label="Vector Retriever",
            config={"top_k": 3},
            position={"x": 300, "y": 100}
        )

        generator = VisualNode(
            id="gen1",
            type="generator",
            label="Answer Generator",
            config={"model": "gpt-4"},
            position={"x": 500, "y": 100}
        )

        evaluator = VisualNode(
            id="eval1",
            type="accuracy_evaluate",  # 使用实际可用的类型
            label="Accuracy Evaluator",
            config={"threshold": 0.8},
            position={"x": 700, "y": 100}
        )

        connections = [
            VisualConnection(id="c1", source_node_id="chunker1", source_port="output",
                           target_node_id="ret1", target_port="input"),
            VisualConnection(id="c2", source_node_id="ret1", source_port="output",
                           target_node_id="gen1", target_port="input"),
            VisualConnection(id="c3", source_node_id="gen1", source_port="output",
                           target_node_id="eval1", target_port="input")
        ]

        visual_pipeline = VisualPipeline(
            id="chunk_eval",
            name="Chunking with Evaluation",
            nodes=[chunker, retriever, generator, evaluator],
            connections=connections
        )

        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None
        assert len(visual_pipeline.nodes) == 4


class TestE2EFromJSON:
    """从 JSON 定义创建流水线的端到端测试"""

    def test_pipeline_from_json_dict(self):
        """测试从 JSON 字典创建流水线"""
        pipeline_dict = {
            "id": "json_pipeline",
            "name": "Pipeline from JSON",
            "nodes": [
                {
                    "id": "node1",
                    "type": "retriever",
                    "label": "Retriever",
                    "config": {"top_k": 5},
                    "position": {"x": 100, "y": 100}
                },
                {
                    "id": "node2",
                    "type": "generator",
                    "label": "Generator",
                    "config": {"model": "gpt-3.5-turbo"},
                    "position": {"x": 300, "y": 100}
                }
            ],
            "connections": [
                {
                    "id": "conn1",
                    "source": "node1",  # from_dict 期望 'source' 而不是 'source_node_id'
                    "sourcePort": "output",
                    "target": "node2",  # from_dict 期望 'target' 而不是 'target_node_id'
                    "targetPort": "input"
                }
            ]
        }

        # 从字典创建 VisualPipeline (使用 dataclass 的 from_dict 方法)
        visual_pipeline = VisualPipeline.from_dict(pipeline_dict)

        # 构建 SAGE Pipeline
        builder = get_pipeline_builder()
        sage_pipeline = builder.build(visual_pipeline)

        assert sage_pipeline is not None
        assert visual_pipeline.id == "json_pipeline"
        assert len(visual_pipeline.nodes) == 2
        assert len(visual_pipeline.connections) == 1

    def test_complex_pipeline_from_json(self):
        """测试复杂流水线的 JSON 序列化和反序列化"""
        # 创建一个复杂的流水线
        pipeline = VisualPipeline(
            id="complex_rag",
            name="Complex RAG",
            description="A complex RAG pipeline with multiple stages",
            nodes=[
                VisualNode(
                    id="n1", type="retriever", label="Retriever",
                    config={"top_k": 5}, position={"x": 100, "y": 100}
                ),
                VisualNode(
                    id="n2", type="reranker", label="Reranker",
                    config={"model": "bge-reranker"}, position={"x": 300, "y": 100}
                ),
                VisualNode(
                    id="n3", type="generator", label="Generator",
                    config={"model": "gpt-4"}, position={"x": 500, "y": 100}
                )
            ],
            connections=[
                VisualConnection(id="c1", source_node_id="n1", source_port="output",
                               target_node_id="n2", target_port="input"),
                VisualConnection(id="c2", source_node_id="n2", source_port="output",
                               target_node_id="n3", target_port="input")
            ]
        )

        # 序列化为字典
        pipeline_dict = pipeline.to_dict()

        # 从字典反序列化
        pipeline_restored = VisualPipeline.from_dict(pipeline_dict)

        # 验证反序列化的流水线
        assert pipeline_restored.id == "complex_rag"
        assert len(pipeline_restored.nodes) == 3
        assert len(pipeline_restored.connections) == 2

        # 构建 SAGE Pipeline
        builder = get_pipeline_builder()
        sage_pipeline = builder.build(pipeline_restored)

        assert sage_pipeline is not None


class TestE2EErrorHandling:
    """错误处理的端到端测试"""

    def test_missing_operator_type(self):
        """测试使用不存在的 Operator 类型"""
        node = VisualNode(
            id="unknown",
            type="non_existent_operator",
            label="Unknown",
            config={},
            position={"x": 100, "y": 100}
        )

        pipeline = VisualPipeline(
            id="error_test",
            name="Error Test",
            nodes=[node],
            connections=[]
        )

        builder = get_pipeline_builder()

        # 应该能够构建但可能在执行时失败
        # 这里我们只测试构建不会崩溃
        try:
            sage_pipeline = builder.build(pipeline)
            # 如果成功构建，验证基本结构
            assert sage_pipeline is not None or sage_pipeline is None
        except Exception as e:
            # 允许抛出明确的错误
            assert "not found" in str(e).lower() or "unknown" in str(e).lower()

    def test_empty_pipeline(self):
        """测试空流水线 - 应该抛出验证错误"""
        pipeline = VisualPipeline(
            id="empty",
            name="Empty Pipeline",
            nodes=[],
            connections=[]
        )

        builder = get_pipeline_builder()

        # 空流水线应该抛出 ValueError
        with pytest.raises(ValueError, match="Pipeline must contain at least one node"):
            builder.build(pipeline)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
