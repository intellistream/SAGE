"""LSHIndex 单元测试

测试 LSH 索引的基本功能：
- 初始化和配置
- 添加、移除、查询
- 相似度检索
- 持久化和加载
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import (
    LSHIndex,
)

# Skip all LSH Index tests - LSH Index not yet implemented/registered
pytestmark = pytest.mark.skip(reason="LSH Index not yet fully implemented")


class TestLSHIndexBasic:
    """测试 LSHIndex 基础功能"""

    def test_init_default(self):
        """测试默认初始化"""
        index = LSHIndex()

        assert index.n_gram == 3
        assert index.num_perm == 128
        assert index.threshold == 0.5
        assert index.size() == 0

    def test_init_with_config(self):
        """测试自定义配置"""
        config = {
            "n_gram": 5,
            "num_perm": 256,
            "threshold": 0.7,
        }
        index = LSHIndex(config)

        assert index.n_gram == 5
        assert index.num_perm == 256
        assert index.threshold == 0.7

    def test_add_and_contains(self):
        """测试添加数据和成员检查"""
        index = LSHIndex()

        index.add("id1", "hello world", {})
        assert index.contains("id1")
        assert not index.contains("id2")
        assert index.size() == 1

        index.add("id2", "hello python", {})
        assert index.contains("id2")
        assert index.size() == 2

    def test_add_update(self):
        """测试更新已存在的数据"""
        index = LSHIndex()

        index.add("id1", "hello world", {})
        assert index.size() == 1

        # 更新（相同 ID）
        index.add("id1", "goodbye world", {})
        assert index.size() == 1
        assert index.contains("id1")

    def test_remove(self):
        """测试移除数据"""
        index = LSHIndex()

        index.add("id1", "hello world", {})
        index.add("id2", "hello python", {})
        assert index.size() == 2

        index.remove("id1")
        assert not index.contains("id1")
        assert index.contains("id2")
        assert index.size() == 1

    def test_remove_nonexistent(self):
        """测试移除不存在的数据（不应报错）"""
        index = LSHIndex()

        index.add("id1", "hello world", {})

        # 移除不存在的 ID
        index.remove("id999")  # 不应报错
        assert index.size() == 1

    def test_clear(self):
        """测试清空索引"""
        index = LSHIndex()

        index.add("id1", "hello world", {})
        index.add("id2", "hello python", {})
        assert index.size() == 2

        index.clear()
        assert index.size() == 0
        assert not index.contains("id1")


class TestLSHIndexQuery:
    """测试 LSH 索引查询功能"""

    def test_query_similar(self):
        """测试相似文本检索"""
        index = LSHIndex({"threshold": 0.5, "num_perm": 128})

        # 添加相似文本
        index.add("id1", "hello world", {})
        index.add("id2", "hello world!", {})  # 非常相似
        index.add("id3", "goodbye world", {})  # 中等相似
        index.add("id4", "python programming", {})  # 不相似

        # 查询相似文本
        results = index.query("hello world")

        # 应该返回 id1 和 id2（最相似）
        assert "id1" in results or "id2" in results
        # id4 应该不在结果中（不相似）
        assert "id4" not in results

    def test_query_with_threshold(self):
        """测试自定义阈值查询"""
        index = LSHIndex({"threshold": 0.3, "num_perm": 128})

        index.add("id1", "hello world", {})
        index.add("id2", "hello python", {})
        index.add("id3", "goodbye world", {})

        # 使用高阈值（更严格）
        results_strict = index.query("hello world", threshold=0.8)
        # 使用低阈值（更宽松）
        results_loose = index.query("hello world", threshold=0.2)

        # 低阈值应该返回更多结果
        assert len(results_loose) >= len(results_strict)

    def test_query_with_top_k(self):
        """测试限制返回结果数量"""
        index = LSHIndex({"threshold": 0.3})

        # 添加多个相似文本
        index.add("id1", "hello world", {})
        index.add("id2", "hello world!", {})
        index.add("id3", "hello worlds", {})
        index.add("id4", "hello worldly", {})

        # 限制返回 2 条
        results = index.query("hello world", top_k=2)
        assert len(results) <= 2

    def test_query_no_match(self):
        """测试无匹配结果"""
        index = LSHIndex({"threshold": 0.8})

        index.add("id1", "hello world", {})
        index.add("id2", "python programming", {})

        # 查询完全不相关的文本
        results = index.query("completely different text", threshold=0.9)
        assert len(results) == 0

    def test_query_requires_text(self):
        """测试查询需要文本参数"""
        index = LSHIndex()

        index.add("id1", "hello world", {})

        # query 不能为 None
        with pytest.raises(ValueError, match="LSHIndex requires a query text"):
            index.query(None)


class TestLSHIndexShingles:
    """测试 n-gram shingles 功能"""

    def test_get_shingles_normal(self):
        """测试正常文本的 shingles"""
        index = LSHIndex({"n_gram": 3})

        shingles = index._get_shingles("hello")
        expected = {"hel", "ell", "llo"}
        assert shingles == expected

    def test_get_shingles_short_text(self):
        """测试短文本（小于 n_gram）"""
        index = LSHIndex({"n_gram": 5})

        shingles = index._get_shingles("hi")
        # 文本太短，返回整个文本
        assert shingles == {"hi"}

    def test_get_shingles_different_n_gram(self):
        """测试不同的 n_gram 大小"""
        index2 = LSHIndex({"n_gram": 2})
        index4 = LSHIndex({"n_gram": 4})

        text = "hello"

        shingles2 = index2._get_shingles(text)
        shingles4 = index4._get_shingles(text)

        # n_gram=2: {"he", "el", "ll", "lo"}
        assert len(shingles2) == 4
        # n_gram=4: {"hell", "ello"}
        assert len(shingles4) == 2


class TestLSHIndexPersistence:
    """测试持久化功能"""

    def test_save_and_load(self):
        """测试保存和加载索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "lsh_index"

            # 创建并填充索引
            index1 = LSHIndex({"n_gram": 3, "num_perm": 128, "threshold": 0.6})
            index1.add("id1", "hello world", {})
            index1.add("id2", "hello python", {})
            index1.add("id3", "goodbye world", {})

            # 保存
            index1.save(save_dir)

            # 加载到新索引
            index2 = LSHIndex()
            index2.load(save_dir)

            # 验证配置
            assert index2.n_gram == 3
            assert index2.num_perm == 128
            assert index2.threshold == 0.6

            # 验证数据
            assert index2.size() == 3
            assert index2.contains("id1")
            assert index2.contains("id2")
            assert index2.contains("id3")

            # 验证查询功能
            results = index2.query("hello world")
            assert len(results) > 0

    def test_load_and_query(self):
        """测试加载后的查询功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "lsh_index"

            # 创建并保存
            index1 = LSHIndex({"threshold": 0.5})
            index1.add("id1", "machine learning", {})
            index1.add("id2", "deep learning", {})
            index1.add("id3", "data science", {})
            index1.save(save_dir)

            # 加载并查询
            index2 = LSHIndex()
            index2.load(save_dir)

            results = index2.query("machine learning")
            # 应该能找到相似项
            assert len(results) > 0
            assert "id1" in results


class TestLSHIndexEdgeCases:
    """测试边界情况"""

    def test_empty_index_query(self):
        """测试空索引查询"""
        index = LSHIndex()

        results = index.query("hello world")
        assert len(results) == 0

    def test_single_item_query(self):
        """测试单条数据查询"""
        index = LSHIndex()

        index.add("id1", "hello world", {})
        results = index.query("hello world")

        # 应该返回自己
        assert "id1" in results

    def test_identical_texts(self):
        """测试完全相同的文本"""
        index = LSHIndex({"threshold": 0.9})

        index.add("id1", "hello world", {})
        index.add("id2", "hello world", {})  # 完全相同

        results = index.query("hello world")

        # 应该返回两个 ID
        assert len(results) == 2
        assert "id1" in results
        assert "id2" in results

    def test_unicode_text(self):
        """测试 Unicode 文本"""
        index = LSHIndex()

        index.add("id1", "你好世界", {})
        index.add("id2", "你好中国", {})
        index.add("id3", "再见世界", {})

        results = index.query("你好世界")
        assert len(results) > 0
        assert "id1" in results
