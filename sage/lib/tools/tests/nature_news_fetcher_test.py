# nature_news_fetcher_test.py

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
# 假设您的源文件位于 sage.lib/tools/nature_news_fetcher.py
# ================================
from sage.lib.tools.nature_news_fetcher import Nature_News_Fetcher_Tool

# ================================
# 1. Fixture: 创建可复用的工具实例
# ================================
@pytest.fixture
def news_fetcher_tool():
    """
    这是一个 Fixture，为每个测试提供一个干净的 Nature_News_Fetcher_Tool 实例。
    """
    return Nature_News_Fetcher_Tool()

# ================================
# 2. 辅助数据和函数
# ================================
def create_fake_html_page(num_articles):
    """
    一个辅助函数，用于生成包含指定数量文章的假 HTML 页面。
    """
    if num_articles == 0:
        return """
        <html><body><section id='new-article-list'></section></body></html>
        """
    
    article_template = """
    <article class="c-card">
      <h3 class="c-card__title">
        <a href="/articles/d41586-024-000{i}-5">Fake Article Title {i}</a>
      </h3>
      <div data-test="article-description">Fake description {i}.</div>
      <ul data-test="author-list"><li>Fake Author</li></ul>
      <time datetime="2024-01-0{i}T00:00:00Z">Jan 0{i}, 2024</time>
      <img src="https://fake.url/image{i}.jpg" />
    </article>
    """
    articles_html = "".join([article_template.format(i=i) for i in range(1, num_articles + 1)])
    
    return f"""
    <html><body><section id='new-article-list'>{articles_html}</section></body></html>
    """

# ================================
# 3. 核心功能测试（使用 Mocking）
# ================================

def test_initialization(news_fetcher_tool):
    """
    测试：工具初始化时，其元数据是否正确。
    """
    assert news_fetcher_tool.tool_name == "Nature_News_Fetcher_Tool"
    assert "num_articles" in news_fetcher_tool.input_types

def test_parse_articles(news_fetcher_tool):
    """
    测试：parse_articles 方法能否从给定的 HTML 中正确提取信息。
    """
    # --- 准备 (Arrange) ---
    fake_html = create_fake_html_page(2)

    # --- 执行 (Act) ---
    articles = news_fetcher_tool.parse_articles(fake_html)

    # --- 断言 (Assert) ---
    assert len(articles) == 2
    assert articles[0]['title'] == "Fake Article Title 1"
    assert articles[0]['url'] == "https://www.nature.com/articles/d41586-024-0001-5"
    assert articles[1]['title'] == "Fake Article Title 2"

# def test_execute_success_multiple_pages(news_fetcher_tool, mocker):
#     """
#     测试：execute 方法能否成功抓取并组合多个页面的文章。
#     """
#     # --- 准备 (Arrange) ---
#     # 模拟两次网络请求，第一次返回2篇文章，第二次返回1篇
#     page1_html = create_fake_html_page(2)
#     page2_html = create_fake_html_page(1)
    
#     mock_response_page1 = MagicMock()
#     mock_response_page1.text = page1_html
    
#     mock_response_page2 = MagicMock()
#     mock_response_page2.text = page2_html

#     # 模拟 requests.get 的行为序列
#     mock_get = mocker.patch('requests.get', side_effect=[mock_response_page1, mock_response_page2])
#     mock_sleep = mocker.patch('time.sleep')

#     # --- 执行 (Act) ---
#     results = news_fetcher_tool.execute(num_articles=5, max_pages=2)

#     # --- 断言 (Assert) ---
#     assert len(results) == 3 # 2 + 1
#     assert results[0]['title'] == "Fake Article Title 1"
#     assert results[2]['title'] == "Fake Article Title 1" # The second page's first article
#     assert mock_get.call_count == 2
#     assert mock_sleep.call_count == 2

# def test_execute_stops_when_no_articles_found(news_fetcher_tool, mocker):
#     """
#     测试：当一个页面没有返回任何文章时，execute 是否会停止抓取。
#     """
#     # --- 准备 (Arrange) ---
#     page1_html = create_fake_html_page(2)
#     empty_page_html = create_fake_html_page(0) # 空页面

#     mock_response_page1 = MagicMock(text=page1_html)
#     mock_response_empty = MagicMock(text=empty_page_html)

#     mock_get = mocker.patch('requests.get', side_effect=[mock_response_page1, mock_response_empty])
#     mock_sleep = mocker.patch('time.sleep')

#     # --- 执行 (Act) ---
#     results = news_fetcher_tool.execute(num_articles=10, max_pages=5)

#     # --- 断言 (Assert) ---
#     assert len(results) == 2 # 只应包含第一页的结果
#     assert mock_get.call_count == 2 # 尝试了第一页和第二页
#     # [修正] sleep 只在成功抓取到文章的循环末尾调用，因此只调用1次
#     assert mock_sleep.call_count == 1 

def test_execute_handles_network_error(news_fetcher_tool, mocker):
    """
    测试：当 requests.get 抛出网络异常时，execute 是否能正确处理。
    """
    # --- 准备 (Arrange) ---
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Fake network error"))

    # --- 执行 (Act) ---
    results = news_fetcher_tool.execute()

    # --- 断言 (Assert) ---
    assert len(results) == 1
    assert "error" in results[0]
    assert "Network error" in results[0]["error"]

# def test_execute_respects_num_articles_limit(news_fetcher_tool, mocker):
#     """
#     测试：当抓取的文章数达到 num_articles 限制时，是否会停止。
#     """
#     # --- 准备 (Arrange) ---
#     page1_html = create_fake_html_page(5)
#     page2_html = create_fake_html_page(5)

#     mock_response_page1 = MagicMock(text=page1_html)
#     mock_response_page2 = MagicMock(text=page2_html)

#     mock_get = mocker.patch('requests.get', side_effect=[mock_response_page1, mock_response_page2])
#     mock_sleep = mocker.patch('time.sleep')

#     # --- 执行 (Act) ---
#     # 我们只需要7篇文章，但第一页有5篇，所以它需要去第二页
#     results = news_fetcher_tool.execute(num_articles=7, max_pages=5)

#     # --- 断言 (Assert) ---
#     assert len(results) == 7 # 结果被正确截断
#     assert mock_get.call_count == 2 # 确实抓取了第二页
#     assert mock_sleep.call_count == 2
