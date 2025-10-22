"""
Tests for NodeRegistry - Studio to SAGE Operator mapping
"""
import pytest

from sage.studio.services.node_registry import NodeRegistry


class TestNodeRegistry:
    """测试 NodeRegistry 功能"""
    
    def test_registry_initialization(self):
        """测试 Registry 初始化"""
        registry = NodeRegistry()
        
        # 验证 Registry 已注册所有基本节点类型
        types = registry.list_types()
        assert len(types) > 0
        assert "retriever" in types
        assert "generator" in types
        assert "promptor" in types
    
    def test_get_rag_operators(self):
        """测试获取 RAG 相关的 Operator"""
        registry = NodeRegistry()
        
        # 测试 Retriever
        retriever_cls = registry.get_operator("retriever")
        assert retriever_cls is not None
        assert retriever_cls.__name__ == "RetrieverOperator"
        
        # 测试 Generator
        generator_cls = registry.get_operator("generator")
        assert generator_cls is not None
        assert generator_cls.__name__ == "GeneratorOperator"
        
        # 测试 Promptor
        promptor_cls = registry.get_operator("promptor")
        assert promptor_cls is not None
        assert promptor_cls.__name__ == "PromptorOperator"
    
    def test_get_llm_operators(self):
        """测试获取 LLM 相关的 Operator"""
        registry = NodeRegistry()
        
        # 测试 vLLM
        vllm_cls = registry.get_operator("vllm")
        assert vllm_cls is not None
        # vLLM 应该是 GeneratorOperator
        assert vllm_cls.__name__ == "GeneratorOperator"
        
        # 测试 OpenAI
        openai_cls = registry.get_operator("openai")
        assert openai_cls is not None
    
    def test_get_io_operators(self):
        """测试获取 I/O 相关的 Operator"""
        registry = NodeRegistry()
        
        # 测试 FileSource
        file_source_cls = registry.get_operator("file_source")
        assert file_source_cls is not None
        
        # 测试 PrintSink
        print_sink_cls = registry.get_operator("print_sink")
        assert print_sink_cls is not None
    
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
        from sage.libs.operators import MapOperator
        
        class CustomOperator(MapOperator):
            """自定义测试 Operator"""
            def process_item(self, item, context):
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
        from sage.libs.operators import MapOperator
        
        class FirstOperator(MapOperator):
            def process_item(self, item, context):
                return {"first": True}
        
        class SecondOperator(MapOperator):
            def process_item(self, item, context):
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
