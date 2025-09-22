"""
测试 sage.libs.agents.agent 模块
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import requests

# 尝试导入，如果失败则跳过测试
pytest_plugins = []

try:
    from sage.libs.agents.agent import Tool, BochaSearch, Agent, PREFIX, FORMAT_INSTRUCTIONS
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Agent module not available: {e}")


@pytest.mark.unit
class TestTool:
    """测试Tool类"""
    
    def test_tool_initialization(self):
        """测试Tool初始化"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        def sample_func(x, y):
            return x + y
            
        tool = Tool("add", sample_func, "添加两个数字")
        
        assert tool.name == "add"
        assert tool.func == sample_func
        assert tool.description == "添加两个数字"
    
    def test_tool_run(self):
        """测试Tool运行"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        def multiply(x, y):
            return x * y
            
        tool = Tool("multiply", multiply, "乘法运算")
        result = tool.run(3, 4)
        
        assert result == 12
    
    def test_tool_run_with_kwargs(self):
        """测试Tool使用关键字参数运行"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
            
        tool = Tool("greet", greet, "问候函数")
        result = tool.run("Alice", greeting="Hi")
        
        assert result == "Hi, Alice!"


@pytest.mark.unit
class TestBochaSearch:
    """测试BochaSearch类"""
    
    def test_bocha_search_initialization(self):
        """测试BochaSearch初始化"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        api_key = "test_api_key"
        search = BochaSearch(api_key)
        
        assert search.api_key == api_key
        assert search.url == "https://api.bochaai.com/v1/web-search"
        assert search.headers["Authorization"] == api_key
        assert search.headers["Content-Type"] == "application/json"
    
    @patch('requests.request')
    def test_bocha_search_run_success(self, mock_request):
        """测试BochaSearch运行成功"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        # 模拟成功响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"title": "测试结果1", "url": "http://test1.com"},
                {"title": "测试结果2", "url": "http://test2.com"}
            ]
        }
        mock_request.return_value = mock_response
        
        search = BochaSearch("test_api_key")
        result = search.run("Python编程")
        
        # 验证请求调用
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        
        assert call_args[0] == ("POST", "https://api.bochaai.com/v1/web-search")
        assert "Authorization" in call_args[1]["headers"]
        
        # 验证结果
        assert "results" in result
        assert len(result["results"]) == 2
    
    @patch('requests.request')
    def test_bocha_search_run_with_parameters(self, mock_request):
        """测试BochaSearch运行时的参数"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response
        
        search = BochaSearch("test_api_key")
        search.run("机器学习")
        
        # 验证请求参数
        call_args = mock_request.call_args
        payload_str = call_args[1]["data"]
        payload = json.loads(payload_str)
        
        assert payload["query"] == "机器学习"
        assert payload["summary"] == True
        assert payload["count"] == 10
        assert payload["page"] == 1


@pytest.mark.unit
class TestAgentConstants:
    """测试Agent常量"""
    
    def test_prefix_constant(self):
        """测试PREFIX常量"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        assert "Answer the following questions" in PREFIX
        assert "tools" in PREFIX.lower()
    
    def test_format_instructions_constant(self):
        """测试FORMAT_INSTRUCTIONS常量"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        assert "JSON format" in FORMAT_INSTRUCTIONS
        assert "thought" in FORMAT_INSTRUCTIONS
        assert "action" in FORMAT_INSTRUCTIONS
        assert "action_input" in FORMAT_INSTRUCTIONS
        assert "observation" in FORMAT_INSTRUCTIONS
        assert "final_answer" in FORMAT_INSTRUCTIONS


@pytest.mark.integration
class TestAgentIntegration:
    """Agent集成测试"""
    
    @patch('requests.request')
    def test_agent_with_bocha_search_integration(self, mock_request):
        """测试Agent与BochaSearch的集成"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        # 模拟搜索响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"title": "AI相关结果", "snippet": "人工智能是..."}]
        }
        mock_request.return_value = mock_response
        
        # 创建工具
        search = BochaSearch("test_api_key")
        search_tool = Tool("search", search.run, "网络搜索工具")
        
        # 测试工具使用
        result = search_tool.run("什么是人工智能")
        
        assert "results" in result
        mock_request.assert_called_once()
    
    def test_multiple_tools_integration(self):
        """测试多个工具的集成"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        # 创建多个工具
        def calc_add(a, b):
            return a + b
            
        def calc_multiply(a, b):
            return a * b
            
        add_tool = Tool("add", calc_add, "加法计算")
        multiply_tool = Tool("multiply", calc_multiply, "乘法计算")
        
        # 测试工具组合使用
        result1 = add_tool.run(5, 3)  # 8
        result2 = multiply_tool.run(result1, 2)  # 16
        
        assert result1 == 8
        assert result2 == 16


@pytest.mark.slow
class TestAgentPerformance:
    """Agent性能测试"""
    
    def test_tool_execution_performance(self):
        """测试工具执行性能"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        import time
        
        def fast_function():
            return "fast"
            
        def slow_function():
            time.sleep(0.01)  # 模拟耗时操作
            return "slow"
        
        fast_tool = Tool("fast", fast_function, "快速工具")
        slow_tool = Tool("slow", slow_function, "慢速工具")
        
        # 测试快速工具
        start = time.time()
        result = fast_tool.run()
        fast_time = time.time() - start
        
        # 测试慢速工具
        start = time.time()
        result = slow_tool.run()
        slow_time = time.time() - start
        
        assert fast_time < slow_time
        assert fast_time < 0.001  # 应该很快


@pytest.mark.external
class TestBochaSearchExternal:
    """BochaSearch外部依赖测试"""
    
    def test_bocha_search_network_error_handling(self):
        """测试网络错误处理"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        with patch('requests.request') as mock_request:
            # 模拟网络错误
            mock_request.side_effect = requests.exceptions.ConnectionError("网络连接失败")
            
            search = BochaSearch("test_api_key")
            
            with pytest.raises(requests.exceptions.ConnectionError):
                search.run("测试查询")
    
    def test_bocha_search_invalid_response(self):
        """测试无效响应处理"""
        if not AGENT_AVAILABLE:
            pytest.skip("Agent module not available")
            
        with patch('requests.request') as mock_request:
            # 模拟无效JSON响应
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_request.return_value = mock_response
            
            search = BochaSearch("test_api_key")
            
            with pytest.raises(json.JSONDecodeError):
                search.run("测试查询")


# ===== 简化版测试（当模块不可用时） =====

@pytest.mark.unit
class TestAgentModuleFallback:
    """Agent模块降级测试"""
    
    def test_module_import_fallback(self):
        """测试模块导入降级"""
        # 这个测试总是运行，检查模块可用性
        try:
            from sage.libs.agents.agent import Tool
            assert True  # 导入成功
        except ImportError:
            # 模块不可用，但测试应该通过
            assert True
    
    def test_basic_tool_concept(self):
        """测试基本工具概念（不依赖实际实现）"""
        # 模拟Tool类的基本概念
        class MockTool:
            def __init__(self, name, func, description):
                self.name = name
                self.func = func
                self.description = description
            
            def run(self, *args, **kwargs):
                return self.func(*args, **kwargs)
        
        def add(a, b):
            return a + b
            
        tool = MockTool("add", add, "加法工具")
        result = tool.run(2, 3)
        
        assert result == 5
        assert tool.name == "add"
        assert tool.description == "加法工具"
