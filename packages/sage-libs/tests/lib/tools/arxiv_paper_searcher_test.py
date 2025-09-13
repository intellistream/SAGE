# test_tool.py

import pytest
import requests
# ================================
# 关键修改：根据您的项目结构更新 import 语句
# 假设您的项目根目录是 /home/wxh/refactor_wxh/MemoRAG/
# 并且您会从该根目录运行 pytest
# ================================
from sage.libs.tools.arxiv_paper_searcher import _Searcher_Tool


# ================================
# 1. Fixture: 创建可复用的工具实例
# ================================
@pytest.fixture
def searcher_tool():
    """
    这是一个 Fixture，它为每个需要它的测试函数提供一个干净的、
    全新的 _Searcher_Tool 实例。这避免了在每个测试中重复创建对象。
    """
    return _Searcher_Tool()


# ================================
# 2. 基础功能测试
# ================================
def test_tool_initialization(searcher_tool):
    """
    测试：工具初始化时，其名称、输入/输出类型等元数据是否正确。
    这是一个简单的“冒烟测试”，确保基础配置没问题。
    """
    assert searcher_tool.tool_name == "_Searcher_Tool"
    assert "query" in searcher_tool.input_types
    assert (
        searcher_tool.output_type
        == "list - A list of dictionaries containing paper information."
    )
    assert isinstance(searcher_tool.get_metadata(), dict)


# ================================
# 3. 核心功能测试（使用 Mocking）
# ================================


def test_execute_success_with_mock(searcher_tool, mocker):
    """
    测试：在成功获取网络数据时，execute 方法能否正确解析并返回结果。
    这是最重要的测试，它使用了“模拟”（Mocking）技术来伪造网络响应。
    """
    # --- 准备 (Arrange) ---
    # a. 创建一个假的、简化的 arXiv HTML 响应内容，模拟真实网页结构。
    fake_html_content = """
    <html>
        <body>
            <li class="arxiv-result">
                <p class="title">Fake Paper Title 1</p>
                <p class="authors">Authors: Dr. Fake Author One</p>
                <p class="list-title">
                    <a href="https://arxiv.org/abs/1111.1111">arXiv:1111.1111</a>
                </p>
                <span class="abstract-full">This is a fake abstract. △ Less</span>
            </li>
            <li class="arxiv-result">
                <p class="title">Fake Paper Title 2</p>
                <p class="authors">Authors: Dr. Fake Author Two</p>
                <p class="list-title">
                    <a href="https://arxiv.org/abs/2222.2222">arXiv:2222.2222</a>
                </p>
                <span class="abstract-full">Second fake abstract. △ Less</span>
            </li>
        </body>
    </html>
    """

    # b. 使用 mocker 来“拦截”所有 `requests.get` 的调用。
    # 我们不让它真的去访问网络，而是让它返回我们上面伪造的 HTML 数据。
    mock_response = mocker.Mock()
    mock_response.content = fake_html_content.encode("utf-8")  # 响应内容需要是 bytes
    mocker.patch("requests.get", return_value=mock_response)

    # --- 执行 (Act) ---
    results = searcher_tool.execute(query="any query", max_results=2)

    # --- 断言 (Assert) ---
    # 验证返回结果的类型和数量是否正确
    assert isinstance(results, list)
    assert len(results) == 2

    # 验证第一个解析结果的每个字段是否都正确
    first_paper = results[0]
    assert first_paper["title"] == "Fake Paper Title 1"
    assert first_paper["authors"] == "Dr. Fake Author One"
    assert first_paper["abstract"] == "This is a fake abstract."
    assert first_paper["link"] == "https://arxiv.org/abs/1111.1111"

    # 验证第二个解析结果的标题
    second_paper = results[1]
    assert second_paper["title"] == "Fake Paper Title 2"


def test_execute_handles_network_error(searcher_tool, mocker):
    """
    测试：当网络请求失败（例如超时、DNS错误）时，execute 方法能否优雅地处理。
    """
    # --- 准备 (Arrange) ---
    # 模拟 requests.get 在被调用时，直接抛出一个网络异常
    mocker.patch(
        "requests.get",
        side_effect=requests.exceptions.RequestException("Fake Network Error"),
    )

    # --- 执行 (Act) ---
    results = searcher_tool.execute(query="any query")

    # --- 断言 (Assert) ---
    # 根据您代码中的 try/except 逻辑，遇到异常时应该返回一个空列表
    assert results == []


def test_execute_parameter_handling(searcher_tool, mocker):
    """
    测试：execute 方法对输入参数的处理逻辑是否正确。
    例如，它是否能将无效的 `size` 修正为最接近的有效值。
    """
    # --- 准备 (Arrange) ---
    # 我们只需要一个能让循环退出的空响应即可，内容不重要
    mocker.patch("requests.get", return_value=mocker.Mock(content=b""))

    # --- 执行 (Act) ---
    # 提供一个无效的 size=60 (有效值为25, 50, 100, 200)
    searcher_tool.execute(query="test", size=60)

    # --- 断言 (Assert) ---
    # 检查传递给 requests.get 的参数是否被正确修正了。
    # size=60 应该被修正为最接近的有效值 50。
    # .call_args 可以获取到最后一次调用 mock 对象的参数
    called_args, called_kwargs = requests.get.call_args
    assert called_kwargs["params"]["size"] == "50"


def test_execute_no_results_found(searcher_tool, mocker):
    """
    测试：当搜索页面成功返回，但页面上没有任何论文结果时的情况。
    """
    # --- 准备 (Arrange) ---
    # 模拟一个没有任何 <li class="arxiv-result"> 的HTML响应
    empty_html_content = (
        "<html><body><h3>Show Results</h3><p>No results found.</p></body></html>"
    )
    mocker.patch(
        "requests.get",
        return_value=mocker.Mock(content=empty_html_content.encode("utf-8")),
    )

    # --- 执行 (Act) ---
    results = searcher_tool.execute(query="a query that finds nothing")

    # --- 断言 (Assert) ---
    # 此时应该返回一个空列表
    assert results == []
