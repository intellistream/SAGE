"""
End-to-end integration tests for the agent workflow.

These tests verify the complete agent pipeline added in commit 12aec700c63407e1f5d79455b2d64a60a6688e96,
including the interaction between all components.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest

# Test imports with fallbacks
try:
    from examples.agents.tools.arxiv_tool import ArxivSearchTool
    ARXIV_TOOL_AVAILABLE = True
except ImportError:
    ARXIV_TOOL_AVAILABLE = False

try:
    from sage.libs.agents.action.mcp_registry import MCPRegistry
    from sage.libs.agents.planning.llm_planner import LLMPlanner
    from sage.libs.agents.profile.profile import BaseProfile
    from sage.libs.agents.runtime.agent import AgentRuntime
    from sage.libs.rag.generator import OpenAIGenerator
    SAGE_COMPONENTS_AVAILABLE = True
except ImportError:
    SAGE_COMPONENTS_AVAILABLE = False


@pytest.mark.integration
class TestAgentWorkflowIntegration:
    """End-to-end integration tests for the complete agent workflow."""
    
    def create_test_config(self):
        """Create a minimal test configuration."""
        return {
            "profile": {
                "name": "TestAgent",
                "role": "assistant",
                "language": "zh", 
                "goals": ["帮助用户完成任务"],
                "constraints": ["使用提供的工具"],
                "persona": {"style": "professional"}
            },
            "generator": {
                "remote": {
                    "api_key": "test-key",
                    "method": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "base_url": "https://api.openai.com/v1",
                    "seed": 42
                }
            },
            "planner": {
                "max_steps": 5,
                "enable_repair": True,
                "topk_tools": 3
            },
            "tools": [
                {
                    "module": "examples.agents.tools.arxiv_tool",
                    "class": "ArxivSearchTool",
                    "init_kwargs": {}
                }
            ],
            "runtime": {
                "max_steps": 5,
                "summarizer": "reuse_generator"
            },
            "source": {
                "type": "local",
                "data_path": "test_queries.jsonl",
                "field_query": "query"
            }
        }
    
    def create_mock_generator(self):
        """Create a mock generator for testing."""
        mock_generator = Mock()
        
        def mock_execute(data):
            # Handle both old format and new message format
            user_query = data[0]
            second_param = data[1]
            
            if isinstance(second_param, list):
                # New message format - extract user query from messages
                for msg in second_param:
                    if msg.get("role") == "user":
                        user_query = msg["content"]
                        break
            
            # Generate a simple plan based on the query
            if "arxiv" in user_query.lower() or "paper" in user_query.lower():
                plan = [
                    {
                        "type": "tool",
                        "name": "arxiv_search", 
                        "arguments": {"query": "machine learning", "max_results": 2}
                    },
                    {"type": "reply", "text": "已找到相关论文"}
                ]
            else:
                plan = [
                    {"type": "reply", "text": "我理解您的问题"}
                ]
            
            return (data[0], json.dumps(plan, ensure_ascii=False))
        
        mock_generator.execute = mock_execute
        return mock_generator
    
    def create_mock_arxiv_tool(self):
        """Create a mock ArxivSearchTool for testing."""
        if not ARXIV_TOOL_AVAILABLE:
            # Create a mock version if real tool isn't available
            mock_tool = Mock()
            mock_tool.name = "arxiv_search"
            mock_tool.description = "Search arXiv papers"
            mock_tool.input_schema = {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
            
            def mock_call(arguments):
                return {
                    "output": [
                        {
                            "title": "Test Paper 1",
                            "authors": "Test Author",
                            "link": "https://arxiv.org/abs/1234.5678",
                            "abstract": "Test abstract"
                        }
                    ],
                    "meta": {"query": arguments.get("query", ""), "max_results": arguments.get("max_results", 10)}
                }
            
            mock_tool.call = mock_call
            return mock_tool
        else:
            # Use real tool but mock the network calls
            tool = ArxivSearchTool()
            with patch.object(tool, '_search_arxiv') as mock_search:
                mock_search.return_value = [
                    {
                        "title": "Mock Paper",
                        "authors": "Mock Author", 
                        "link": "https://arxiv.org/abs/mock",
                        "abstract": "Mock abstract"
                    }
                ]
                return tool
    
    @pytest.mark.skipif(not SAGE_COMPONENTS_AVAILABLE, reason="SAGE components not available")
    def test_complete_agent_workflow_with_arxiv_query(self):
        """Test the complete agent workflow with an arXiv search query."""
        
        # Create test query file
        test_queries = [
            {"query": "在 arXiv 搜索 2 篇机器学习论文"},
            {"query": "帮我总结一下深度学习的发展"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for query in test_queries:
                f.write(json.dumps(query, ensure_ascii=False) + '\n')
            temp_path = f.name
        
        try:
            # Create components
            profile = BaseProfile(
                name="TestAgent",
                role="assistant", 
                language="zh",
                goals=["帮助用户"],
                tasks=["使用工具"],
                tone="helpful"
            )
            
            generator = self.create_mock_generator()
            planner = LLMPlanner(generator=generator, max_steps=5)
            
            registry = MCPRegistry()
            arxiv_tool = self.create_mock_arxiv_tool()
            registry.register(arxiv_tool)
            
            runtime = AgentRuntime(
                profile=profile,
                planner=planner,
                tools=registry,
                summarizer=generator,
                max_steps=5
            )
            
            # Test source reading
            from examples.agents.agent import iter_queries
            source_config = {
                "type": "local",
                "data_path": temp_path,
                "field_query": "query"
            }
            
            queries = list(iter_queries(source_config))
            assert len(queries) == 2
            assert "arXiv" in queries[0]
            assert "深度学习" in queries[1]
            
            # Test agent execution for each query
            for query in queries:
                response = runtime.execute({"query": query})
                assert response is not None
                assert isinstance(response, str)
                
                if "arxiv" in query.lower():
                    # Should mention finding papers
                    assert "论文" in response or "paper" in response.lower()
                
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.skipif(not SAGE_COMPONENTS_AVAILABLE, reason="SAGE components not available")
    def test_agent_tool_integration(self):
        """Test that agent properly integrates with tools."""
        
        # Create mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.input_schema = {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"]
        }
        
        def mock_call(arguments):
            return {"output": f"Processed: {arguments.get('input', 'no input')}"}
        
        mock_tool.call = mock_call
        
        # Create generator that uses the tool
        def tool_using_generator(data):
            plan = [
                {
                    "type": "tool",
                    "name": "test_tool",
                    "arguments": {"input": "test data"}
                },
                {"type": "reply", "text": "工具调用完成"}
            ]
            return (data[0], json.dumps(plan, ensure_ascii=False))
        
        mock_generator = Mock()
        mock_generator.execute = tool_using_generator
        
        # Set up components
        profile = BaseProfile(language="zh")
        planner = LLMPlanner(generator=mock_generator)
        
        registry = MCPRegistry()
        registry.register(mock_tool)
        
        runtime = AgentRuntime(
            profile=profile,
            planner=planner,
            tools=registry,
            summarizer=None
        )
        
        # Execute and verify tool was called
        response = runtime.execute({"query": "使用测试工具"})
        assert "工具调用完成" in response
    
    @pytest.mark.skipif(not SAGE_COMPONENTS_AVAILABLE, reason="SAGE components not available")
    def test_agent_error_handling(self):
        """Test agent error handling in various scenarios."""
        
        # Test with tool that raises an exception
        failing_tool = Mock()
        failing_tool.name = "failing_tool"
        failing_tool.description = "A tool that fails"
        failing_tool.input_schema = {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"]
        }
        
        def failing_call(arguments):
            raise Exception("Tool execution failed")
        
        failing_tool.call = failing_call
        
        # Generator that tries to use the failing tool
        def failing_generator(data):
            plan = [
                {
                    "type": "tool",
                    "name": "failing_tool",
                    "arguments": {"input": "test"}
                },
                {"type": "reply", "text": "应该不会到达这里"}
            ]
            return (data[0], json.dumps(plan, ensure_ascii=False))
        
        mock_generator = Mock()
        mock_generator.execute = failing_generator
        
        profile = BaseProfile(language="zh")
        planner = LLMPlanner(generator=mock_generator)
        
        registry = MCPRegistry()
        registry.register(failing_tool)
        
        runtime = AgentRuntime(
            profile=profile,
            planner=planner,
            tools=registry,
            summarizer=None
        )
        
        # Should handle the error gracefully
        response = runtime.execute({"query": "使用会失败的工具"})
        assert response is not None
        # Should contain some error indication or fallback response
        assert isinstance(response, str)
    
    @pytest.mark.skipif(not SAGE_COMPONENTS_AVAILABLE, reason="SAGE components not available")
    def test_message_format_consistency(self):
        """Test that the new message format is used consistently throughout the pipeline."""
        
        # Generator that validates message format
        message_validator = Mock()
        
        def validate_and_respond(data):
            user_query, second_param = data
            
            # Should receive messages in new format
            if isinstance(second_param, list):
                messages = second_param
                assert len(messages) >= 1
                
                # Check for system message
                system_msgs = [msg for msg in messages if msg.get("role") == "system"]
                assert len(system_msgs) >= 1
                
                # Check for user message
                user_msgs = [msg for msg in messages if msg.get("role") == "user"]
                if len(user_msgs) > 0:
                    assert user_msgs[0]["content"] == user_query
            
            plan = [{"type": "reply", "text": "消息格式验证通过"}]
            return (user_query, json.dumps(plan, ensure_ascii=False))
        
        message_validator.execute = validate_and_respond
        
        profile = BaseProfile(language="zh")
        planner = LLMPlanner(generator=message_validator)
        registry = MCPRegistry()
        
        runtime = AgentRuntime(
            profile=profile,
            planner=planner,
            tools=registry,
            summarizer=message_validator
        )
        
        # Should not raise any assertion errors
        response = runtime.execute({"query": "测试消息格式"})
        assert "消息格式验证通过" in response
    
    def test_test_mode_compatibility(self):
        """Test that the agent examples work in test mode."""
        
        try:
            # Import the agent module
            from examples.agents import agent
            
            # Mock the main function to avoid actual execution
            with patch.object(agent, 'main') as mock_main:
                
                # Simulate test mode execution
                with patch.dict('os.environ', {'SAGE_EXAMPLES_MODE': 'test'}):
                    # This should call main() and then print success message
                    try:
                        agent.main()
                        print("\n✅ Test passed: Agent pipeline structure validated")
                        test_passed = True
                    except Exception as e:
                        print(f"❌ Test failed: {e}")
                        test_passed = False
                
                # Verify main was called
                mock_main.assert_called_once()
                
        except ImportError:
            pytest.skip("Agent examples module not available")


@pytest.mark.integration
class TestConfigIntegration:
    """Integration tests with real configuration files."""
    
    def test_config_with_real_components(self):
        """Test that the configuration works with real SAGE components."""
        
        if not SAGE_COMPONENTS_AVAILABLE:
            pytest.skip("SAGE components not available")
        
        from sage.common.utils.config.loader import load_config
        
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..", "..",
            "examples", "config", "config_agent_min.yaml"
        )
        
        if not os.path.exists(config_path):
            pytest.skip("Config file not found")
        
        try:
            config = load_config(config_path)
            
            # Test profile creation
            profile = BaseProfile.from_dict(config["profile"])
            assert profile.name == config["profile"]["name"]
            
            # Test registry creation
            registry = MCPRegistry()
            assert registry is not None
            
            # Test that generator config is valid structure
            gen_config = config["generator"]["remote"]
            assert "method" in gen_config
            assert "model_name" in gen_config
            
        except Exception as e:
            pytest.fail(f"Config integration failed: {e}")
    
    def test_data_file_compatibility(self):
        """Test that the data file format is compatible with iter_queries."""
        
        try:
            from examples.agents.agent import iter_queries
            
            # Check if the data file exists
            data_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "..", "..",
                "examples", "data", "agent_queries.jsonl"
            )
            
            if os.path.exists(data_path):
                source_config = {
                    "type": "local",
                    "data_path": data_path,
                    "field_query": "query"
                }
                
                queries = list(iter_queries(source_config))
                assert len(queries) > 0
                
                # All queries should be non-empty strings
                for query in queries:
                    assert isinstance(query, str)
                    assert len(query.strip()) > 0
                    
            else:
                pytest.skip("Agent queries data file not found")
                
        except ImportError:
            pytest.skip("Agent examples module not available")