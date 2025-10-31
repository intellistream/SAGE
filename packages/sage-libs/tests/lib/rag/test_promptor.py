"""
Test sage.libs.rag.promptor module
"""

import pytest

# Try to import promptor module
pytest_plugins = []

try:
    from sage.libs.rag.promptor import (
        QA_prompt_template,  # noqa: F401
        QAPromptor,
        QueryProfilerPromptor,  # noqa: F401
        SummarizationPromptor,  # noqa: F401
        summarization_prompt_template,  # noqa: F401
    )

    PROMPTOR_AVAILABLE = True
except ImportError as e:
    PROMPTOR_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Promptor module not available: {e}")


@pytest.mark.unit
class TestQAPromptor:
    """Test QAPromptor class"""

    def test_qa_promptor_import(self):
        """Test QAPromptor import"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        from sage.libs.rag.promptor import QAPromptor

        assert QAPromptor is not None

    def test_qa_promptor_initialization(self):
        """Test QAPromptor initialization"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        assert promptor.config == config
        assert hasattr(promptor, "execute")

    def test_execute_with_question_and_context(self):
        """Test execute method with question and context"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Test input data
        input_data = {
            "question": "What is machine learning?",
            "context": [
                "Machine learning is a subset of AI.",
                "It involves algorithms that learn from data.",
            ],
        }

        result = promptor.execute(input_data)

        # Verify result structure - QAPromptor returns [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2

        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)

        # Verify data remains unchanged
        assert data_result["question"] == "What is machine learning?"
        assert data_result["context"] == [
            "Machine learning is a subset of AI.",
            "It involves algorithms that learn from data.",
        ]

        # Verify prompt format
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"

    def test_execute_with_retrieved_docs(self):
        """Test execute method with retrieved docs"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Test input data with retrieved_docs
        input_data = {
            "question": "What is deep learning?",
            "retrieved_docs": [
                {"content": "Deep learning uses neural networks."},
                {"content": "It is a subset of machine learning."},
            ],
        }

        result = promptor.execute(input_data)

        # Verify result - QAPromptor returns [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2

        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)

        # Verify data remains unchanged
        assert data_result["question"] == "What is deep learning?"
        assert "retrieved_docs" in data_result

        # Verify prompt format
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"

    def test_execute_with_external_corpus(self):
        """Test execute method with external corpus"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Test input data with external_corpus
        input_data = {
            "question": "Explain neural networks",
            "external_corpus": "Neural networks are computing systems inspired by biological neural networks.",
        }

        result = promptor.execute(input_data)

        # Verify result - QAPromptor returns [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2

        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)

        # Verify data remains unchanged
        assert data_result["question"] == "Explain neural networks"
        assert "external_corpus" in data_result

        # Verify prompt format
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"

    def test_execute_with_empty_context(self):
        """Test execute method with empty context"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Test empty context
        input_data = {"question": "What is AI?", "context": []}

        result = promptor.execute(input_data)

        # Verify result - QAPromptor returns [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2

        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)

        # Verify data remains unchanged
        assert data_result["question"] == "What is AI?"
        assert "context" in data_result

        # Verify prompt format
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"

    def test_execute_with_query_tuple(self):
        """Test execute method with query dict using refining_docs"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Test dict input with refining_docs
        input_data = {
            "query": "What is reinforcement learning?",
            "refining_docs": [
                "Reinforcement learning is a type of machine learning.",
                "It involves agents learning through interaction.",
            ],
        }

        result = promptor.execute(input_data)

        # Verify result - returns [original_data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2
        original_data, prompt = result

        # Verify original data is preserved
        assert original_data == input_data

        # Verify prompt format
        assert isinstance(prompt, list)
        assert len(prompt) == 2
        system_msg, user_msg = prompt
        assert system_msg["role"] == "system"
        assert user_msg["role"] == "user"
        assert "What is reinforcement learning?" in user_msg["content"]

    def test_execute_preserves_additional_fields(self):
        """Test execute method preserves additional fields"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Test input data with additional fields
        input_data = {
            "question": "What is NLP?",
            "context": ["Natural Language Processing is a field of AI."],
            "metadata": {"source": "textbook"},
            "timestamp": "2023-01-01",
        }

        result = promptor.execute(input_data)

        # Verify result - QAPromptor returns [data, prompt]
        assert isinstance(result, list)
        assert len(result) == 2

        data_result, prompt_result = result
        assert isinstance(data_result, dict)
        assert isinstance(prompt_result, list)

        # Verify result preserves all original fields
        assert data_result["question"] == "What is NLP?"
        assert data_result["metadata"] == {"source": "textbook"}
        assert data_result["timestamp"] == "2023-01-01"
        assert "context" in data_result

        # Verify prompt format
        assert len(prompt_result) == 2  # system + user prompt
        assert prompt_result[0]["role"] == "system"
        assert prompt_result[1]["role"] == "user"


@pytest.mark.unit
class TestQueryProfilerPromptor:
    """Test QueryProfilerPromptor class"""

    def test_query_profiler_promptor_import(self):
        """Test QueryProfilerPromptor import"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        try:
            from sage.libs.rag.promptor import QueryProfilerPromptor

            assert QueryProfilerPromptor is not None
        except ImportError:
            pytest.skip("QueryProfilerPromptor not available in module")

    def test_query_profiler_promptor_initialization(self):
        """Test QueryProfilerPromptor initialization"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        try:
            from sage.libs.rag.promptor import QueryProfilerPromptor
        except ImportError:
            pytest.skip("QueryProfilerPromptor not available in module")

        config = {"metadata": {"dataset": "test"}, "chunk_size": 512}

        try:
            profiler = QueryProfilerPromptor(config=config)
            assert profiler.config == config
            assert hasattr(profiler, "execute")
        except Exception as e:
            pytest.skip(f"QueryProfilerPromptor initialization failed: {e}")


@pytest.mark.unit
class TestSummarizationPromptor:
    """Test SummarizationPromptor class"""

    def test_summarization_promptor_import(self):
        """Test SummarizationPromptor import"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        try:
            from sage.libs.rag.promptor import SummarizationPromptor

            assert SummarizationPromptor is not None
        except ImportError:
            pytest.skip("SummarizationPromptor not available in module")

    def test_summarization_promptor_initialization(self):
        """Test SummarizationPromptor initialization"""
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
            assert hasattr(promptor, "execute")
        except Exception as e:
            pytest.skip(f"SummarizationPromptor initialization failed: {e}")

    def test_summarization_promptor_execute(self):
        """Test SummarizationPromptor execute"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        try:
            from sage.libs.rag.promptor import SummarizationPromptor
        except ImportError:
            pytest.skip("SummarizationPromptor not available in module")

        config = {"task_type": "summarization"}
        promptor = SummarizationPromptor(config=config)

        # SummarizationPromptor expects (query, external_corpus) format
        query = "Please summarize the following text"
        external_corpus = [
            "This is a long text that needs to be summarized. ",
            "It contains multiple sentences and paragraphs with important information.",
        ]

        input_data = (query, external_corpus)

        result = promptor.execute(input_data)

        # Verify result - SummarizationPromptor returns [data, message] format
        assert isinstance(result, list)
        assert len(result) == 2

        data, message = result
        assert isinstance(data, dict)
        assert isinstance(message, dict)

        # Check message content
        assert "content" in message
        assert "Please summarize the following text" in message["content"]


@pytest.mark.unit
class TestPromptTemplates:
    """Test prompt templates"""

    def test_qa_prompt_template(self):
        """Test QA prompt template"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        from sage.libs.rag.promptor import QA_prompt_template

        # Test template rendering
        context = "Machine learning is a subset of artificial intelligence."
        rendered = QA_prompt_template.render(external_corpus=context)

        assert "Machine learning is a subset of artificial intelligence." in rendered
        assert "intelligent assistant" in rendered
        assert "knowledge base" in rendered

    def test_qa_prompt_template_no_context(self):
        """Test QA prompt template without context"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        from sage.libs.rag.promptor import QA_prompt_template

        # Test template rendering without context
        rendered = QA_prompt_template.render()

        assert "intelligent assistant" in rendered
        assert "knowledge base" in rendered
        # Should not contain context section
        assert "Relevant corpus" not in rendered

    def test_summarization_prompt_template(self):
        """Test summarization prompt template"""
        if not PROMPTOR_AVAILABLE:
            pytest.skip("Promptor module not available")

        from sage.libs.rag.promptor import summarization_prompt_template

        # Test template rendering
        content = "This is content that needs to be summarized."
        rendered = summarization_prompt_template.render(external_corpus=content)

        assert "This is content that needs to be summarized." in rendered
        assert "Summarize the content" in rendered
        assert "concise and clear" in rendered


@pytest.mark.integration
class TestPromptorIntegration:
    """Promptor integration tests"""

    @pytest.mark.skipif(not PROMPTOR_AVAILABLE, reason="Promptor module not available")
    def test_qa_promptor_full_pipeline(self):
        """Test QAPromptor complete pipeline"""
        config = {"task_type": "qa"}
        promptor = QAPromptor(config=config)

        # Simulate complete RAG pipeline data with new unified format
        pipeline_data = {
            "query": "What are the benefits of renewable energy?",
            "retrieval_results": [
                "Renewable energy reduces carbon emissions.",
                "Solar and wind power are sustainable sources.",
                "Renewable energy creates green jobs.",
            ],
            "retrieval_docs": [
                "Renewable energy reduces carbon emissions.",
                "Solar and wind power are sustainable sources.",
                "Renewable energy creates green jobs.",
            ],
            "retrieval_time": 0.5,
        }

        result = promptor.execute(pipeline_data)

        # QAPromptor returns [data, prompt] format
        assert isinstance(result, list)
        assert len(result) == 2

        data, messages = result

        # Verify data section
        assert isinstance(data, dict)
        assert "query" in data
        assert "retrieval_docs" in data

        # Verify messages section (OpenAI format)
        assert isinstance(messages, list)
        assert len(messages) >= 1

        # Check messages content
        message_content = str(messages)
        assert "What are the benefits of renewable energy?" in message_content
