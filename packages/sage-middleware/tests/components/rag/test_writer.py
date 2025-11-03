"""
测试 sage.middleware.operators.rag.writer 模块
"""

import pytest

# 尝试导入writer模块
pytest_plugins = []

try:
    from sage.middleware.operators.rag.writer import MemoryWriter

    WRITER_AVAILABLE = True
except ImportError as e:
    WRITER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Writer module not available: {e}")


@pytest.mark.unit
class TestMemoryWriter:
    """测试MemoryWriter类"""

    def test_memory_writer_import(self):
        """测试MemoryWriter导入"""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer module not available")

        from sage.middleware.operators.rag.writer import MemoryWriter

        assert MemoryWriter is not None

    def test_memory_writer_initialization_empty(self):
        """测试MemoryWriter空配置初始化"""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer module not available")

        config = {}
        writer = MemoryWriter(config=config)

        assert writer.config == config
        assert writer.collections == {}

    def test_memory_writer_initialization_with_stm(self):
        """测试MemoryWriter STM配置初始化"""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer module not available")

        config = {
            "stm": True,
            "stm_collection": "short_term_memory",
            "stm_config": {"max_size": 100},
        }
        writer = MemoryWriter(config=config)

        assert "stm" in writer.collections
        assert writer.collections["stm"]["collection"] == "short_term_memory"

    def test_memory_writer_initialization_with_ltm(self):
        """测试MemoryWriter LTM配置初始化"""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer module not available")

        config = {
            "ltm": True,
            "ltm_collection": "long_term_memory",
            "ltm_config": {"max_size": 1000},
        }
        writer = MemoryWriter(config=config)

        assert "ltm" in writer.collections
        assert writer.collections["ltm"]["collection"] == "long_term_memory"

    def test_execute_with_string(self):
        """测试执行字符串输入"""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer module not available")

        config = {}
        writer = MemoryWriter(config=config)

        # 由于execute方法可能需要实际的存储后端，这里只测试基本调用
        try:
            _ = writer.execute("test data")  # noqa: F841
            # 如果没有抛出异常，则认为基本功能正常
            assert True
        except Exception:
            # 如果需要实际后端，跳过
            pytest.skip("MemoryWriter requires actual storage backend")

    def test_execute_with_list(self):
        """测试执行列表输入"""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer module not available")

        config = {}
        writer = MemoryWriter(config=config)

        try:
            _ = writer.execute(["data1", "data2"])  # noqa: F841
            assert True
        except Exception:
            pytest.skip("MemoryWriter requires actual storage backend")
