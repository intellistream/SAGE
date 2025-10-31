"""
测试 sage.middleware.operators.rag.searcher 模块
"""

import pytest
from unittest.mock import Mock, patch

# 尝试导入searcher模块
pytest_plugins = []

try:
    from sage.middleware.operators.rag.searcher import BochaWebSearch

    SEARCHER_AVAILABLE = True
except ImportError as e:
    SEARCHER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Searcher module not available: {e}")


@pytest.mark.unit
class TestBochaWebSearch:
    """测试BochaWebSearch类"""

    def test_bocha_web_search_import(self):
        """测试BochaWebSearch导入"""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher module not available")

        from sage.middleware.operators.rag.searcher import BochaWebSearch

        assert BochaWebSearch is not None

    def test_bocha_web_search_initialization(self):
        """测试BochaWebSearch初始化"""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher module not available")

        config = {
            "api_key": "test_api_key",
            "count": 5,
            "page": 1,
            "summary": True,
        }

        searcher = BochaWebSearch(config=config)

        assert searcher.api_key == "test_api_key"
        assert searcher.count == 5
        assert searcher.page == 1
        assert searcher.summary is True

    def test_bocha_web_search_missing_api_key(self):
        """测试缺少API密钥"""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher module not available")

        config = {}

        with pytest.raises(ValueError, match="requires an 'api_key'"):
            BochaWebSearch(config=config)

    @patch('requests.post')
    def test_execute_success(self, mock_post):
        """测试成功执行搜索"""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher module not available")

        # Mock成功响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "snippet": "Snippet 1"},
                {"title": "Result 2", "snippet": "Snippet 2"},
            ]
        }
        mock_post.return_value = mock_response

        config = {"api_key": "test_key", "count": 2}
        searcher = BochaWebSearch(config=config)

        result = searcher.execute("test query")

        assert isinstance(result, dict)
        assert "results" in result

    @patch('requests.post')
    def test_execute_error_handling(self, mock_post):
        """测试错误处理"""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher module not available")

        # Mock请求异常
        mock_post.side_effect = Exception("API Error")

        config = {"api_key": "test_key"}
        searcher = BochaWebSearch(config=config)

        result = searcher.execute("test query")

        # 应该返回空字典
        assert result == {}
