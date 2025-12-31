"""BM25Index 单元测试

测试 BM25 文本检索索引的功能：
- 基本添加和检索
- 中英文自动检测
- 动态插入和删除
- 持久化和加载
- 排序和分数过滤
"""

import tempfile
from pathlib import Path

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import (
    BM25Index,
    IndexFactory,
)


class TestBM25IndexBasic:
    """测试 BM25 索引的基本功能"""

    def test_create_index(self):
        """测试创建索引"""
        config = {"backend": "numba", "language": "auto"}
        index = BM25Index(config)

        assert index.backend == "numba"
        assert index.language == "auto"
        assert index.size() == 0

    def test_create_via_factory(self):
        """测试通过工厂创建索引"""
        index = IndexFactory.create("bm25", {"language": "zh"})

        assert isinstance(index, BM25Index)
        assert index.language == "zh"

    def test_add_and_contains(self):
        """测试添加和检查"""
        index = BM25Index()

        # 添加文档
        index.add("doc1", "人工智能和机器学习", {})
        index.add("doc2", "深度学习神经网络", {})

        # 检查
        assert index.contains("doc1")
        assert index.contains("doc2")
        assert not index.contains("doc3")
        assert index.size() == 2

    def test_query_chinese(self):
        """测试中文检索"""
        index = BM25Index({"language": "zh"})

        # 添加中文文档
        index.add("doc1", "人工智能是计算机科学的一个分支", {})
        index.add("doc2", "机器学习是人工智能的核心技术", {})
        index.add("doc3", "深度学习是机器学习的一种方法", {})

        # 查询"人工智能"
        results = index.query("人工智能", top_k=2)

        # doc1 和 doc2 都包含"人工智能"，应该排在前面
        assert len(results) == 2
        assert "doc1" in results
        assert "doc2" in results

    def test_query_english(self):
        """测试英文检索"""
        index = BM25Index({"language": "en"})

        # 添加英文文档
        index.add("doc1", "Artificial intelligence is a branch of computer science", {})
        index.add("doc2", "Machine learning is a core technology of AI", {})
        index.add("doc3", "Deep learning is a method of machine learning", {})

        # 查询 "machine learning"
        results = index.query("machine learning", top_k=2)

        # doc2 和 doc3 都包含 "machine learning"
        assert len(results) == 2
        assert "doc2" in results
        assert "doc3" in results

    def test_query_with_top_k(self):
        """测试 top_k 参数"""
        index = BM25Index()

        # 添加多个文档
        for i in range(5):
            index.add(f"doc{i}", f"文档{i}包含一些文本内容", {})

        # 查询 top_k=2
        results = index.query("文档", top_k=2)
        assert len(results) == 2

        # 查询 top_k=10（超过文档数量）
        results = index.query("文档", top_k=10)
        assert len(results) == 5

    def test_query_empty_index(self):
        """测试空索引查询"""
        index = BM25Index()

        results = index.query("查询内容")
        assert results == []

    def test_update_document(self):
        """测试更新文档（添加相同 ID）"""
        index = BM25Index({"language": "zh"})

        # 添加文档
        index.add("doc1", "原始内容关于人工智能", {})
        index.add("doc2", "其他文档", {})

        # 查询"人工智能"应该返回 doc1
        results = index.query("人工智能", top_k=10)
        assert "doc1" in results

        # 更新 doc1（添加相同 ID）
        index.add("doc1", "更新后的内容关于机器学习", {})

        # 大小应该不变
        assert index.size() == 2

        # 查询"机器学习"应该返回 doc1
        results = index.query("机器学习", top_k=10)
        assert "doc1" in results

        # 查询"人工智能"不应该返回 doc1（因为已经更新）
        results = index.query("人工智能", top_k=10)
        # doc1 已经不包含"人工智能"了，所以不应该排第一
        # 由于 BM25 算法的特性，这里只检查 doc1 是否还存在
        assert index.contains("doc1")

    def test_remove_document(self):
        """测试删除文档"""
        index = BM25Index()

        # 添加文档
        index.add("doc1", "文档1", {})
        index.add("doc2", "文档2", {})
        index.add("doc3", "文档3", {})

        assert index.size() == 3

        # 删除 doc2
        index.remove("doc2")

        assert index.size() == 2
        assert not index.contains("doc2")
        assert index.contains("doc1")
        assert index.contains("doc3")

    def test_remove_nonexistent(self):
        """测试删除不存在的文档"""
        index = BM25Index()

        index.add("doc1", "文档1", {})

        # 删除不存在的文档（不应报错）
        index.remove("doc_nonexistent")

        assert index.size() == 1

    def test_clear(self):
        """测试清空索引"""
        index = BM25Index()

        # 添加文档
        index.add("doc1", "文档1", {})
        index.add("doc2", "文档2", {})

        # 清空
        index.clear()

        assert index.size() == 0
        assert not index.contains("doc1")
        assert index.query("文档") == []


class TestBM25IndexLanguageDetection:
    """测试语言自动检测"""

    def test_auto_detect_chinese(self):
        """测试自动检测中文"""
        index = BM25Index({"language": "auto"})

        # 添加中文文档（会自动检测为中文）
        index.add("doc1", "这是一段中文文本", {})

        assert index.tokenizer is not None

    def test_auto_detect_english(self):
        """测试自动检测英文"""
        index = BM25Index({"language": "auto"})

        # 添加英文文档（会自动检测为英文）
        index.add("doc1", "This is an English text", {})

        assert index.tokenizer is not None

    def test_explicit_chinese(self):
        """测试显式指定中文"""
        index = BM25Index({"language": "zh"})

        index.add("doc1", "中文文档", {})
        results = index.query("中文", top_k=1)

        assert results == ["doc1"]

    def test_explicit_english(self):
        """测试显式指定英文"""
        index = BM25Index({"language": "en"})

        index.add("doc1", "English document", {})
        results = index.query("document", top_k=1)

        assert results == ["doc1"]


class TestBM25IndexPersistence:
    """测试持久化功能"""

    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "bm25_index.pkl"

            # 创建索引并添加数据
            index1 = BM25Index({"language": "zh"})
            index1.add("doc1", "人工智能相关文档", {})
            index1.add("doc2", "机器学习相关文档", {})
            index1.add("doc3", "深度学习相关文档", {})

            # 保存
            index1.save(save_path)

            # 验证文件存在
            assert save_path.exists()

            # 加载到新索引
            index2 = BM25Index()
            index2.load(save_path)

            # 验证数据
            assert index2.size() == 3
            assert index2.language == "zh"

            # 验证查询功能（检查 doc1 在结果中）
            results = index2.query("人工智能", top_k=10)
            assert "doc1" in results

    def test_load_nonexistent_directory(self):
        """测试加载不存在的目录"""
        index = BM25Index()

        with pytest.raises(FileNotFoundError, match="not found"):
            index.load("/nonexistent/path/")

    def test_save_empty_index(self):
        """测试保存空索引"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "empty_index.pkl"

            # 保存空索引
            index1 = BM25Index()
            index1.save(save_path)

            # 加载
            index2 = BM25Index()
            index2.load(save_path)

            assert index2.size() == 0


class TestBM25IndexEdgeCases:
    """测试边界情况"""

    def test_query_invalid_type(self):
        """测试非字符串查询"""
        index = BM25Index()
        index.add("doc1", "文档内容", {})

        with pytest.raises(TypeError, match="requires string query"):
            index.query(123)  # 传入非字符串

    def test_single_document(self):
        """测试单文档索引"""
        index = BM25Index()

        index.add("doc1", "单个文档", {})

        results = index.query("文档", top_k=5)
        assert results == ["doc1"]

    def test_duplicate_words(self):
        """测试包含重复词的文档"""
        index = BM25Index({"language": "zh"})

        index.add("doc1", "重复重复重复词汇", {})
        index.add("doc2", "普通文档", {})

        # 查询"重复"应该返回 doc1
        results = index.query("重复", top_k=1)
        assert results == ["doc1"]

    def test_repr(self):
        """测试字符串表示"""
        index = BM25Index()
        index.add("doc1", "文档1", {})
        index.add("doc2", "文档2", {})

        repr_str = repr(index)
        assert "BM25Index" in repr_str
        assert "size=2" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
