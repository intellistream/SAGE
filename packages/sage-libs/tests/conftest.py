"""
SAGE Userspace 测试配置文件
提供共享的 fixtures 和测试工具
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Any, Dict, List, Optional


# ===== 基础 Fixtures =====

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_config():
    """基础配置字典"""
    return {
        "name": "test_config",
        "version": "1.0.0",
        "debug": True,
        "timeout": 30,
        "max_retries": 3
    }


@pytest.fixture
def sample_data():
    """样例测试数据"""
    return {
        "text": "这是一个测试文档",
        "id": "doc_001",
        "metadata": {"source": "test", "type": "document"},
        "timestamp": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_query():
    """样例查询"""
    return "什么是人工智能？"


# ===== 数据处理 Fixtures =====

@pytest.fixture
def sample_documents():
    """样例文档列表"""
    return [
        {"text": "人工智能是计算机科学的分支", "id": "doc1", "score": 0.9},
        {"text": "机器学习是AI的重要组成部分", "id": "doc2", "score": 0.8},
        {"text": "深度学习使用神经网络", "id": "doc3", "score": 0.7},
        {"text": "自然语言处理处理文本数据", "id": "doc4", "score": 0.6}
    ]


@pytest.fixture
def sample_embeddings():
    """样例向量表示"""
    return [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.2, 0.3, 0.4, 0.5, 0.6],
        [0.3, 0.4, 0.5, 0.6, 0.7],
        [0.4, 0.5, 0.6, 0.7, 0.8]
    ]


@pytest.fixture
def sample_qa_pair():
    """样例问答对"""
    return {
        "question": "什么是深度学习？",
        "answer": "深度学习是机器学习的子领域，使用多层神经网络进行学习。",
        "references": [
            "深度学习是一种机器学习方法",
            "神经网络是深度学习的基础"
        ],
        "generated": "深度学习是使用神经网络的机器学习技术",
        "context": ["深度学习相关文档1", "深度学习相关文档2"]
    }


# ===== 模拟对象 Fixtures =====

@pytest.fixture
def mock_environment():
    """模拟环境对象"""
    env = Mock()
    env.get_config.return_value = {"test": True}
    env.logger = Mock()
    env.env_base_dir = "/tmp/test_env"
    return env


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端"""
    client = Mock()
    client.generate.return_value = "这是生成的回答"
    client.embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    client.is_available.return_value = True
    return client


@pytest.fixture
def mock_vector_store():
    """模拟向量存储"""
    store = Mock()
    store.add.return_value = True
    store.search.return_value = [
        {"text": "相关文档1", "score": 0.9},
        {"text": "相关文档2", "score": 0.8}
    ]
    store.delete.return_value = True
    return store


@pytest.fixture
def mock_agent_tools():
    """模拟Agent工具"""
    tools = []
    
    # 搜索工具
    search_tool = Mock()
    search_tool.name = "search"
    search_tool.description = "搜索相关信息"
    search_tool.run.return_value = "搜索结果"
    tools.append(search_tool)
    
    # 计算工具
    calc_tool = Mock()
    calc_tool.name = "calculate"
    calc_tool.description = "执行数学计算"
    calc_tool.run.return_value = "42"
    tools.append(calc_tool)
    
    return tools


# ===== 异步 Fixtures =====

@pytest.fixture
def mock_async_client():
    """模拟异步客户端"""
    client = AsyncMock()
    client.generate.return_value = "异步生成的回答"
    client.embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    return client


# ===== RAG 相关 Fixtures =====

@pytest.fixture
def sample_retrieval_result():
    """样例检索结果"""
    return {
        "query": "什么是机器学习？",
        "documents": [
            {"text": "机器学习是AI的分支", "score": 0.95, "id": "doc1"},
            {"text": "监督学习需要标注数据", "score": 0.85, "id": "doc2"},
            {"text": "无监督学习不需要标签", "score": 0.75, "id": "doc3"}
        ],
        "total_time": 0.5,
        "retrieval_method": "dense"
    }


@pytest.fixture
def sample_evaluation_data():
    """样例评估数据"""
    return {
        "question": "什么是深度学习？",
        "generated": "深度学习是使用多层神经网络的机器学习方法",
        "references": [
            "深度学习是机器学习的子领域，使用神经网络",
            "深度学习通过多层网络学习复杂模式"
        ],
        "context": [
            "深度学习是机器学习的一个分支",
            "神经网络是深度学习的核心技术"
        ]
    }


# ===== 插件系统 Fixtures =====

@pytest.fixture
def mock_plugin_manager():
    """模拟插件管理器"""
    manager = Mock()
    manager.load_plugin.return_value = True
    manager.unload_plugin.return_value = True
    manager.list_plugins.return_value = ["plugin1", "plugin2"]
    manager.get_plugin.return_value = Mock()
    return manager


@pytest.fixture
def sample_plugin_config():
    """样例插件配置"""
    return {
        "name": "test_plugin",
        "version": "1.0.0",
        "description": "测试插件",
        "entry_point": "test_plugin.main:Plugin",
        "dependencies": ["numpy", "scikit-learn"],
        "config": {
            "param1": "value1",
            "param2": 42,
            "param3": True
        }
    }


# ===== 模型相关 Fixtures =====

@pytest.fixture
def mock_transformer_model():
    """模拟Transformer模型"""
    model = Mock()
    tokenizer = Mock()
    
    # 模拟tokenizer
    tokenizer.encode.return_value = [101, 7592, 1010, 102]
    tokenizer.decode.return_value = "测试文本"
    tokenizer.return_tensors = "pt"
    
    # 模拟model
    model_output = Mock()
    model_output.last_hidden_state.mean.return_value.detach.return_value.numpy.return_value = [[0.1, 0.2, 0.3]]
    model.return_value = model_output
    
    return {"model": model, "tokenizer": tokenizer}


# ===== 工具函数 =====

def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """创建临时文件"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
            tmp.write(content)
    except:
        os.close(fd)
        raise
    return path


def create_sample_dataset(size: int = 10) -> List[Dict[str, Any]]:
    """创建样例数据集"""
    return [
        {
            "id": f"item_{i}",
            "text": f"这是第{i}个测试文档",
            "label": i % 3,
            "features": [0.1 * i, 0.2 * i, 0.3 * i]
        }
        for i in range(size)
    ]


# ===== 测试标记 =====

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 标记单元测试")
    config.addinivalue_line("markers", "integration: 标记集成测试")
    config.addinivalue_line("markers", "slow: 标记耗时测试")
    config.addinivalue_line("markers", "external: 标记需要外部依赖的测试")


# ===== 测试会话配置 =====

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ["SAGE_TEST_MODE"] = "1"
    os.environ["SAGE_LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # 清理环境变量
    os.environ.pop("SAGE_TEST_MODE", None)
    os.environ.pop("SAGE_LOG_LEVEL", None)
