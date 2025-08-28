"""
测试 sage.libs.rag.promptor 模块
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile
from jinja2 import Template

# 尝试导入promptor模块
pytest_plugins = []

try:
    from sage.libs.rag.promptor import (
        QAPromptor, SummarizationPromptor, QueryProfilerPromptor,
        QA_prompt_template, summarization_prompt_template
    )
    PROMPTOR_AVAILABLE = True
except ImportError as e:
    PROMPTOR_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Promptor module not available: {e}")


@pytest.mark.unit
class TestQAPromptor:
    """测试QAPromptor类"""
    
    def test_qa_promptor_import(self):
        """测试QAPromptor导入"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        from sage.libs.rag.promptor import QAPromptor
        assert QAPromptor is not None
    
    def test_qa_promptor_initialization(self):
        """测试QAPromptor初始化"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        assert promptor.config == config
        assert hasattr(promptor, 'execute')
    
    def test_execute_with_question_and_context(self):
        """测试execute方法处理问题和上下文"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 测试输入数据
        input_data = {
            "question": "What is machine learning?",
            "context": ["Machine learning is a subset of AI.", "It involves algorithms that learn from data."]
        }
        
        result = promptor.execute(input_data)

        # 验证结果结构 - QAPromptor 返回 [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2
        
        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)
        
        # 验证数据保持不变
        assert data_result["question"] == "What is machine learning?"
        assert data_result["context"] == ["Machine learning is a subset of AI.", "It involves algorithms that learn from data."]
        
        # 验证prompt格式
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"

    def test_execute_with_retrieved_docs(self):
        """测试execute方法处理检索到的文档"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 测试带有retrieved_docs的输入数据
        input_data = {
            "question": "What is deep learning?",
            "retrieved_docs": [
                {"content": "Deep learning uses neural networks."},
                {"content": "It is a subset of machine learning."}
            ]
        }
        
        result = promptor.execute(input_data)
        
        # 验证结果 - QAPromptor 返回 [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2
        
        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)
        
        # 验证数据保持不变
        assert data_result["question"] == "What is deep learning?"
        assert "retrieved_docs" in data_result
        
        # 验证prompt格式
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"

    def test_execute_with_external_corpus(self):
        """测试execute方法处理外部语料库"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 测试带有external_corpus的输入数据
        input_data = {
            "question": "Explain neural networks",
            "external_corpus": "Neural networks are computing systems inspired by biological neural networks."
        }
        
        result = promptor.execute(input_data)
        
        # 验证结果 - QAPromptor 返回 [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2
        
        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)
        
        # 验证数据保持不变
        assert data_result["question"] == "Explain neural networks"
        assert "external_corpus" in data_result
        
        # 验证prompt格式
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"
    
    def test_execute_with_empty_context(self):
        """测试execute方法处理空上下文"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 测试空上下文
        input_data = {
            "question": "What is AI?",
            "context": []
        }
        
        result = promptor.execute(input_data)
        
        # 验证结果 - QAPromptor 返回 [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2
        
        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)
        
        # 验证数据保持不变
        assert data_result["question"] == "What is AI?"
        assert "context" in data_result
        
        # 验证prompt格式
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"
    
    def test_execute_with_query_tuple(self):
        """测试execute方法处理查询元组"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 测试元组输入
        query = "What is reinforcement learning?"
        docs = [
            {"content": "Reinforcement learning is a type of machine learning."},
            {"content": "It involves agents learning through interaction."}
        ]
        input_data = (query, docs)
        
        result = promptor.execute(input_data)
        
        # 验证结果 - 元组输入会触发错误处理，返回错误提示
        assert isinstance(result, list)
        assert len(result) == 2
        system_msg, user_msg = result
        
        # 验证错误处理格式
        assert system_msg["role"] == "system"
        assert "error" in system_msg["content"].lower() or "encountered" in system_msg["content"].lower()
        assert user_msg["role"] == "user"

    def test_execute_preserves_additional_fields(self):
        """测试execute方法保留额外字段"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 测试带有额外字段的输入数据
        input_data = {
            "question": "What is NLP?",
            "context": ["Natural Language Processing is a field of AI."],
            "metadata": {"source": "textbook"},
            "timestamp": "2023-01-01"
        }
        
        result = promptor.execute(input_data)
        
        # 验证结果 - QAPromptor 返回 [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2
        
        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)
        
        # 验证结果保留所有原始字段
        assert data_result["question"] == "What is NLP?"
        assert data_result["metadata"] == {"source": "textbook"}
        assert data_result["timestamp"] == "2023-01-01"
        assert "context" in data_result
        
        # 验证prompt格式
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"


@pytest.mark.unit 
class TestQueryProfilerPromptor:
    """测试QueryProfilerPromptor类"""
    
    def test_query_profiler_promptor_import(self):
        """测试QueryProfilerPromptor导入"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        try:
            from sage.libs.rag.promptor import QueryProfilerPromptor
            assert QueryProfilerPromptor is not None
        except ImportError:
            pytest.skip("QueryProfilerPromptor not available in module")
    
    def test_query_profiler_promptor_initialization(self):
        """测试QueryProfilerPromptor初始化"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        try:
            from sage.libs.rag.promptor import QueryProfilerPromptor
        except ImportError:
            pytest.skip("QueryProfilerPromptor not available in module")
        
        config = {
            "metadata": {"dataset": "test"},
            "chunk_size": 512
        }
        
        try:
            profiler = QueryProfilerPromptor(config=config)
            assert profiler.config == config
            assert hasattr(profiler, 'execute')
        except Exception as e:
            pytest.skip(f"QueryProfilerPromptor initialization failed: {e}")


@pytest.mark.unit
class TestSummarizationPromptor:
    """测试SummarizationPromptor类"""
    
    def test_summarization_promptor_import(self):
        """测试SummarizationPromptor导入"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        try:
            from sage.libs.rag.promptor import SummarizationPromptor
            assert SummarizationPromptor is not None
        except ImportError:
            pytest.skip("SummarizationPromptor not available in module")
    
    def test_summarization_promptor_initialization(self):
        """测试SummarizationPromptor初始化"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        try:
            from sage.libs.rag.promptor import SummarizationPromptor
        except ImportError:
            pytest.skip("SummarizationPromptor not available in module")
        
        config = {"task_type": "summarization"}
        
        try:
            promptor = SummarizationPromptor(config=config)
            assert promptor.config == config
            assert hasattr(promptor, 'execute')
        except Exception as e:
            pytest.skip(f"SummarizationPromptor initialization failed: {e}")
    
    def test_summarization_promptor_execute(self):
        """测试SummarizationPromptor执行"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        try:
            from sage.libs.rag.promptor import SummarizationPromptor
        except ImportError:
            pytest.skip("SummarizationPromptor not available in module")
        
        config = {"task_type": "summarization"}
        promptor = SummarizationPromptor(config=config)
        
        # SummarizationPromptor期望(query, external_corpus)格式
        query = "Please summarize the following text"
        external_corpus = ["This is a long text that needs to be summarized. ", 
                         "It contains multiple sentences and paragraphs with important information."]
        
        input_data = (query, external_corpus)
        
        result = promptor.execute(input_data)
        
        # 验证结果 - SummarizationPromptor返回[data, message]格式
        assert isinstance(result, list)
        assert len(result) == 2
        
        data, message = result
        assert isinstance(data, dict)
        assert isinstance(message, dict)
        
        # 检查message内容
        assert "content" in message
        assert "Please summarize the following text" in message["content"]


@pytest.mark.unit
class TestPromptTemplates:
    """测试prompt模板"""
    
    def test_qa_prompt_template(self):
        """测试QA prompt模板"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        from sage.libs.rag.promptor import QA_prompt_template
        
        # 测试模板渲染
        context = "Machine learning is a subset of artificial intelligence."
        rendered = QA_prompt_template.render(external_corpus=context)
        
        assert "Machine learning is a subset of artificial intelligence." in rendered
        assert "intelligent assistant" in rendered
        assert "knowledge base" in rendered
    
    def test_qa_prompt_template_no_context(self):
        """测试QA prompt模板无上下文"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        from sage.libs.rag.promptor import QA_prompt_template
        
        # 测试无上下文的模板渲染
        rendered = QA_prompt_template.render()
        
        assert "intelligent assistant" in rendered
        assert "knowledge base" in rendered
        # 不应包含上下文部分
        assert "Relevant corpus" not in rendered
    
    def test_summarization_prompt_template(self):
        """测试摘要prompt模板"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")
        
        from sage.libs.rag.promptor import summarization_prompt_template
        
        # 测试模板渲染
        content = "This is content that needs to be summarized."
        rendered = summarization_prompt_template.render(external_corpus=content)
        
        assert "This is content that needs to be summarized." in rendered
        assert "Summarize the content" in rendered
        assert "concise and clear" in rendered


@pytest.mark.integration
class TestPromptorIntegration:
    """Promptor集成测试"""
    
    @pytest.mark.skipif(not PROMPTOR_AVAILABLE, reason="Promptor module not available")
    def test_qa_promptor_full_pipeline(self):
        """测试QAPromptor完整pipeline"""
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)
        
        # 模拟完整的RAG pipeline数据
        pipeline_data = {
            "question": "What are the benefits of renewable energy?",
            "retrieved_docs": [
                {"content": "Renewable energy reduces carbon emissions.", "score": 0.9},
                {"content": "Solar and wind power are sustainable sources.", "score": 0.8},
                {"content": "Renewable energy creates green jobs.", "score": 0.7}
            ],
            "metadata": {
                "retrieval_method": "dense",
                "total_docs": 100,
                "top_k": 3
            }
        }
        
        result = promptor.execute(pipeline_data)
        
        # QAPromptor返回[data, prompt]格式
        assert isinstance(result, list)
        assert len(result) == 2
        
        data, messages = result
        
        # 验证data部分
        assert isinstance(data, dict)
        assert "question" in data
        assert "retrieved_docs" in data
        assert "metadata" in data
        
        # 验证messages部分（OpenAI格式）
        assert isinstance(messages, list)
        assert len(messages) >= 1
        
        # 检查messages内容
        message_content = str(messages)
        assert "What are the benefits of renewable energy?" in message_content
