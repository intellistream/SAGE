"""
Tests for NodeRegistry - Studio to SAGE Operator mapping
"""

import pytest
from sage.studio.services.node_registry import (
    NodeRegistry,  # type: ignore[import-not-found]
)


class TestNodeRegistry:
    """测试 NodeRegistry 功能"""

    def test_registry_initialization(self):
        """测试 Registry 初始化"""
        registry = NodeRegistry()

        # 验证 Registry 已注册所有基本节点类型
        types = registry.list_types()
        assert len(types) > 0
        assert "map" in types  # Generic map operator always registered

        # RAG operators may be registered if dependencies available
        # We don't assert their presence to avoid test failures when deps missing

    def test_get_rag_operators(self):
        """测试获取 RAG 相关的 Operator"""
        registry = NodeRegistry()

        # Test if RAG operators are available (depends on sage-middleware installation)
        retriever_cls = registry.get_operator("retriever")
        if retriever_cls is not None:
            # ChromaRetriever should be the default
            assert "Retriever" in retriever_cls.__name__

        generator_cls = registry.get_operator("generator")
        if generator_cls is not None:
            # OpenAIGenerator should be the default
            assert "Generator" in generator_cls.__name__

        promptor_cls = registry.get_operator("promptor")
        if promptor_cls is not None:
            # QAPromptor should be the default
            assert "Promptor" in promptor_cls.__name__

    def test_get_specific_generators(self):
        """测试获取特定的 Generator Operator"""
        registry = NodeRegistry()

        # Test OpenAI Generator
        openai_cls = registry.get_operator("openai_generator")
        if openai_cls is not None:
            assert "OpenAI" in openai_cls.__name__

        # Test HuggingFace Generator
        hf_cls = registry.get_operator("hf_generator")
        if hf_cls is not None:
            assert "HF" in hf_cls.__name__ or "HuggingFace" in hf_cls.__name__

    def test_get_specific_retrievers(self):
        """测试获取特定的 Retriever Operator"""
        registry = NodeRegistry()

        # Test Chroma Retriever
        chroma_cls = registry.get_operator("chroma_retriever")
        if chroma_cls is not None:
            assert "Chroma" in chroma_cls.__name__

        # Test Milvus Retrievers
        milvus_dense_cls = registry.get_operator("milvus_dense_retriever")
        if milvus_dense_cls is not None:
            assert "Milvus" in milvus_dense_cls.__name__

    def test_get_unknown_operator(self):
        """测试获取不存在的节点类型"""
        registry = NodeRegistry()

        # 不存在的类型应该返回 None
        result = registry.get_operator("unknown_type")
        assert result is None

    def test_list_types(self):
        """测试列出所有节点类型"""
        registry = NodeRegistry()

        types = registry.list_types()
        assert isinstance(types, list)
        assert len(types) > 0

        # 验证返回的是排序后的列表
        assert types == sorted(types)

    def test_register_custom_operator(self):
        """测试注册自定义 Operator"""
        from sage.kernel.operators import MapOperator

        class CustomOperator(MapOperator):
            """自定义测试 Operator"""

            def map_function(self, item):
                return {"custom": "data"}

        registry = NodeRegistry()

        # 注册自定义节点类型
        registry.register("custom_node", CustomOperator)

        # 验证可以获取到
        custom_cls = registry.get_operator("custom_node")
        assert custom_cls is CustomOperator

        # 验证出现在类型列表中
        types = registry.list_types()
        assert "custom_node" in types

    def test_register_duplicate_type(self):
        """测试注册重复的节点类型"""
        from sage.kernel.operators import MapOperator

        class FirstOperator(MapOperator):
            def map_function(self, item):
                return {"first": True}

        class SecondOperator(MapOperator):
            def map_function(self, item):
                return {"second": True}

        registry = NodeRegistry()

        # 注册第一个
        registry.register("test_type", FirstOperator)

        # 注册第二个（应该覆盖）
        registry.register("test_type", SecondOperator)

        # 验证获取到的是第二个
        result_cls = registry.get_operator("test_type")
        assert result_cls is SecondOperator


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
