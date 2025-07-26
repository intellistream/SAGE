import pytest

from sage.lib.rag.retriever import DenseRetriever, BM25sRetriever  # 替换为你代码实际模块路径

@pytest.fixture
def dense_retriever_config():
    return {
        "ltm": {"some_key": "some_value"},
        "session_folder": None
    }

@pytest.fixture
def bm25s_retriever_config():
    return {
        "bm25s_collection": "my_bm25_collection",
        "bm25s_config": {"param": "value"}
    }

def test_dense_retriever_execute(dense_retriever_config):
    retriever = DenseRetriever(dense_retriever_config)

    # mock runtime_context
    mock_runtime_context = MagicMock()
    retriever.ctx = mock_runtime_context
    mock_runtime_context.retrieve.return_value = ["doc1", "doc2"]

    input_query = "test query"
    data = input_query

    result = retriever.execute(data)

    # 断言返回的数据格式
    query, chunks = result
    assert query == input_query
    assert chunks == ["doc1", "doc2"]

    # 确认runtime_context.retrieve被调用
    mock_runtime_context.retrieve.assert_called_once_with(
        query=input_query,
        collection_config=dense_retriever_config["ltm"]
    )

def test_dense_retriever_execute_no_ltm(dense_retriever_config):
    dense_retriever_config.pop("ltm")  # 移除ltm配置
    retriever = DenseRetriever(dense_retriever_config)

    # runtime_context不mock
    input_query = "query without ltm"
    data = input_query

    result = retriever.execute(data)

    query, chunks = result
    assert query == input_query
    assert chunks == []  # 无ltm时返回空chunks

from unittest.mock import MagicMock

def test_bm25s_retriever_execute(bm25s_retriever_config, caplog):
    retriever = BM25sRetriever(bm25s_retriever_config)

    # 注入 runtime_context mock（不需要 memory 了）
    mock_runtime_context = MagicMock()
    mock_runtime_context.retrieve.return_value = ["doc1", "doc2"]
    retriever.ctx = mock_runtime_context

    data = "some query"

    with caplog.at_level("INFO"):
        result = retriever.execute(data)

    query, chunks = result
    assert query == "some query"
    assert chunks == ["doc1", "doc2"]


def test_bm25s_retriever_execute_no_collection(bm25s_retriever_config):
    bm25s_retriever_config["bm25s_collection"] = None
    retriever = BM25sRetriever(bm25s_retriever_config)

    # 注入 runtime_context mock，避免访问时报错
    mock_runtime_context = MagicMock()
    mock_memory = MagicMock()
    mock_runtime_context.memory = mock_memory
    retriever.ctx = mock_runtime_context

    data = "some query"

    import pytest
    with pytest.raises(ValueError, match="BM25s collection is not configured"):
        retriever.execute(data)


