# url_text_extractor_test.py

# ================================
# 重要提示：此测试文件依赖 pytest-mock 插件。
# 如果遇到 "fixture 'mocker' not found" 的错误，请运行以下命令安装：
# pip install pytest-mock
# ================================

import pytest
import requests
from unittest.mock import MagicMock

# ================================
# 关键修改：根据您的项目结构更新 import 语句
# 假设您的源文件位于 sage.lib/tools/url_text_extractor.py
# ================================
from sage.apps.lib.tools.url_text_extractor import URL_Text_Extractor_Tool


# ================================
# 1. Fixture: 创建可复用的工具实例
# ================================
@pytest.fixture
def url_extractor_tool():
    """
    这是一个 Fixture，为每个测试提供一个干净的 URL_Text_Extractor_Tool 实例。
    """
    return URL_Text_Extractor_Tool()

# ================================
# 2. 核心功能测试（使用 Mocking）
# ================================

def test_initialization(url_extractor_tool):
    """
    测试：工具初始化时，其元数据是否正确。
    """
    assert url_extractor_tool.tool_name == "URL_Text_Extractor_Tool"
    assert "url" in url_extractor_tool.input_types

def test_execute_success(url_extractor_tool, mocker):
    """
    测试：在成功获取网页时，能否正确提取和格式化文本。
    """
    # --- 准备 (Arrange) ---
    # 模拟一个简单的 HTML 页面
    fake_html = "<html><head><title>Test Page</title></head><body><p>Hello</p> <span>World</span></body></html>"
    expected_text = "Test Page\nHello\nWorld"
    
    # 模拟 requests.get 的成功响应
    mock_response = MagicMock()
    mock_response.content = fake_html.encode('utf-8')
    # 模拟 raise_for_status() 不抛出任何异常
    mock_response.raise_for_status.return_value = None
    mock_get = mocker.patch('requests.get', return_value=mock_response)

    # --- 执行 (Act) ---
    result = url_extractor_tool.execute(url="https://fake-example.com")

    # --- 断言 (Assert) ---
    mock_get.assert_called_once_with("https://fake-example.com")
    assert "extracted_text" in result
    assert result["extracted_text"] == expected_text

def test_arxiv_pdf_url_replacement(url_extractor_tool, mocker):
    """
    测试：是否能正确地将 arxiv.org/pdf 链接替换为 /abs 链接。
    """
    # --- 准备 (Arrange) ---
    mock_get = mocker.patch('requests.get', return_value=MagicMock())
    pdf_url = "https://arxiv.org/pdf/1234.5678"
    expected_abs_url = "https://arxiv.org/abs/1234.5678"

    # --- 执行 (Act) ---
    url_extractor_tool.execute(url=pdf_url)

    # --- 断言 (Assert) ---
    # 验证 requests.get 是用替换后的 URL 调用的
    mock_get.assert_called_once_with(expected_abs_url)

def test_text_truncation(url_extractor_tool, mocker):
    """
    测试：当提取的文本超过10000个字符时，是否会被正确截断。
    """
    # --- 准备 (Arrange) ---
    # 创建一个超过10000个字符的假文本
    long_text = "a" * 10001
    fake_html = f"<html><body>{long_text}</body></html>"
    
    mock_response = MagicMock()
    mock_response.content = fake_html.encode('utf-8')
    mock_response.raise_for_status.return_value = None
    mocker.patch('requests.get', return_value=mock_response)

    # --- 执行 (Act) ---
    result = url_extractor_tool.execute(url="https://longtext.com")

    # --- 断言 (Assert) ---
    extracted_text = result["extracted_text"]
    assert len(extracted_text) == 10000
    assert extracted_text == "a" * 10000

def test_network_error_handling(url_extractor_tool, mocker):
    """
    测试：当发生网络错误时，能否返回正确的错误信息。
    """
    # --- 准备 (Arrange) ---
    # 模拟 requests.get 抛出网络异常
    error_message = "Fake 404 Not Found"
    mocker.patch('requests.get', side_effect=requests.RequestException(error_message))

    # --- 执行 (Act) ---
    result = url_extractor_tool.execute(url="https://non-existent-url.com")

    # --- 断言 (Assert) ---
    assert "extracted_text" in result
    assert "Error fetching URL" in result["extracted_text"]
    assert error_message in result["extracted_text"]

def test_general_error_handling(url_extractor_tool, mocker):
    """
    测试：当发生非网络的其他异常时，能否返回正确的错误信息。
    """
    # --- 准备 (Arrange) ---
    # 模拟 BeautifulSoup 在解析时发生异常
    error_message = "Fake parsing error"
    mocker.patch('requests.get', return_value=MagicMock()) # 让 get 成功
    mocker.patch('sage.lib.tools.url_text_extractor.BeautifulSoup', side_effect=Exception(error_message))

    # --- 执行 (Act) ---
    result = url_extractor_tool.execute(url="https://badhtml.com")

    # --- 断言 (Assert) ---
    assert "extracted_text" in result
    assert "Error extracting text" in result["extracted_text"]
    assert error_message in result["extracted_text"]
