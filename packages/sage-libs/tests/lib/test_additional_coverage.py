"""
Unit tests for LLM Planner and other components
"""

from unittest.mock import MagicMock

import pytest

# Check if vllm is available
try:
    import vllm  # noqa: F401

    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False


class TestLLMPlanner:
    """Test LLMPlanner class"""

    def test_llm_planner_init(self):
        """Test LLMPlanner initialization"""
        from sage.libs.agents.planning.llm_planner import LLMPlanner

        mock_generator = MagicMock()
        planner = LLMPlanner(generator=mock_generator)
        assert planner is not None
        assert planner.generator == mock_generator

    def test_llm_planner_plan_generation(self):
        """Test plan generation"""
        from sage.libs.agents.planning.llm_planner import LLMPlanner

        mock_generator = MagicMock()
        # Mock generator to return valid JSON plan
        plan_json = '[{"type":"tool","name":"calculator","arguments":{"expr":"2+2"}},{"type":"reply","text":"完成"}]'
        mock_generator.execute.return_value = ("test query", plan_json)

        planner = LLMPlanner(generator=mock_generator, max_steps=3)
        tools = {
            "calculator": {
                "description": "Do math",
                "input_schema": {
                    "type": "object",
                    "properties": {"expr": {"type": "string"}},
                    "required": ["expr"],
                },
            }
        }
        plan = planner.plan("System prompt", "计算 2+2", tools)
        assert plan is not None
        assert len(plan) > 0

    def test_llm_planner_with_custom_params(self):
        """Test LLMPlanner with custom parameters"""
        from sage.libs.agents.planning.llm_planner import LLMPlanner

        mock_generator = MagicMock()
        planner = LLMPlanner(
            generator=mock_generator, max_steps=10, enable_repair=False, topk_tools=8
        )
        assert planner.max_steps == 10
        assert planner.enable_repair is False
        assert planner.topk_tools == 8


class TestLLMPlannerErrorHandling:
    """Test error handling in LLMPlanner"""

    def test_llm_planner_repair_mechanism(self):
        """Test LLMPlanner repair mechanism when JSON parsing fails"""
        from sage.libs.agents.planning.llm_planner import LLMPlanner

        mock_generator = MagicMock()
        # First call returns invalid JSON, second call returns valid JSON
        plan_json = '[{"type":"reply","text":"修复后的回复"}]'
        mock_generator.execute.side_effect = [
            ("test query", "Invalid JSON response"),  # First try fails
            ("test query", plan_json),  # Repair succeeds
        ]

        planner = LLMPlanner(generator=mock_generator, enable_repair=True)
        tools = {"test_tool": {"description": "Test", "input_schema": {"type": "object"}}}
        plan = planner.plan("System", "Query", tools)

        # Should have called execute twice (initial + repair)
        assert mock_generator.execute.call_count == 2
        assert plan is not None


class TestLongRefinerPromptTemplate:
    """Test PromptTemplate class"""

    @pytest.mark.skipif(not VLLM_AVAILABLE, reason="vllm not available")
    def test_prompt_template_init(self):
        """Test PromptTemplate initialization"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.prompt_template import (
            PromptTemplate,
        )

        mock_tokenizer = MagicMock()
        template = PromptTemplate(
            mock_tokenizer, system_prompt="System", user_prompt="User {query}"
        )
        assert template is not None
        assert template.system_prompt == "System"
        assert template.user_prompt == "User {query}"

    @pytest.mark.skipif(not VLLM_AVAILABLE, reason="vllm not available")
    def test_prompt_template_get_prompt(self):
        """Test PromptTemplate get_prompt method"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.prompt_template import (
            PromptTemplate,
        )

        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template.return_value = "Formatted prompt"
        mock_tokenizer.return_value = MagicMock(input_ids=[[1, 2, 3]])

        template = PromptTemplate(
            mock_tokenizer, system_prompt="System", user_prompt="User {question}"
        )

        # Test get_prompt method which is the actual method
        result = template.get_prompt(question="test query")
        assert result is not None


class TestBaseTool:
    """Test BaseTool class"""

    def test_base_tool_init(self):
        """Test BaseTool initialization"""
        from sage.libs.tools.tool import BaseTool

        class TestTool(BaseTool):
            def execute(self, *args, **kwargs):
                return "result"

        tool = TestTool(tool_name="test_tool", tool_description="A test tool", input_types=["str"])
        assert tool is not None
        assert tool.tool_name == "test_tool"

    def test_base_tool_execute(self):
        """Test BaseTool execute method"""
        from sage.libs.tools.tool import BaseTool

        class TestTool(BaseTool):
            def execute(self, *args, **kwargs):
                return "tool result"

        tool = TestTool(tool_name="test_tool", tool_description="A test tool")
        result = tool.execute("test input")
        assert result == "tool result"

    def test_base_tool_metadata(self):
        """Test BaseTool get_metadata method"""
        from sage.libs.tools.tool import BaseTool

        class TestTool(BaseTool):
            def execute(self, *args, **kwargs):
                return "result"

        tool = TestTool(
            tool_name="test_tool",
            tool_description="A test tool",
            input_types=["str"],
            output_type="str",
        )
        metadata = tool.get_metadata()
        assert metadata["name"] == "test_tool"
        assert metadata["description"] == "A test tool"


class TestSink:
    """Test Sink classes"""

    def test_terminal_sink_init(self):
        """Test TerminalSink initialization"""
        from sage.libs.io.sink import TerminalSink

        sink = TerminalSink(config={})
        assert sink is not None

    def test_terminal_sink_execute_with_dict(self):
        """Test TerminalSink execute with dict input"""
        from sage.libs.io.sink import TerminalSink

        sink = TerminalSink(config={})
        data = {"query": "Test question", "answer": "Test answer"}
        # execute method prints output, we just test it doesn't raise
        sink.execute(data)

    def test_file_sink_init(self):
        """Test FileSink initialization"""
        from sage.libs.io.sink import FileSink

        sink = FileSink(config={})
        assert sink is not None


class TestBaseServiceKernel:
    """Test BaseService from kernel"""

    def test_base_service_init(self):
        """Test BaseService initialization"""
        from sage.platform.service.base_service import BaseService

        class TestService(BaseService):
            pass

        service = TestService()
        assert service is not None

    def test_base_service_logger_property(self):
        """Test BaseService logger property"""
        from sage.platform.service.base_service import BaseService

        class TestService(BaseService):
            pass

        service = TestService()
        # logger is a property
        logger = service.logger
        assert logger is not None

    def test_base_service_name_property(self):
        """Test BaseService name property"""
        from sage.platform.service.base_service import BaseService

        class TestService(BaseService):
            pass

        service = TestService()
        # name should default to class name
        assert service.name == "TestService"
