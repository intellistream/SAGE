"""T1.6 - FAISSIndex 测试

验收标准：8个测试全部通过
- test_init: 初始化配置
- test_add_and_query: 添加和查询向量
- test_cosine_similarity: Cosine 相似度
- test_remove_and_tombstone: 删除和墓碑机制
- test_rebuild_index: 索引重建
- test_duplicate_detection: 重复检测
- test_persistence: 持久化和加载
- test_contains_and_size: contains 和 size 方法
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import (
    FAISSIndex,
    IndexFactory,
)


class TestFAISSIndex:
    """T1.6 - FAISSIndex 功能测试"""

    def test_init(self):
        """测试初始化"""
        # 基本初始化
        index = FAISSIndex({"dim": 128})
        assert index.dim == 128
        assert index.size() == 0

        # 指定 metric
        index_l2 = FAISSIndex({"dim": 64, "metric": "l2"})
        assert index_l2.normalize is False

        index_cosine = FAISSIndex({"dim": 64, "metric": "cosine"})
        assert index_cosine.normalize is True

        # 缺少 dim 应该报错
        with pytest.raises(ValueError):
            FAISSIndex({})

    def test_add_and_query(self):
        """测试添加和查询向量"""
        index = FAISSIndex({"dim": 4, "metric": "l2"})

        # 添加向量
        vec1 = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")
        vec2 = np.array([0.0, 1.0, 0.0, 0.0], dtype="float32")
        vec3 = np.array([0.9, 0.1, 0.0, 0.0], dtype="float32")

        index.add("id1", "text1", {"vector": vec1})
        index.add("id2", "text2", {"vector": vec2})
        index.add("id3", "text3", {"vector": vec3})

        assert index.size() == 3

        # 查询最近邻
        query = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")
        results = index.query(query, top_k=2)

        assert len(results) <= 2
        assert "id1" in results  # 应该返回最相似的 id1
        assert "id3" in results or "id2" in results

    def test_cosine_similarity(self):
        """测试 Cosine 相似度"""
        index = FAISSIndex({"dim": 3, "metric": "cosine"})

        # 添加向量（会自动归一化）
        vec1 = np.array([1.0, 0.0, 0.0], dtype="float32")
        vec2 = np.array([0.0, 1.0, 0.0], dtype="float32")
        vec3 = np.array([0.5, 0.5, 0.0], dtype="float32")  # 45度角

        index.add("id1", "text1", {"vector": vec1})
        index.add("id2", "text2", {"vector": vec2})
        index.add("id3", "text3", {"vector": vec3})

        # 查询与 vec3 相似的向量
        results = index.query(vec3, top_k=3)
        assert len(results) == 3
        assert results[0] == "id3"  # 自己应该是第一个

    def test_remove_and_tombstone(self):
        """测试删除和墓碑机制"""
        index = FAISSIndex({"dim": 2, "metric": "l2", "tombstone_threshold": 3})

        # 添加向量
        for i in range(5):
            vec = np.array([float(i), 0.0], dtype="float32")
            index.add(f"id{i}", f"text{i}", {"vector": vec})

        assert index.size() == 5

        # 删除向量（标记为墓碑）
        index.remove("id1")
        index.remove("id2")

        assert index.size() == 3  # 应该减少
        assert not index.contains("id1")
        assert not index.contains("id2")
        assert index.contains("id0")

        # 查询不应该返回被删除的向量
        query = np.array([1.0, 0.0], dtype="float32")
        results = index.query(query, top_k=5)
        assert "id1" not in results
        assert "id2" not in results

    def test_rebuild_index(self):
        """测试索引重建"""
        index = FAISSIndex({"dim": 2, "metric": "l2", "tombstone_threshold": 2})

        # 添加向量
        for i in range(5):
            vec = np.array([float(i), 0.0], dtype="float32")
            index.add(f"id{i}", f"text{i}", {"vector": vec})

        initial_size = index.size()

        # 删除向量触发重建
        index.remove("id0")
        index.remove("id1")  # 达到阈值，触发重建

        # 重建后墓碑应该被清空
        assert len(index.tombstones) == 0
        assert index.size() == initial_size - 2

        # 验证剩余向量仍然可查询
        query = np.array([3.0, 0.0], dtype="float32")
        results = index.query(query, top_k=2)
        assert "id3" in results

    def test_duplicate_detection(self):
        """测试重复向量检测"""
        index = FAISSIndex({"dim": 2, "metric": "l2"})

        # 添加相同向量
        vec = np.array([1.0, 2.0], dtype="float32")
        index.add("id1", "text1", {"vector": vec})
        index.add("id2", "text2", {"vector": vec})  # 相同向量，不同ID

        # 第二次添加应该被跳过（重复检测）
        # 但如果是更新同一个ID，应该允许
        index.add("id1", "text1_updated", {"vector": vec})
        assert index.size() == 1  # 只有一个向量

    def test_persistence(self):
        """测试持久化和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_index"

            # 创建并保存索引
            index1 = FAISSIndex({"dim": 3, "metric": "cosine"})
            vec1 = np.array([1.0, 0.0, 0.0], dtype="float32")
            vec2 = np.array([0.0, 1.0, 0.0], dtype="float32")
            index1.add("id1", "text1", {"vector": vec1})
            index1.add("id2", "text2", {"vector": vec2})

            index1.save(save_path)

            # 加载索引
            index2 = FAISSIndex({"dim": 3})
            index2.load(save_path)

            # 验证加载的索引
            assert index2.size() == 2
            assert index2.contains("id1")
            assert index2.contains("id2")

            # 验证查询功能
            results = index2.query(vec1, top_k=1)
            assert results[0] == "id1"

    def test_contains_and_size(self):
        """测试 contains 和 size 方法"""
        index = FAISSIndex({"dim": 2, "metric": "l2"})

        # 空索引
        assert index.size() == 0
        assert not index.contains("id1")

        # 添加向量
        vec = np.array([1.0, 0.0], dtype="float32")
        index.add("id1", "text1", {"vector": vec})

        assert index.size() == 1
        assert index.contains("id1")
        assert not index.contains("id2")

        # 删除向量
        index.remove("id1")
        assert index.size() == 0
        assert not index.contains("id1")


class TestFAISSIndexFactory:
    """测试 IndexFactory 集成"""

    def test_create_via_factory(self):
        """测试通过 IndexFactory 创建 FAISSIndex"""
        index = IndexFactory.create("faiss", {"dim": 128, "metric": "cosine"})

        assert isinstance(index, FAISSIndex)
        assert index.dim == 128
        assert index.normalize is True

    def test_factory_registration(self):
        """测试 FAISSIndex 已注册"""
        assert IndexFactory.is_registered("faiss")
        assert "faiss" in IndexFactory.list_types()
